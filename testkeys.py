#!/usr/bin/env python3
"""Host tests of the real concurrent adapter and windgetc dispatch."""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parent
edit = (root / 'edit.c').read_text()
start = edit.index('int windgetc(void)')
end = edit.index('\n}', start) + 2
wrapper = edit[start:end]
source = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int version, inputs, nout, legacy_calls;
static unsigned char output[32];
static int input, crt_resets;
int dosplus_crtreset(void) { crt_resets++; return 0; }
static void check(int ok) { if (!ok) { fputs("keyboard check failed\n", stderr); exit(1); } }
int osver(void) { return version & 255; }
int ostype(void) { return version >> 8; }
int bdos(int fn, int arg) {
    if (fn == 2) { check(nout < 32); output[nout++] = arg; return 0; }
    check(fn == 6 && arg == 255); inputs++; return input;
}
static int getch(void) { legacy_calls++; return 'x'; }
#include "keyos.c"
#include "keyboard.c"
''' + wrapper + r'''
int main(void) {
    int ansi, i, n;
    int keys[] = {0xC8,0xD0,0xCD,0xCB,0xC7,0xC9,0xD2,0xCF,0xD1,0xD3};
    char letters[] = "ABCDHIL";
    int direct[] = {26,10,127};
    version = 0x1431;
    for (ansi = 0; ansi <= 1; ansi++) {
        nout = 0;
        vi_key_init(ansi);
        check(vi_key_concurrent() && nout == 2 && !memcmp(output,"\0336",2));
        for (i = 0; i < 10; i++) {
            input = keys[i]; n = inputs;
            if (i < 7) {
                check(windgetc() == 27);
                if (ansi) check(windgetc() == '[');
                check(windgetc() == letters[i]);
            } else check(windgetc() == direct[i-7]);
            check(inputs == n+1 && legacy_calls == 0);
        }
        input = 0xE9; check(windgetc() == 0xE9); /* do not mask text to 7 bits */
        input = 27; check(windgetc() == 27); /* literal Esc */
        vi_key_exit(); vi_key_exit();
        check(!vi_key_concurrent() && nout == 4 && !memcmp(output,"\0336\0337",4));
    }
    version = 0x1022; nout = 0;
    vi_key_init(0); check(!vi_key_concurrent() && windgetc() == 'x');
    vi_key_exit(); check(nout == 0);
    version = 0x1041; vi_key_init(0); check(!vi_key_concurrent());
    version = 0x1422; vi_key_init(0); check(!vi_key_concurrent());
    version = 0x1041; vi_os_close(); check(crt_resets == 1);
    version = 0x1441; vi_os_close(); check(crt_resets == 1);
    version = 0x1431; vi_os_close(); check(crt_resets == 1);
    version = 0x1022; vi_os_close(); check(crt_resets == 1);
    puts("PASS: VI raw keys, terminal sequences, unsigned bytes, legacy gate and no BIOS dispatch concurrently");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='vi-keys-') as folder:
    work = Path(folder)
    (work / 'keys.c').write_text(source)
    binary = work / 'keys'
    subprocess.run([os.environ.get('CC_HOST','cc'),'-std=gnu89','-D__CPM86__',
                    '-fsanitize=address,undefined','-I'+str(root),str(work/'keys.c'),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
