#!/usr/bin/env python3
"""Compile the complete VT backend and check byte ordering and write failures."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

HEADER = r'''
#include <stdio.h>
#include <stddef.h>
#include <sys/types.h>
struct sgttyb { int sg_flags; };
#define CRMOD 16
#define CBREAK 2
#define TIOCSETP 1
int ioctl(int, int, struct sgttyb *);
ssize_t probe_write(int, const void *, size_t);
int probe_flush(FILE *);
'''

PROBE = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "stevie.h"
#include "stub.h"
int vi_rows = 24, vi_columns = 80;
static int failure, writes;
void vi_key_init(int ansi) { (void)ansi; }
void vi_key_exit(void) { fputs("keys restored\n", stderr); }
int ioctl(int fd, int request, struct sgttyb *state) {
    (void)fd; (void)request; (void)state; return 0;
}
int probe_flush(FILE *stream) {
    return failure == 1 || failure == 4 ? EOF : fflush(stream);
}
ssize_t probe_write(int fd, const void *text, size_t length) {
    writes++;
    if (failure == 2) return -1;
    if (failure == 3) return (int)length - 1;
    return (int)write(fd, text, length);
}
int main(int argc, char **argv) {
    char text[80], buffered[256];
    int row, col, start, i;
    setvbuf(stdout, buffered, _IOFBF, sizeof buffered);
    if (argc > 1) {
        failure = atoi(argv[1]);
        if (failure == 4)
            windrefresh();
        windgoto(0, 0);
        return 2;
    }
    printf("prefix:");
    for (row = 0; row < vi_rows; row++)
        for (col = 0; col < vi_columns; col++)
            windgoto(row, col);
    for (start = 32; start < 256; start += 80) {
        int length = 256 - start < 80 ? 256 - start : 80;
        for (i = 0; i < length; i++) text[i] = (char)(start + i);
        windputc('!');
        windputrun(text, (unsigned)length);
    }
    for (i = 0; i < 32; i++) windputc(i);
    windcolor(2);
    windputc('~');
    windcolorreset();
    windcursor(0);
    windcursor(1);
    windclear();
    windgoto(22, 79);
    windputrun("Z", 1);
    windstr("suffix");
    windrefresh();
    fflush(stdout);
    if (writes != 1925) {
        fprintf(stderr, "FAIL: expected 1925 block writes, got %d\n", writes);
        return 1;
    }
    return 0;
}
'''


def main():
    with tempfile.TemporaryDirectory(prefix='vi-vt-output-') as directory:
        work = Path(directory)
        (work / 'stub.h').write_text(HEADER)
        (work / 'probe.c').write_text(PROBE)
        for terminal in ('52', '100'):
            flags = [os.environ.get('CC', 'cc'), '-std=c99',
                     '-D_POSIX_C_SOURCE=200809L', '-Wall', '-Wextra',
                     '-Werror', '-Wno-comment', '-Wno-unused-function', '-I' + str(ROOT),
                     '-I' + str(work)]
            subprocess.run(flags + ['-include', str(work / 'stub.h'),
                           '-D__VTCMD__', '-D__VT' + terminal + '__',
                           '-Dwrite=probe_write', '-Dfflush=probe_flush',
                           '-c', str(ROOT / 'window.c'), '-o', 'window.o'],
                           cwd=work, check=True)
            subprocess.run(flags + ['probe.c', 'window.o', '-o', 'probe'],
                           cwd=work, check=True)
            result = subprocess.run([str(work / 'probe')], capture_output=True)
            assert result.returncode == 0, result.stderr
            expected = bytearray(b'prefix:')
            for row in range(24):
                for col in range(80):
                    expected += (bytes((27, 89, row + 32, col + 32))
                                 if terminal == '52' else
                                 f'\x1b[{row + 1};{col + 1}H'.encode())
            for start in range(32, 256, 80):
                expected += b'!' + bytes(range(start, min(start + 80, 256)))
            expected += bytes(range(32))
            expected += (b'\x1bb\x02~\x1bb\x07\x1bf\x1be\x1bE'
                         b'\x1bY6oZsuffix' if terminal == '52' else
                         b'\x1b[32m~\x1b[0m\x1b[?25l\x1b[?25h'
                         b'\x1b[2J\x1b[H\x1b[23;80HZsuffix')
            assert result.stdout == expected, (terminal, result.stdout, expected)
            for failure in (1, 2, 3, 4):
                result = subprocess.run([str(work / 'probe'), str(failure)],
                                        capture_output=True)
                assert result.returncode == 1, (terminal, failure, result.stderr)
                assert b'Unable to write terminal output!' in result.stderr
                assert b'keys restored' in result.stderr
            print(f'VT{terminal} PASS: 1920 cursor positions, all byte values, '
                  'buffered ordering, flush/write/short-write errors')


if __name__ == '__main__':
    main()
