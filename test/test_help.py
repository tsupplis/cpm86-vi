#!/usr/bin/env python3
"""Verify full help and the VI_TINY omission without changing editor state."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROBE = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "stevie.h"
int vi_rows = 25;
static int visible = 1, reads, clears, redraws, length;
static char output[4096], status[128];
void windcursor(int on) { visible = on; }
void windclear(void) { clears++; }
void windgoto(int r, int c) { assert(r >= 0 && r < vi_rows && c == 0); }
void windputc(int c) {
    assert(!visible && length < sizeof output - 1);
    output[length++] = c;
}
void windcolor(int color) { assert(color == 2); }
void windcolorreset(void) {}
void windrefresh(void) {}
int vgetc(void) { assert(visible); reads++; return ' '; }
void screenclear(void) {}
void updatescreen(void) { redraws++; }
void message(char *s) { strcpy(status, s); }
int main(void) {
    help();
    assert(visible);
#ifdef VI_TINY
    assert(!reads && !clears && !redraws && !length);
    assert(strstr(status, "Help omitted"));
#else
    assert(reads == 1 && clears == 1 && redraws == 1);
    assert(strstr(output, "Movement") && strstr(output, "set single mark"));
#endif
    return 0;
}
'''


def main():
    with tempfile.TemporaryDirectory(prefix='vi-help-') as directory:
        work = Path(directory)
        (work / 'probe.c').write_text(PROBE)
        for name, flags in (('full', []), ('tiny', ['-DVI_TINY'])):
            binary = work / name
            subprocess.run(
                [os.environ.get('CC_HOST', 'cc'), '-std=c99',
                 '-fsanitize=address,undefined', *flags, '-I' + str(ROOT),
                 str(work / 'probe.c'), str(ROOT / 'help.c'), '-o', str(binary)],
                check=True)
            subprocess.run([str(binary)], check=True)
            print('HELP PASS:', name, flush=True)


if __name__ == '__main__':
    main()
