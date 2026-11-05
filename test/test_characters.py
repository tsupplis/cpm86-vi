#!/usr/bin/env python3
"""Check all display bytes/bases and compare old/compact cached rendering."""
import argparse
import os
from pathlib import Path
import re
import shutil
import tempfile

from test_buffer_runtime import ROOT, build, run
from test_display_pce import run_probe
from test_editor_state import function

CHECKS = r'''
#include <stdio.h>
#include <string.h>
#include "stevie.h"

int main(void)
{
    static int bases[] = {8, 16, 10, 16, 8, 10};
    char expected[6];
    unsigned c, mode, width;
    for (mode = 0; mode < sizeof bases / sizeof bases[0]; mode++) {
        if (bases[mode] == 8) octchars();
        else if (bases[mode] == 16) hexchars();
        else decchars();
        for (c = 0; c < 256; c++) {
            width = c == 10 || c == 13 || (c >= 32 && c < 127) ? 1 : 5;
            if (vi_char_width[c] != width) return 1;
            if (width == 1) continue;
            if (bases[mode] == 8) sprintf(expected, "[%03o]", c);
            else if (bases[mode] == 16) sprintf(expected, "[x%02x]", c);
            else sprintf(expected, "[%3u]", c);
            if (strcmp(vi_char_text((unsigned char)c), expected)) {
                printf("VI CHARACTERS FAIL: base %d byte %u\n", bases[mode], c);
                return 1;
            }
        }
    }
    for (c = 0; c < 256; c++) {
        width = c >= '0' && c <= '9' ? c - '0' :
                c >= 'a' && c <= 'f' ? c - 'a' + 10 :
                c >= 'A' && c <= 'F' ? c - 'A' + 10 : (unsigned)-1;
        if (hextoint(c) != (int)width) return 1;
    }
    if (hextoint(-1) != -1 || hextoint(256) != -1) return 1;
    puts("VI CHARACTERS PASS");
    return 0;
}
'''

REFERENCE = r'''
struct reference_charinfo { char ch_size; char *ch_str; };
static struct reference_charinfo reference_chars[256];
static char reference_text[159][6];

static void reference_mode(unsigned base)
{
    unsigned c, slot = 0;
    char *p;
    for (c = 0; c < 256; c++) {
        reference_chars[c].ch_size =
            c == 10 || c == 13 || (c >= 32 && c < 127) ? 1 : 5;
        reference_chars[c].ch_str = NULL;
        if (reference_chars[c].ch_size == 1) continue;
        p = reference_text[slot++];
        reference_chars[c].ch_str = p;
        if (base == 8) sprintf(p, "[%03o]", c);
        else if (base == 16) sprintf(p, "[x%02x]", c);
        else sprintf(p, "[%3u]", c);
    }
}
'''

PROBE = r'''
#include "editor.c"
#include "charref.c"

static unsigned clock_value, timings[2][3][2];
static char reference_image[VI_SCREEN_IMAGE_SIZE];
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
    static unsigned bases[] = {8, 16, 10};
    char *bottom;
    FILE *report;
    unsigned base, pattern, variant, i, row, start;
    REQUIRE(vi_yank_init());
    windinit();
    screenalloc();
    filealloc();
    REQUIRE(vi_rows == 25 && vi_columns == 80);
    vi_state = NORMAL;
    for (base = 0; base < 3; base++) {
        reference_mode(bases[base]);
        if (base == 0) octchars();
        else if (base == 1) hexchars();
        else decchars();
        for (pattern = 0; pattern < 3; pattern++) {
            for (i = 0; i < 512; i++) {
                unsigned c = i % 256U;
                vi_file_mem[i] = pattern == 0 ? 'A' :
                    pattern == 1 && reference_chars[c].ch_size == 1 ? 1 : c;
            }
            vi_top_char = vi_file_mem;
            vi_file_end = vi_file_mem + 512;
            memset(screen_line, 'Z', 80);
            for (row = 0; row < 25; row++)
                REQUIRE(vi_screen_store(VI_SCREEN_NEXT, row, screen_line));
            reference_filetonext();
            bottom = vi_bot_char;
            for (row = 0; row < 25; row++)
                REQUIRE(vi_screen_load(VI_SCREEN_NEXT, row,
                                      reference_image + row * 80));
            filetonext();
            REQUIRE(vi_bot_char == bottom);
            for (row = 0; row < 25; row++) {
                REQUIRE(vi_screen_load(VI_SCREEN_NEXT, row, screen_line));
                REQUIRE(!memcmp(screen_line, reference_image + row * 80, 80));
            }
            if (pattern == 2) continue;
            for (variant = 0; variant < 2; variant++) {
                start = clock_ticks();
                for (i = 0; i < 4; i++) {
                    if (variant == 0) reference_filetonext();
                    else filetonext();
                }
                timings[variant][base][pattern] = clock_ticks() - start;
            }
        }
    }
finish:
    vi_key_exit();
    vi_yank_close();
    report = fopen("RESULT.TXT", "w");
    if (report == NULL) return 1;
    fprintf(report, "VI CHARACTER RENDER %s\n", failed_line ? "FAIL" : "PASS");
    if (failed_line)
        fprintf(report, "failed line %d\n", failed_line);
    else {
        fprintf(report, "legacy storage %u width storage %u repeats 4\n",
                (unsigned)(sizeof reference_chars + sizeof reference_text),
                (unsigned)sizeof vi_char_width);
        for (base = 0; base < 3; base++)
            for (pattern = 0; pattern < 2; pattern++)
                fprintf(report, "base %u pattern %u ticks %u %u\n", bases[base],
                        pattern, timings[0][base][pattern],
                        timings[1][base][pattern]);
    }
    return fclose(report) != 0 || failed_line != 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timing', action='store_true',
                        help='One bounded native renderer comparison')
    parser.add_argument('--output', type=Path, help='Save the native timing report')
    args = parser.parse_args()
    if args.output and not args.timing:
        parser.error('--output requires --timing')
    with tempfile.TemporaryDirectory(prefix='vi-characters-') as directory:
        work = Path(directory)
        shutil.copyfile(ROOT / 'stevie.h', work / 'stevie.h')
        shutil.copyfile(ROOT / 'hexchars.c', work / 'hexchars.c')
        (work / 'check.c').write_text(CHECKS)
        run([os.environ.get('CC_HOST', 'cc'), '-std=c99', '-g',
             '-fsanitize=address,undefined', '-I.', 'check.c', 'hexchars.c',
             '-o', 'check-host'], work)
        result = run([str(work / 'check-host')], work)
        assert result.stdout.strip() == 'VI CHARACTERS PASS', result.stdout
        print('CHARACTERS PASS: host sanitizers (all bytes, bases and mode switches)',
              flush=True)
        with tempfile.TemporaryDirectory(prefix='vi-characters-compiler-') as compiler:
            previous = os.environ.get('TMPDIR')
            os.environ['TMPDIR'] = compiler
            try:
                for source in ('check', 'hexchars'):
                    run(['aztec42_cc', '-I.', '+F', '+0', '-o', source + '.o',
                         source + '.c'], work)
                for library, extension in (('c86', 'cmd'), ('d11', 'com'), ('c', 'exe')):
                    program = 'check.' + extension
                    run(['aztec42_link', '-o', program, 'check.o', 'hexchars.o',
                         '-l' + library], work)
                    result = run([os.environ.get('EMU2', 'emu2'), program], work)
                    assert 'VI CHARACTERS PASS' in result.stdout, result.stdout
                    print('CHARACTERS PASS:', library, flush=True)
                if args.timing:
                    renderer = function((ROOT / 'main.c').read_text(),
                                        'static void filetonext(void) {')
                    renderer = renderer.replace('filetonext(', 'reference_filetonext(')
                    renderer = renderer.replace('vi_char_width[c]',
                                                'reference_chars[c].ch_size')
                    renderer = renderer.replace('vi_char_text((unsigned char)c)',
                                                'reference_chars[c].ch_str')
                    assert 'vi_char_' not in renderer, renderer
                    (work / 'charref.c').write_text(REFERENCE + renderer)
                    build(work, ('vid1bios.exe',), PROBE)
                    dos = Path(os.environ.get(
                        'DOS11_SOURCE', Path.home() / 'Projects/DOS/pcdos11-hacking'))
                    report = run_probe(work, 'characters', dos / 'pcdos_base.img',
                                       dos / 'pcdos.cfg', dos / 'pce/pceexit.com',
                                       'vid1bios.exe', 'cga', ram=256, timeout=60)
                    assert report.startswith('VI CHARACTER RENDER PASS\n'), report
                    cases = re.findall(r'^base (\d+) pattern (\d) ticks (\d+) (\d+)$',
                                       report, re.M)
                    assert {(int(base), int(pattern)) for base, pattern, _, _ in cases} == {
                        (base, pattern) for base in (8, 16, 10) for pattern in (0, 1)}
                    assert len(cases) == 6, report
                    if args.output:
                        args.output.write_text(report)
            finally:
                if previous is None:
                    del os.environ['TMPDIR']
                else:
                    os.environ['TMPDIR'] = previous


if __name__ == '__main__':
    main()
