#!/usr/bin/env python3
"""Check production search, navigation and count arithmetic on 16-bit runtimes."""
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

unsigned char vi_char_width[256];
char *vi_file_mem, *vi_file_end, *vi_file_max, *vi_curs_char, *vi_top_char;
char *vi_file_name = "probe";
int vi_rows = 25, vi_columns = 80, vi_curs_col, vi_changed;
unsigned long vi_curs_row, vi_curs_vcol, vi_renum;
static unsigned long received;
static int command, failures;
static char last_message[128];
void normal(int c) { command = c; received = vi_renum; }
void clearlastmess(void) {}
void updatescreen(void) {}
void message(char *s) { strcpy(last_message, s); }
static void check(int ok, int line, char *expression) {
    if (!ok) {
        printf("Failed check at line %d: %s\n", line, expression);
        failures++;
    }
}
#define CHECK(ok) check((ok), __LINE__, #ok)
'''

CHECKS = r'''
static void searches(unsigned size) {
    memset(vi_file_mem, 'x', size);
    vi_file_end = vi_file_mem + size;
    vi_curs_char = vi_file_mem;
    memcpy(vi_file_mem, "aba", 3);
    memcpy(vi_file_end - 5, "ababa", 5);
    CHECK(fwdsearch("aba") == vi_file_end - 5);
    CHECK(bcksearch("aba") == vi_file_end - 3);
    vi_curs_char = vi_file_end - 5;
    CHECK(fwdsearch("aba") == vi_file_end - 3);
    vi_curs_char = vi_file_end - 3;
    CHECK(fwdsearch("aba") == vi_file_mem);
    CHECK(bcksearch("aba") == vi_file_end - 5);
    CHECK(fwdsearch("not here") == NULL && bcksearch("not here") == NULL);
    CHECK(fwdsearch("") == NULL && bcksearch("") == NULL);
    vi_file_end = vi_file_mem + 2;
    vi_curs_char = vi_file_mem;
    CHECK(fwdsearch("aba") == NULL && bcksearch("aba") == NULL);
}
static void lines(unsigned size) {
    char expected[128];
    memset(vi_file_mem, '\n', size);
    vi_file_end = vi_file_mem + size;
    vi_top_char = vi_file_mem;
    vi_curs_char = vi_file_end - 1;
    CHECK(cntlines(vi_file_mem, vi_file_end) == (unsigned long)size + 1UL);
    cursor_position();
    CHECK(vi_curs_row == (unsigned long)size - 1UL);
    gotoline(32767U);
    CHECK(vi_curs_char == vi_file_mem + 32766U);
    gotoline(32768U);
    CHECK(vi_curs_char == vi_file_mem + (size < 32768U ? size - 1U : 32767U));
    gotoline(40000U);
    CHECK(vi_curs_char == vi_file_mem + (size < 40000U ? size - 1U : 39999U));
    gotoline(VI_COUNT_MAX);
    CHECK(vi_curs_char == vi_file_end - 1);
    gotoline(0);
    CHECK(vi_curs_char == vi_file_end - 1);
    cursupdate();
    CHECK(vi_curs_row < (unsigned long)vi_rows - 1UL && vi_curs_col == 0);
    fileinfo();
    sprintf(expected, "\"probe\" line %lu of %lu", (unsigned long)size,
            (unsigned long)size);
    CHECK(!strcmp(last_message, expected));
}
static void columns(void) {
    unsigned long target = 85000UL;
    memset(vi_file_mem, 1, 36001U);
    vi_file_mem[18000U] = '\n';
    vi_file_end = vi_file_mem + 36001U;
    vi_top_char = vi_curs_char = vi_file_mem + 17000U;
    cursor_position();
    CHECK(vi_curs_vcol == target);
    CHECK(coladvance(vi_file_mem, target) == vi_file_mem + 17000U);
    CHECK(onedown(VI_COUNT_MAX));
    CHECK(vi_curs_char == vi_file_mem + 35001U);
    CHECK(oneup(VI_COUNT_MAX));
    CHECK(vi_curs_char == vi_file_mem + 17000U);
    memcpy(vi_file_mem, "\001x\tY\n", 5);
    vi_file_end = vi_file_mem + 5;
    CHECK(coladvance(vi_file_mem, 5UL) == vi_file_mem + 1);
    CHECK(coladvance(vi_file_mem, 6UL) == vi_file_mem + 2);
    CHECK(coladvance(vi_file_mem, 7UL) == vi_file_mem + 2);
    CHECK(coladvance(vi_file_mem, 14UL) == vi_file_mem + 3);
    CHECK(coladvance(vi_file_mem, 100000UL) == vi_file_mem + 3);
    memcpy(vi_file_mem, "a\nlast", 6);
    vi_file_end = vi_file_mem + 6;
    gotoline(0);
    CHECK(vi_curs_char == vi_file_mem + 2);
    vi_file_end = vi_file_mem;
    *vi_file_mem = 0;
    gotoline(0);
    CHECK(vi_curs_char == vi_file_mem);
    CHECK(coladvance(vi_file_mem, 100000UL) == vi_file_mem);
}
static void counts(char *text, unsigned long expected) {
    vi_renum = 0;
    while (*text)
        donormal(*text++);
    donormal('G');
    CHECK(received == expected && command == 'G' && vi_renum == 0);
}
int main(void) {
    static unsigned sizes[] = {32767U, 32768U, 40000U, 40064U};
    unsigned i;
    unsigned long count;
    vi_file_mem = malloc(40065U);
    if (!vi_file_mem) {
        puts("VI NAVIGATION ALLOCATION FAILED");
        return 1;
    }
    vi_file_max = vi_file_mem + 40065U;
    for (i = 0; i < 256; i++)
        vi_char_width[i] = 1;
    vi_char_width[1] = 5;
    vi_char_width[9] = 8;
    for (i = 0; i < sizeof sizes / sizeof sizes[0]; i++) {
        searches(sizes[i]);
        lines(sizes[i]);
    }
    columns();
    counts("32767", 32767UL);
    counts("32768", 32768UL);
    counts("40000", 40000UL);
    counts("65535", 65535UL);
    counts("65536", 65536UL);
    counts("999999999999999999999999999999999999999", 65536UL);
    count = 0;
    for (i = 0; i < 1000; i++)
        count = vi_count_digit(count, 9);
    CHECK(count == 65536UL);
    free(vi_file_mem);
    printf("VI NAVIGATION %s: %d failures\n", failures ? "FAIL" : "PASS", failures);
    return failures != 0;
}
'''


def main():
    source = HARNESS
    for name, signatures in (
            ('linefunc.c', ('unsigned vi_byte_span(', 'unsigned long vi_count_digit(',
                            'char *nextline(', 'char *prevline(', 'char *coladvance(',
                            'static char *fwdsearch(char *str)\n',
                            'static char *bcksearch(char *str)\n')),
            ('misccmds.c', ('unsigned long cntlines(', 'void fileinfo(', 'void gotoline(')),
            ('edit.c', ('static void donormal(int c)\n', 'static void cursor_position(',
                        'static char *next_screen_row(', 'void cursupdate(',
                        'int oneup(', 'int onedown('))):
        contents = (ROOT / name).read_text()
        for signature in signatures:
            source += '\n' + function(contents, signature)
    with tempfile.TemporaryDirectory(prefix='vi-navigation-') as directory:
        work = Path(directory)
        shutil.copyfile(ROOT / 'stevie.h', work / 'stevie.h')
        (work / 'nav.c').write_text(source + CHECKS)
        run([os.environ.get('CC_HOST', 'cc'), '-std=c99', '-g',
             '-fsanitize=address,undefined', '-I.', 'nav.c', '-o', 'nav-host'], work)
        result = run([str(work / 'nav-host')], work)
        assert 'VI NAVIGATION PASS: 0 failures' in result.stdout, result.stdout
        print('NAVIGATION PASS: host sanitizers', flush=True)
        run(['aztec42_cc', '-I.', '+F', '+0', '-o', 'nav.o', 'nav.c'], work)
        for library, extension in (('c86', 'cmd'), ('d11', 'com'), ('c', 'exe')):
            program = 'nav.' + extension
            run(['aztec42_link', '-o', program, 'nav.o', '-l' + library], work)
            result = run([os.environ.get('EMU2', 'emu2'), program], work)
            assert 'VI NAVIGATION PASS: 0 failures' in result.stdout, result.stdout
            print('NAVIGATION PASS:', library, '(large search, lines, columns, counts)',
                  flush=True)


if __name__ == '__main__':
    main()
