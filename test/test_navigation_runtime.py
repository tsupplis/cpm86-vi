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
static unsigned long comparisons;
static int counted_memcmp(const void *a, const void *b, size_t n) {
    comparisons++;
    return memcmp(a, b, n);
}
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
static char *reference_forward(char *str)
{
    unsigned length = strlen(str);
    char *p, *last;
    if (length == 0 || length > vi_byte_span(vi_file_mem, vi_file_end))
        return NULL;
    last = vi_file_end - length;
    p = vi_curs_char < vi_file_end ? vi_curs_char + 1 : vi_file_end;
    for (; p <= last; p++)
        if (!memcmp(p, str, length)) return p;
    for (p = vi_file_mem; p <= last && p <= vi_curs_char; p++)
        if (!memcmp(p, str, length)) return p;
    return NULL;
}

static char *reference_backward(char *str)
{
    unsigned length = strlen(str);
    char *p, *last;
    if (length == 0 || length > vi_byte_span(vi_file_mem, vi_file_end))
        return NULL;
    last = vi_file_end - length;
    p = vi_curs_char > last ? last + 1 : vi_curs_char;
    while (p > vi_file_mem) {
        p--;
        if (!memcmp(p, str, length)) return p;
    }
    p = last + 1;
    while (p > vi_curs_char) {
        p--;
        if (!memcmp(p, str, length)) return p;
    }
    return NULL;
}

static void reference_cursor_position(void)
{
    char *p;
    int c, n;
    vi_curs_row = vi_curs_col = vi_curs_vcol = 0;
    for (p = vi_top_char; p < vi_curs_char; p++) {
        c = (unsigned char)*p;
        if (c == '\n') {
            vi_curs_row++;
            vi_curs_col = 0;
        } else {
            n = vi_char_width[c];
            while (n-- > 0) {
                if (vi_curs_col == vi_columns) {
                    vi_curs_row++;
                    vi_curs_col = 0;
                }
                vi_curs_col++;
            }
        }
    }
    if (vi_curs_col == vi_columns) {
        if (vi_curs_char < vi_file_end && *vi_curs_char == '\n')
            vi_curs_col--;
        else {
            vi_curs_row++;
            vi_curs_col = 0;
        }
    }
    p = vi_curs_char;
    while (p > vi_file_mem && p[-1] != '\n') p--;
    while (p < vi_curs_char)
        vi_curs_vcol += vi_char_width[(unsigned char)*p++];
}

static void parity(void)
{
    static char *patterns[] = {
        "", "a", "b", "aaaaab", "abaaa", "aba", "aa", "abab",
        "baaaaa", "\377a", "\001", "\r\n", "aaaaaaaaa"
    };
    unsigned trial, length, i, j, position, top;
    unsigned long random = 17, row, column;
    int col;
    char pattern[10];
    for (trial = 0; trial < 128; trial++) {
        length = trial % 97;
        for (i = 0; i < length; i++) {
            random = random * 1664525UL + 1013904223UL;
            vi_file_mem[i] = random % 8 == 0 ? 0 :
                            random % 8 == 1 ? 255 :
                            random % 8 == 2 ? '\n' : 'a' + random % 3;
        }
        vi_file_end = vi_file_mem + length;
        for (position = 0; position <= length; position++) {
            vi_curs_char = vi_file_mem + position;
            for (j = 0; j < sizeof patterns / sizeof patterns[0]; j++) {
                CHECK(fwdsearch(patterns[j]) == reference_forward(patterns[j]));
                CHECK(bcksearch(patterns[j]) == reference_backward(patterns[j]));
            }
            if (position < length && vi_file_mem[position] != 0) {
                i = 0;
                while (i < 9 && position + i < length &&
                       vi_file_mem[position + i] != 0) {
                    pattern[i] = vi_file_mem[position + i];
                    i++;
                }
                pattern[i] = 0;
                CHECK(fwdsearch(pattern) == reference_forward(pattern));
                CHECK(bcksearch(pattern) == reference_backward(pattern));
            }
            top = position / 2;
            vi_top_char = vi_file_mem + top;
            vi_columns = 1 + trial % 80;
            reference_cursor_position();
            row = vi_curs_row; col = vi_curs_col; column = vi_curs_vcol;
            cursor_position();
            CHECK(vi_curs_row == row && vi_curs_col == col &&
                  vi_curs_vcol == column);
        }
    }
    vi_columns = 80;
    memset(vi_file_mem, 'a', 8192U);
    vi_file_end = vi_file_mem + 8192U;
    vi_curs_char = vi_file_mem + 4095U;
    for (j = 3; j <= 8; j++) {
        if (j != 3 && j != 4 && j != 8) continue;
        comparisons = 0;
        CHECK(fwdsearch(patterns[j]) == NULL);
        CHECK(comparisons == 0);
        CHECK(bcksearch(patterns[j]) == NULL);
        CHECK(comparisons == 0);
    }
}

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
    parity();
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
            if 'search(char *str)' in signature:
                source += '\n#define memcmp counted_memcmp\n'
            source += '\n' + function(contents, signature)
            if 'search(char *str)' in signature:
                source += '\n#undef memcmp\n'
    with tempfile.TemporaryDirectory(prefix='vi-navigation-') as directory:
        work = Path(directory)
        shutil.copyfile(ROOT / 'stevie.h', work / 'stevie.h')
        (work / 'nav.c').write_text(source + CHECKS)
        run([os.environ.get('CC_HOST', 'cc'), '-std=c99', '-g',
             '-fsanitize=address,undefined', '-I.', 'nav.c', '-o', 'nav-host'], work)
        result = run([str(work / 'nav-host')], work)
        assert 'VI NAVIGATION PASS: 0 failures' in result.stdout, result.stdout
        print('NAVIGATION PASS: host sanitizers', flush=True)
        run(['aztec43_acc', '-I.', '-squeeze', '-c', '-o', 'nav.o', 'nav.c'], work)
        for target_flag, extension, library in (('-target=cpm86', 'cmd', 'c86'), ('-target=dos1', 'com', 'd11'), ('-target=dos2', 'exe', 'c')):
            program = 'nav.' + extension
            run(['aztec43_acc', target_flag, '-o', program, 'nav.o'], work)
            result = run([os.environ.get('EMU2', 'emu2'), program], work)
            assert 'VI NAVIGATION PASS: 0 failures' in result.stdout, result.stdout
            print('NAVIGATION PASS:', library, '(large search, lines, columns, counts)',
                  flush=True)


if __name__ == '__main__':
    main()
