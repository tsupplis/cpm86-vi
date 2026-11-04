#!/usr/bin/env python3
"""Test production capacity primitives across the signed 16-bit boundary."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

from test_editor_state import function

ROOT = Path(__file__).resolve().parents[1]

HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stevie.h"

char *vi_file_mem, *vi_file_end, *vi_file_max, *vi_curs_char;
char vi_ins_buff[CMDSIZE], *vi_ins_ptr;
int vi_ninsert, vi_changed;
static int failures, messages;
void message(char *s) { (void)s; messages++; }
static void check(int ok) { if (!ok) failures++; }
'''

CHECKS = r'''
int main(void)
{
    static unsigned sizes[] = {32000U, 32767U, 32768U, 40000U};
    char *memory = malloc(40001U);
    unsigned size, i, j;
    int before;
    if (memory == NULL) {
        puts("VI CAPACITY ALLOCATION FAILED");
        return 1;
    }
    vi_file_mem = memory;
    for (j = 0; j < sizeof sizes / sizeof sizes[0]; j++) {
        size = sizes[j];
        vi_file_max = memory + size;
        vi_file_end = vi_curs_char = memory;
        vi_ins_ptr = vi_ins_buff;
        vi_ninsert = vi_changed = 0;
        check(vi_byte_span(memory, memory) == 0U);
        check(vi_byte_span(memory, vi_file_max) == size);
        check(vi_byte_span(memory + 1U, vi_file_max) == size - 1U);
        check(vi_byte_span(memory + size / 2U, vi_file_max) == size - size / 2U);
        check(canincrease(size - 1U));
        before = messages;
        check(!canincrease(size) && messages == before + 1);
        check(insertbyte('A', 1));
        check(vi_file_end == memory + 1 && memory[0] == 'A');
        check(vi_ins_ptr == vi_ins_buff + 1 && vi_ninsert == 1);

        vi_file_end = vi_curs_char = vi_file_max - 2;
        vi_ins_ptr = vi_ins_buff;
        vi_ninsert = vi_changed = 0;
        before = messages;
        check(!insertbyte('B', 1) && messages == before + 1);
        check(vi_file_end == vi_file_max - 2 && !vi_changed);
        check(insertbyte('B', 0) && vi_file_end == vi_file_max - 1);
        before = messages;
        check(!insertbyte('C', 0) && messages == before + 1);
        check(vi_file_end == vi_file_max - 1 && vi_ninsert == 1);
        vi_file_end = vi_file_max;
        check(vi_byte_span(vi_file_end, vi_file_max) == 0U);
        check(!canincrease(1U));
    }
    vi_file_max = memory + 40000U;
    for (i = 0; i < 40000U; i++)
        memory[i] = (char)(i % 251U);
    memory[40000U] = 77;
    vi_file_end = memory + 39997U;
    vi_curs_char = memory;
    vi_changed = 0;
    insstr("XY");
    check(vi_file_end == memory + 39999U && vi_curs_char == memory + 2);
    check(vi_changed && memory[0] == 'X' && memory[1] == 'Y');
    for (i = 0; i < 39997U; i++)
        check(memory[i + 2U] == (char)(i % 251U));
    check(memory[40000U] == 77);
    vi_changed = 0;
    before = messages;
    inschar('Z');
    check(!vi_changed && messages == before + 1);
    check(vi_file_end == memory + 39999U && vi_curs_char == memory + 2);
    check(memory[40000U] == 77);
    free(memory);
    printf("VI CAPACITY %s: %d failures\n", failures ? "FAIL" : "PASS", failures);
    return failures != 0;
}
'''


def run(args, work):
    try:
        return subprocess.run(args, cwd=work, check=True, timeout=60,
                              capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        print(error.stdout[-4000:])
        print(error.stderr[-4000:])
        raise
    except subprocess.TimeoutExpired as error:
        print((error.stdout or b'')[-4000:])
        print((error.stderr or b'')[-4000:])
        raise


def main():
    lines = (ROOT / 'linefunc.c').read_text()
    misc = (ROOT / 'misccmds.c').read_text()
    edit = (ROOT / 'edit.c').read_text()
    source = HARNESS
    source += function(lines, 'unsigned vi_byte_span(const char *first, const char *last)')
    for signature in ('static int canincrease(unsigned n)\n',
                      'void inschar(int c)', 'void insstr(char *s)'):
        source += '\n' + function(misc, signature)
    for signature in ('static int insertroom(int n, int reserve_eof)\n',
                      'static int insertbyte(int c, int reserve_eof)\n'):
        source += '\n' + function(edit, signature)
    with tempfile.TemporaryDirectory(prefix='vi-capacity-') as directory:
        work = Path(directory)
        shutil.copyfile(ROOT / 'stevie.h', work / 'stevie.h')
        (work / 'capacity.c').write_text(source + CHECKS)
        run([os.environ.get('CC_HOST', 'cc'), '-std=c99', '-g',
             '-fsanitize=address,undefined', '-I.', 'capacity.c',
             '-o', 'capacity-host'], work)
        result = run([str(work / 'capacity-host')], work)
        assert 'VI CAPACITY PASS: 0 failures' in result.stdout, result.stdout
        print('CAPACITY PASS: host sanitizers', flush=True)
        run(['aztec42_cc', '-I.', '+F', '+0', '-o', 'capacity.o', 'capacity.c'], work)
        for library, extension in (('c86', 'cmd'), ('d11', 'com'), ('c', 'exe')):
            program = 'capacity.' + extension
            run(['aztec42_link', '-o', program, 'capacity.o', '-l' + library], work)
            result = run([os.environ.get('EMU2', 'emu2'), program], work)
            assert 'VI CAPACITY PASS: 0 failures' in result.stdout, result.stdout
            print('CAPACITY PASS:', library, '(32000/32767/32768/40000 bytes)',
                  flush=True)


if __name__ == '__main__':
    main()
