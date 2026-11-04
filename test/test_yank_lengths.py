#!/usr/bin/env python3
"""Exercise production yank/deletion primitives with unsigned byte lengths."""
from pathlib import Path
import os
import shutil
import tempfile

from test_capacity_runtime import run
from test_editor_state import function

ROOT = Path(__file__).resolve().parents[1]

HARNESS = r'''
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stevie.h"
#include "yankmem.h"

char *vi_file_mem, *vi_file_end, *vi_file_max, *vi_curs_char, *vi_uncurs_char;
char vi_undo_buff[CMDSIZE], vi_redo_buff[CMDSIZE];
int vi_changed, vi_undo_changed, vi_undel_chars;
static unsigned savednum, savedcount;
static int savedlast;
static int failures, messages, screens, fail_load;
void message(char *s) { (void)s; messages++; }
void updatescreen(void) { screens++; }
static void check(int ok, int line, char *expression) {
    if (!ok) {
        printf("Failed check at line %d: %s\n", line, expression);
        failures++;
    }
}
#define CHECK(ok) check((ok), __LINE__, #ok)
#define TEST_CAPACITY 40064U

#define vi_yank_load actual_yank_load
#include "yankmem.c"
#undef vi_yank_load
int vi_yank_load(unsigned offset, char *destination, unsigned length) {
    if (fail_load) {
        memset(destination, '?', length);
        return 0;
    }
    return actual_yank_load(offset, destination, length);
}
'''

CHECKS = r'''
static void state(unsigned length) {
    vi_file_max = vi_file_mem + TEST_CAPACITY + 10U;
    vi_file_end = vi_file_mem + length;
    vi_curs_char = vi_file_mem;
    vi_uncurs_char = vi_file_mem + 1;
    vi_changed = 0;
    vi_undo_changed = 1;
    vi_undel_chars = 7;
    strcpy(vi_undo_buff, "rZ");
    strcpy(vi_redo_buff, "rX");
}
static void unchanged(void) {
    CHECK(!vi_changed && vi_undo_changed && vi_undel_chars == 7);
    CHECK(vi_uncurs_char == vi_file_mem + 1);
    CHECK(!strcmp(vi_undo_buff, "rZ") && !strcmp(vi_redo_buff, "rX"));
}
static char pattern(unsigned i) {
    unsigned c = i % 251U;
    return (char)(c == '\n' ? 255U : c);
}
static void line_roundtrip(unsigned size, int terminated) {
    unsigned i;
    for (i = 0; i < size; i++)
        vi_file_mem[i] = pattern(i);
    if (terminated)
        vi_file_mem[size - 1U] = '\n';
    state(size);
    vi_curs_char = vi_file_mem + size / 2U;
    CHECK(yankline(1));
    CHECK(savednum == size && savedcount == 1);
    CHECK(savedlast == (terminated ? '\n' : pattern(size - 1U)));
    CHECK(vi_curs_char == vi_file_mem + size / 2U);
    unchanged();
    delline(1);
    CHECK(vi_file_end == vi_file_mem && vi_curs_char == vi_file_mem);
    vi_file_max = vi_file_mem + size;
    putline(1);
    CHECK(vi_file_end == vi_file_max && vi_curs_char == vi_file_mem);
    CHECK(!strcmp(vi_undo_buff, "1dd") && !strcmp(vi_redo_buff, "P"));
    for (i = 0; i < size; i++)
        CHECK(vi_file_mem[i] ==
              (terminated && i == size - 1U ? '\n' : pattern(i)));
}
static void delete_boundaries(unsigned size) {
    unsigned i;
    int before;
    memset(vi_file_mem, 'x', size);
    state(size);
    before = screens;
    CHECK(!deleol());
    CHECK(!delword(0));
    CHECK(!delword(1));
    CHECK(screens == before && vi_file_end == vi_file_mem + size);
    CHECK(vi_curs_char == vi_file_mem);
    unchanged();
    for (i = 0; i < size; i++)
        CHECK(vi_file_mem[i] == 'x');
    vi_file_mem[size - 1U] = '\n';
    memcpy(vi_file_mem + size, "tail\n", 5);
    state(size + 5U);
    vi_curs_char = vi_file_mem + size / 2U;
    delline(1);
    CHECK(vi_file_end == vi_file_mem + 5 && vi_curs_char == vi_file_mem);
    CHECK(!memcmp(vi_file_mem, "tail\n", 5) && vi_changed);
}
static void rejected_yank(void) {
    char copy[3];
    unsigned size = vi_yank_capacity() + 1U, i;
    memcpy(vi_file_mem, "ok\n", 3);
    state(3);
    CHECK(yankline(1));
    memset(vi_file_mem, 'x', size);
    state(size);
    vi_curs_char++;
    CHECK(!yankline(1));
    CHECK(savednum == 3 && savedcount == 1 && savedlast == '\n');
    CHECK(vi_curs_char == vi_file_mem + 1 && vi_file_end == vi_file_mem + size);
    unchanged();
    for (i = 0; i < size; i++)
        CHECK(vi_file_mem[i] == 'x');
    CHECK(vi_yank_load(0, copy, 3) && !memcmp(copy, "ok\n", 3));
}
static void paste_edges(void) {
    int k, before, previous_screens;
    memcpy(vi_file_mem, "Y", 1);
    state(1);
    CHECK(yankline(1));
    for (k = 0; k < 2; k++) {
        vi_file_mem[0] = 'a';
        state(1);
        vi_file_max = vi_file_mem + 2;
        before = messages;
        previous_screens = screens;
        putline(k);
        CHECK(messages == before + 1 && screens == previous_screens);
        CHECK(vi_file_end == vi_file_mem + 1 && vi_file_mem[0] == 'a');
        CHECK(vi_curs_char == vi_file_mem);
        unchanged();
        savednum = (unsigned)-1;
        before = messages;
        putline(k);
        CHECK(messages == before + 1 && vi_file_end == vi_file_mem + 1);
        unchanged();
        savednum = 1;
        vi_file_max = vi_file_mem + 3;
        putline(k);
        CHECK(vi_file_end == vi_file_max && vi_changed);
        CHECK(!memcmp(vi_file_mem, k ? "Y\na" : "a\nY", 3));
    }
}
static void failed_load(void) {
    unsigned i;
    int before;
    memcpy(vi_file_mem, "Y\n", 2);
    state(2);
    CHECK(yankline(1));
    for (i = 0; i < 39990U; i++)
        vi_file_mem[i] = pattern(i);
    state(39990U);
    vi_curs_char = vi_file_mem + 123;
    before = screens;
    fail_load = 1;
    putline(1);
    fail_load = 0;
    CHECK(vi_file_end == vi_file_mem + 39990U);
    CHECK(vi_curs_char == vi_file_mem + 123 && screens == before);
    unchanged();
    for (i = 0; i < 39990U; i++)
        CHECK(vi_file_mem[i] == pattern(i));
}
static void large_copies(void) {
    unsigned i;
    memset(vi_file_mem, 'x', 40000U);
    vi_file_mem[40000U] = 0;
    state(0);
    insstr(vi_file_mem);
    CHECK(vi_file_end == vi_file_mem + 40000U);
    CHECK(vi_changed);
    CHECK(vi_curs_char == vi_file_end);
    for (i = 0; i < 40000U; i++)
        CHECK(vi_file_mem[i] == 'x');
    state(40000U);
    vi_file_mem[1] = ' ';
    CHECK(delword(0));
    CHECK(vi_file_end == vi_file_mem + 39999U && vi_file_mem[0] == ' ');
    CHECK(!strcmp(vi_undo_buff, "ix\033"));
    for (i = 1; i < 39999U; i++)
        CHECK(vi_file_mem[i] == 'x');
}
static void line_counts(void) {
    unsigned size = vi_yank_capacity();
    char expected[16];
    memset(vi_file_mem, '\n', size);
    state(size);
    CHECK(yankline(VI_COUNT_MAX));
    CHECK(savednum == size && savedcount == size);
    state(0);
    putline(1);
    sprintf(expected, "%udd", size);
    CHECK(vi_file_end == vi_file_mem + size);
    CHECK(!strcmp(vi_undo_buff, expected));
}
int main(void) {
    static unsigned sizes[] = {24000U, 32767U, 32768U, 40000U, VI_YANK_CAPACITY};
    unsigned j;
    vi_file_mem = malloc(TEST_CAPACITY + 11U);
    if (!vi_file_mem || !vi_yank_init()) {
        puts("VI YANK LENGTH ALLOCATION FAILED");
        return 1;
    }
    printf("YANK CAPACITY: %u\n", vi_yank_capacity());
    for (j = 0; j < sizeof sizes / sizeof sizes[0]; j++) {
        delete_boundaries(sizes[j]);
        if (sizes[j] <= vi_yank_capacity()) {
            line_roundtrip(sizes[j], 0);
            line_roundtrip(sizes[j], 1);
            printf("YANK ROUNDTRIP: %u\n", sizes[j]);
        }
    }
    rejected_yank();
    paste_edges();
    failed_load();
    large_copies();
    line_counts();
    vi_yank_close();
    free(vi_file_mem);
    printf("VI YANK LENGTH %s: %d failures\n", failures ? "FAIL" : "PASS", failures);
    return failures != 0;
}
'''


def main():
    source = HARNESS
    for name, signatures in (
            ('linefunc.c', ('unsigned vi_byte_span(', 'char *prevline(')),
            ('edit.c', ('int oneleft(', 'void beginline(')),
            ('normal.c', ('void resetundo(',)),
            ('main.c', ('void addtobuff(',)),
            ('misccmds.c', ('int issepchar(', 'int yankline(', 'void putline(',
                            'static int canincrease(unsigned n)\n',
                            'void insstr(', 'void delchar(', 'int deleol(',
                            'int delword(', 'void delline('))):
        contents = (ROOT / name).read_text()
        for signature in signatures:
            source += '\n' + function(contents, signature)
    with tempfile.TemporaryDirectory(prefix='vi-yank-length-') as directory:
        work = Path(directory)
        for name in ('stevie.h', 'yankmem.h', 'yankmem.c', 'yankcopy.asm',
                     'yankcp.asm', 'yankd11.asm', 'yankd20.asm'):
            shutil.copyfile(ROOT / name, work / name)
        (work / 'length.c').write_text(source + CHECKS)
        shutil.copyfile(ROOT / 'test/yankmock.c', work / 'mock.c')
        run([os.environ.get('CC_HOST', 'cc'), '-std=c99', '-g',
             '-fsanitize=address,undefined', '-I.', 'length.c', 'mock.c',
             '-o', 'length-host'], work)
        result = run([str(work / 'length-host')], work)
        assert 'VI YANK LENGTH PASS: 0 failures' in result.stdout, result.stdout
        print('YANK LENGTH PASS: host sanitizers', flush=True)
        run(['aztec42_cc', '-I.', '+F', '+0', '-o', 'length.o', 'length.c'], work)
        run(['aztec42_as', 'yankcopy.asm'], work)
        for library, adapter, extension in (
                ('c86', 'yankcp', 'cmd'), ('d11', 'yankd11', 'exe'),
                ('c', 'yankd20', 'exe')):
            run(['aztec42_as', adapter + '.asm'], work)
            program = 'length.' + extension
            run(['aztec42_link', '-o', program, 'length.o', 'yankcopy.o',
                 adapter + '.o', '-l' + library], work)
            if extension == 'cmd':
                run(['pcdev_cmdmod', '-t', 'EXTRA', '-n', '10000',
                     '-m', '10000', program, '2'], work)
            result = run([os.environ.get('EMU2', 'emu2'), program], work)
            assert 'VI YANK LENGTH PASS: 0 failures' in result.stdout, result.stdout
            capacity = 38016
            assert f'YANK CAPACITY: {capacity}' in result.stdout, result.stdout
            assert f'YANK ROUNDTRIP: {capacity}' in result.stdout, result.stdout
            print('YANK LENGTH PASS:', library, f'({capacity}-byte yank)',
                  flush=True)


if __name__ == '__main__':
    main()
