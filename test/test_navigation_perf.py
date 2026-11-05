#!/usr/bin/env python3
"""One bounded 8088 cursor/search comparison against frozen pre-P4 functions."""
import argparse
import os
from pathlib import Path
import re
import tempfile

from test_buffer_runtime import ROOT, build
from test_display_pce import run_probe
from test_editor_state import function
from test_navigation_runtime import CHECKS

PROBE = r'''
#include "editor.c"
#include "navfuncs.c"

static unsigned clock_value, cursor_ticks[2], search_ticks[2][2][3];
static int failed_line;
#define REQUIRE(x) if (!(x)) { failed_line = __LINE__; goto finish; }

static unsigned clock_ticks(void)
{
#asm
    push es
    mov ax,40h
    mov es,ax
    mov ax,word ptr es:[6ch]
    mov word ptr clock_value_,ax
    pop es
#endasm
    return clock_value;
}

int main(void)
{
    static char *patterns[] = {"aaaaab", "abaaa", "baaaaa"};
    void (*position)(void);
    char *(*search)(char *);
    FILE *report;
    unsigned variant, direction, pattern, i, start;
    REQUIRE(vi_yank_init());
    windinit();
    screenalloc();
    filealloc();
    hexchars();
    memset(vi_file_mem, 'a', 8192U);
    vi_file_end = vi_file_mem + 8192U;
    vi_top_char = vi_file_mem + 4080U;
    vi_curs_char = vi_file_mem + 4095U;
    for (variant = 0; variant < 2; variant++) {
        position = variant ? current_cursor_position : reference_cursor_position;
        start = clock_ticks();
        for (i = 0; i < 8; i++) position();
        cursor_ticks[variant] = clock_ticks() - start;
        REQUIRE(vi_curs_row == 0 && vi_curs_col == 15 &&
                vi_curs_vcol == 4095UL);
        for (direction = 0; direction < 2; direction++) {
            search = variant ? (direction ? current_backward : current_forward) :
                               (direction ? reference_backward : reference_forward);
            for (pattern = 0; pattern < 3; pattern++) {
                start = clock_ticks();
                for (i = 0; i < 2; i++)
                    REQUIRE(search(patterns[pattern]) == NULL);
                search_ticks[variant][direction][pattern] = clock_ticks() - start;
                REQUIRE(vi_curs_char == vi_file_mem + 4095U);
            }
        }
    }
finish:
    vi_key_exit();
    vi_yank_close();
    report = fopen("RESULT.TXT", "w");
    if (report == NULL) return 1;
    fprintf(report, "VI NAV PERF %s\n", failed_line ? "FAIL" : "PASS");
    if (failed_line)
        fprintf(report, "failed line %d\n", failed_line);
    else {
        fprintf(report, "cursor repeats 8 ticks %u %u\n", cursor_ticks[0],
                cursor_ticks[1]);
        for (direction = 0; direction < 2; direction++)
            for (pattern = 0; pattern < 3; pattern++)
                fprintf(report, "search %u %s repeats 2 ticks %u %u\n", direction,
                        patterns[pattern], search_ticks[0][direction][pattern],
                        search_ticks[1][direction][pattern]);
    }
    return fclose(report) != 0 || failed_line != 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Save the native report')
    args = parser.parse_args()
    functions = '\n'.join(function(CHECKS, signature) for signature in (
        'static char *reference_forward(char *str)',
        'static char *reference_backward(char *str)',
        'static void reference_cursor_position(void)'))
    for file, signature, original, replacement in (
            ('edit.c', 'static void cursor_position(void)\n',
             'cursor_position(', 'current_cursor_position('),
            ('linefunc.c', 'static char *fwdsearch(char *str)\n',
             'fwdsearch(', 'current_forward('),
            ('linefunc.c', 'static char *bcksearch(char *str)\n',
             'bcksearch(', 'current_backward(')):
        functions += '\n' + function((ROOT / file).read_text(), signature).replace(
            original, replacement)
    with tempfile.TemporaryDirectory(prefix='vi-nav-perf-') as directory:
        work = Path(directory)
        (work / 'navfuncs.c').write_text(functions)
        with tempfile.TemporaryDirectory(prefix='vi-nav-compiler-') as compiler:
            previous = os.environ.get('TMPDIR')
            os.environ['TMPDIR'] = compiler
            try:
                build(work, ('vid1bios.exe',), PROBE)
            finally:
                if previous is None:
                    del os.environ['TMPDIR']
                else:
                    os.environ['TMPDIR'] = previous
        dos = Path(os.environ.get(
            'DOS11_SOURCE', Path.home() / 'Projects/DOS/pcdos11-hacking'))
        report = run_probe(work, 'navigation', dos / 'pcdos_base.img',
                           dos / 'pcdos.cfg', dos / 'pce/pceexit.com',
                           'vid1bios.exe', 'cga', ram=256, timeout=60)
        assert report.startswith('VI NAV PERF PASS\n'), report
        assert re.search(r'^cursor repeats 8 ticks \d+ \d+$', report, re.M), report
        cases = re.findall(r'^search ([01]) (\w+) repeats 2 ticks (\d+) (\d+)$',
                           report, re.M)
        assert len(cases) == 6 and {(direction, pattern) for direction, pattern,
                                   _, _ in cases} == {
            (str(direction), pattern) for direction in (0, 1)
            for pattern in ('aaaaab', 'abaaa', 'baaaaa')}, report
        if args.output:
            args.output.write_text(report)


if __name__ == '__main__':
    main()
