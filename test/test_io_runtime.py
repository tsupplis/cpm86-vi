#!/usr/bin/env python3
"""Verify large read counts, error rollback and real saves on host and 8086."""
from pathlib import Path
import os
import shutil
import tempfile

from test_editor_state import function
from test_capacity_runtime import run

ROOT = Path(__file__).resolve().parents[1]

HARNESS = r'''
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stevie.h"
#include "save.h"

char *vi_file_mem, *vi_file_end, *vi_file_max, *vi_curs_char, *vi_top_char;
char *vi_mark;
char *vi_file_name = "INPUT.TXT";
int vi_binary, vi_changed;
static char last_output[256];
static long fail_after = -1L;
static int read_failed, fail_close;
static unsigned long tail_moves, tail_bytes;
void message(char *s) { snprintf(last_output, sizeof last_output, "%s", s); }
char *strsave(char *s) { return s; }
int vi_set_filename(char *s) { vi_file_name = s; return 1; }
static int test_getc(FILE *f) {
    if (fail_after == 0L) { read_failed = 1; return EOF; }
    if (fail_after > 0L) fail_after--;
    return getc(f);
}
static int test_ferror(FILE *f) { return read_failed || ferror(f); }
static int test_fclose(FILE *f) {
    int result = fclose(f);
    return fail_close ? EOF : result;
}
static void *test_memmove(void *to, const void *from, size_t length) {
    if ((char *)to > (const char *)from && length) {
        tail_moves++;
        tail_bytes += length;
    }
    return memmove(to, from, length);
}
#define REQUIRE(x) if (!(x)) { \
    printf("VI IO FAIL: line %d\n", __LINE__); return 1; }
'''

CHECKS = r'''
static void prepare(unsigned length, int dirty)
{
    memset(vi_file_mem, 'T', length);
    memcpy(vi_file_mem, "HEAD", 4);
    vi_file_end = vi_file_mem + length;
    vi_curs_char = vi_file_mem + 5;
    vi_top_char = vi_file_mem + 1;
    vi_changed = dirty;
}

static int original(unsigned length, int dirty)
{
    unsigned i;
    if (vi_file_end != vi_file_mem + length ||
        vi_curs_char != vi_file_mem + 5 || vi_top_char != vi_file_mem + 1 ||
        vi_changed != dirty || memcmp(vi_file_mem, "HEAD", 4))
        return 0;
    for (i = 4; i < length; i++)
        if (vi_file_mem[i] != 'T') return 0;
    return 1;
}

static int check_chunks(void)
{
    static unsigned sizes[] = {127U, 128U, 129U, 255U, 256U, 257U};
    static long failures[] = {0L, 1L, 127L, 128L, 129L, 255L, 256L, 257L};
    unsigned s, offset, i, length;
    unsigned long moves;
    int dirty;
    char name[16];
    for (s = 0; s < sizeof sizes / sizeof sizes[0]; s++) {
        length = sizes[s];
        sprintf(name, "C%u.TXT", length);
        for (offset = 0; offset <= 8; offset += 4) {
            for (dirty = 0; dirty <= 1; dirty++) {
                prepare(8, dirty);
                vi_file_max = vi_file_end + length;
                tail_moves = tail_bytes = 0;
                REQUIRE(readfile(name, vi_file_mem + offset, 1) == 0);
                REQUIRE(vi_file_end == vi_file_max && vi_changed == dirty);
                REQUIRE(vi_curs_char == vi_file_mem + 5 &&
                        vi_top_char == vi_file_mem + 1);
                for (i = 0; i < offset; i++)
                    REQUIRE(vi_file_mem[i] == (i < 4 ? "HEAD"[i] : 'T'));
                for (i = 0; i < length; i++)
                    REQUIRE(vi_file_mem[offset + i] == 'X');
                for (i = offset; i < 8; i++)
                    REQUIRE(vi_file_mem[length + i] == (i < 4 ? "HEAD"[i] : 'T'));
                moves = offset == 8 ? 0 : (length + 127U) / 128U;
                REQUIRE(tail_moves == moves && tail_bytes == moves * (8 - offset));

                prepare(8, dirty);
                vi_file_max = vi_file_end + length - 1;
                REQUIRE(readfile(name, vi_file_mem + offset, 1) == -1);
                REQUIRE(original(8, dirty));
            }
        }
    }
    vi_file_max = vi_file_mem + 40064U;
    for (dirty = 0; dirty <= 1; dirty++) {
        for (s = 0; s < sizeof failures / sizeof failures[0]; s++) {
            prepare(8, dirty);
            fail_after = failures[s];
            REQUIRE(readfile("C257.TXT", vi_file_mem + 4, 1) == -1);
            fail_after = -1L; read_failed = 0;
            REQUIRE(original(8, dirty));
        }
        prepare(8, dirty);
        fail_close = 1;
        REQUIRE(readfile("C129.TXT", vi_file_mem + 4, 1) == -1);
        fail_close = 0;
        REQUIRE(original(8, dirty));
    }
    prepare(8, 0);
    REQUIRE(readfile("FILTER.TXT", vi_file_mem + 4, 1) == 0);
    REQUIRE(vi_file_end == vi_file_mem + 265U);
    REQUIRE(!memcmp(vi_file_mem, "HEAD", 4));
    for (i = 0; i < 256; i++)
        REQUIRE(vi_file_mem[4 + i] == (i < 127 ? 'A' : 'B'));
    REQUIRE(vi_file_mem[260] == '\n');
    REQUIRE(!memcmp(vi_file_mem + 261, "TTTT", 4));
    prepare(8, 0);
    vi_binary = 1;
    REQUIRE(readfile("PACKED.IN", vi_file_mem + 4, 1) == 0);
    REQUIRE(vi_file_end == vi_file_mem + 776U);
    REQUIRE(!memcmp(vi_file_mem, "HEAD", 4));
    for (i = 0; i < 768; i++)
        REQUIRE((unsigned char)vi_file_mem[4 + i] == i % 256U);
    REQUIRE(!memcmp(vi_file_mem + 772, "TTTT", 4));
    vi_binary = 0;
    return 0;
}

int main(void)
{
    static unsigned sizes[] = {32767U, 32768U, 40000U};
    unsigned i, j;
    int dirty;
    char name[16], expected[80];
    vi_file_mem = malloc(40065U);
    REQUIRE(vi_file_mem != NULL);
    vi_file_max = vi_file_mem + 40064U;
    vi_binary = 0;
    REQUIRE(check_chunks() == 0);
    for (j = 0; j < sizeof sizes / sizeof sizes[0]; j++) {
        sprintf(name, "N%u.TXT", sizes[j]);
        vi_file_end = vi_curs_char = vi_top_char = vi_file_mem;
        vi_changed = 0;
        REQUIRE(readfile(name, vi_file_mem, 1) == 0);
        REQUIRE(vi_file_end == vi_file_mem + sizes[j] && !vi_changed);
        for (i = 0; i < sizes[j]; i++) REQUIRE(vi_file_mem[i] == 1);
        sprintf(expected, "%u characters", sizes[j]);
        REQUIRE(strstr(last_output, expected) != NULL);
        sprintf(expected, "(%u un-printable)", sizes[j]);
        REQUIRE(strstr(last_output, expected) != NULL);
    }

    for (dirty = 0; dirty <= 1; dirty++) {
        prepare(8, dirty);
        fail_after = 35000L;
        REQUIRE(readfile("N40000.TXT", vi_file_mem + 4, 1) == -1);
        fail_after = -1L; read_failed = 0;
        REQUIRE(original(8, dirty));
        REQUIRE(strstr(last_output, "Read/close failed") != NULL);
        fail_close = 1;
        REQUIRE(readfile("N40000.TXT", vi_file_mem + 4, 1) == -1);
        fail_close = 0;
        REQUIRE(original(8, dirty));
        REQUIRE(strstr(last_output, "Read/close failed") != NULL);
        vi_file_max = vi_file_mem + 40000U;
        REQUIRE(readfile("N40000.TXT", vi_file_mem + 4, 1) == -1);
        REQUIRE(original(8, dirty));
        REQUIRE(strstr(last_output, "File too long") != NULL);
        vi_file_max = vi_file_mem + 40064U;
    }
    prepare(39994U, 1);
    fail_after = 2L;
    REQUIRE(readfile("N40000.TXT", vi_file_mem + 4, 1) == -1);
    fail_after = -1L; read_failed = 0;
    REQUIRE(original(39994U, 1));

    vi_file_end = vi_curs_char = vi_top_char = vi_file_mem;
    vi_changed = 0;
    vi_file_max = vi_file_mem + 40000U;
    vi_file_mem[40000U] = 77;
    REQUIRE(readfile("OVER.TXT", vi_file_mem, 1) == -1);
    REQUIRE(vi_file_end == vi_file_mem && !vi_changed);
    REQUIRE(vi_file_mem[40000U] == 77);
    vi_file_max = vi_file_mem + 40064U;

    vi_binary = 1;
    REQUIRE(readfile("BINARY.IN", vi_file_mem, 1) == 0);
    REQUIRE(vi_file_end == vi_file_mem + 32768U);
    for (i = 0; i < 32768U; i++) REQUIRE(vi_file_mem[i] == 1);
    vi_file_end = vi_file_mem;
    vi_binary = 0;
    REQUIRE(readfile("CRLF.IN", vi_file_mem, 1) == 0);
    REQUIRE(vi_file_end == vi_file_mem + 40000U);
    for (i = 0; i < 40000U; i++) REQUIRE(vi_file_mem[i] == '\n');
    REQUIRE(strstr(last_output, "40000 characters") != NULL);

    for (i = 0; i < 40000U; i++) vi_file_mem[i] = (char)(i % 251U);
    vi_file_end = vi_file_mem + 40000U;
    vi_binary = vi_changed = 1;
    REQUIRE(writeit("OUTPUT.BIN") && !vi_changed);
    REQUIRE(strstr(last_output, "40000 characters") != NULL);
    memset(vi_file_mem, '\n', 40000U);
    vi_binary = 0;
    vi_changed = 1;
    REQUIRE(writeit("OUTPUT.TXT") && !vi_changed);
    REQUIRE(strstr(last_output, "40000 characters") != NULL);
    free(vi_file_mem);
    puts("VI IO PASS: 0 failures");
    return 0;
}
'''


def verify(program, work, cpm=False):
    work.mkdir()
    for size in (127, 128, 129, 255, 256, 257):
        (work / f'C{size}.TXT').write_bytes(b'X' * size + b'\x1a')
    (work / 'FILTER.TXT').write_bytes(
        b'A' * 127 + b'\r' * 300 + b'B' * 129 + b'\r\n\x1aignored')
    (work / 'PACKED.IN').write_bytes(bytes(range(256)) * 3)
    for size in (32767, 32768, 40000):
        (work / f'N{size}.TXT').write_bytes(b'\x01' * size + b'\x1a')
    (work / 'OVER.TXT').write_bytes(b'\x01' * 40001 + b'\x1a')
    (work / 'BINARY.IN').write_bytes(b'\x01' * 32768)
    (work / 'CRLF.IN').write_bytes(b'\r\n' * 40000 + b'\x1a')
    result = run(program, work)
    assert 'VI IO PASS: 0 failures' in result.stdout, result.stdout
    binary = bytes(i % 251 for i in range(40000))
    text = b'\r\n' * 40000
    if cpm:
        binary += b'\x00' * (-len(binary) % 128)
        text += b'\x1a'
        text += b'\x1a' * (-len(text) % 128)
    assert (work / 'OUTPUT.BIN').read_bytes() == binary
    assert (work / 'OUTPUT.TXT').read_bytes() == text


def main():
    source = HARNESS
    source += function((ROOT / 'linefunc.c').read_text(),
                       'unsigned vi_byte_span(const char *first, const char *last)')
    source += function((ROOT / 'linefunc.c').read_text(), 'void vi_mark_adjust(')
    source += '\n#undef getc\n#define getc test_getc\n'
    source += '#undef ferror\n#define ferror test_ferror\n'
    source += '#define fclose test_fclose\n'
    source += '#define memmove test_memmove\n'
    source += function((ROOT / 'main.c').read_text(),
                       'int readfile(char *fname, char *fromp,')
    source += '\n#undef getc\n#undef ferror\n#undef fclose\n#undef memmove\n'
    source += function((ROOT / 'cmdline.c').read_text(), 'static int writeit(char *fname)\n')
    with tempfile.TemporaryDirectory(prefix='vi-io-') as directory:
        work = Path(directory)
        for name in ('stevie.h', 'save.c', 'save.h', 'os.asm'):
            shutil.copyfile(ROOT / name, work / name)
        (work / 'io.c').write_text(source + CHECKS)
        headers = work / 'host-headers'
        headers.mkdir()
        (headers / 'dos.h').write_text('')
        run([os.environ.get('CC_HOST', 'cc'), '-std=c99', '-g',
             '-D_POSIX_C_SOURCE=200809L', '-fsanitize=address,undefined',
             '-Ihost-headers', '-I.', 'io.c', 'save.c', '-o', 'io-host'], work)
        verify([str(work / 'io-host')], work / 'host')
        print('IO PASS: host sanitizers', flush=True)
        run(['aztec43_acc', '-c', '-o', 'os.o', 'os.asm'], work)
        run(['aztec43_acc', '-I.', '-squeeze', '-c', '-o', 'io.o', 'io.c'], work)
        for target_flag, extension, library in (('-target=cpm86', 'cmd', 'c86'), ('-target=dos1', 'com', 'd11'), ('-target=dos2', 'exe', 'c')):
            extra = ['os.o'] if library == 'c86' else []
            run(['aztec43_acc', target_flag, '-I.', '-squeeze', '-c', '-o', 'save.o', 'save.c'], work)
            program = 'io.' + extension
            run(['aztec43_acc', target_flag, '-o', program, 'io.o', 'save.o', *extra], work)
            verify([os.environ.get('EMU2', 'emu2'), str(work / program)],
                   work / library, cpm=library == 'c86')
            print('IO PASS:', library, '(large counts, rollback, 80000-byte text save)',
                  flush=True)


if __name__ == '__main__':
    main()
