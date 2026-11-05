#!/usr/bin/env python3
"""Host tests of the real concurrent adapter and windgetc dispatch."""
from pathlib import Path
import os
import subprocess
import tempfile
from test_editor_state import function

root = Path(__file__).resolve().parents[1]
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
static int peeked = -1;
int dosplus_crtreset(void) { crt_resets++; return 0; }
static void check(int ok) { if (!ok) { fputs("keyboard check failed\n", stderr); exit(1); } }
int osver(void) { return version & 255; }
int ostype(void) { return version >> 8; }
int bdos(int fn, int arg) {
    if (fn == 2) { check(nout < 32); output[nout++] = arg; return 0; }
    check(fn == 6 && arg == 255); inputs++; return input;
}
static int getch(int wait) { legacy_calls++; return 'x'; }
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

raw = edit[edit.index('#if defined(__PCBIOS__)'):edit.index('void edit(void)')]
raw = raw.replace(function(edit, 'static int bioskey(void)'),
                  'static int bioskey(void) { return take_key(); }')
raw = raw.replace(function(edit, 'static int keyready(void)'),
                  'static int keyready(void) { return key_count != 0; }')
poll_probe = r'''
#include <assert.h>
#include <stdio.h>
#include "stevie.h"
#include "keyboard.h"
static int keys[16], key_count, key_offset;
static int take_key(void) {
    assert(key_count > 0);
    key_count--;
    return keys[key_offset++];
}
static void queue(int a, int b, int c) {
    assert(!key_count);
    key_offset = 0;
    keys[0] = a; keys[1] = b; keys[2] = c;
    key_count = c >= 0 ? 3 : b >= 0 ? 2 : 1;
}
int vi_os_concurrent(void) { return CONCURRENT; }
int bdos(int fn, int arg) {
    if (fn == 2) return 0;
    if (fn == 11) return key_count ? 255 : 0;
    assert(fn == 6 && arg == 255);
    return key_count ? take_key() : 0;
}
void windrefreshcursor(void) { assert(0); }
''' + raw + r'''
int main(void) {
    vi_key_init(1);
    assert(windpeek() == -1);
    queue('a', 'b', 'c');
    assert(windpeek() == 'a' && windpeek() == 'a');
    assert(windgetc() == 'a');
    assert(windpeek() == 'b' && windgetc() == 'b');
    assert(windpeek() == 'c' && windgetc() == 'c');
    assert(windpeek() == -1);
    queue(27, 8, 233);
    assert(windpeek() == 27 && windgetc() == 27);
    assert(windpeek() == 8 && windgetc() == 8);
    assert(windpeek() == 233 && windgetc() == 233);
    assert(windpeek() == -1);
#if defined(__PCBIOS__) && !CONCURRENT
    {
        static int scans[] = {0x48,0x50,0x4d,0x4b,0x47,0x49,0x52,0x51,0x4f,0x53};
        static char mapped[] = "ABCDHIL\n\032\177";
        int i;
        for (i = 0; i < 10; i++) {
            queue(scans[i] << 8, -1, -1);
            if (i < 7)
                assert(windpeek() == 27 && windgetc() == 27);
            assert(windpeek() == mapped[i] && windgetc() == mapped[i]);
        }
    }
    queue(0x3b00, -1, -1);
    assert(windpeek() == -1);
#elif CONCURRENT
    queue(0xcd, -1, -1);
    assert(windpeek() == 27 && windgetc() == 27);
    assert(windpeek() == '[' && windgetc() == '[');
    assert(windpeek() == 'C' && windgetc() == 'C');
#endif
    assert(windpeek() == -1);
    vi_key_exit();
    puts("PASS: nonblocking keyboard peek, retained controls and extended keys");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='vi-key-peek-') as folder:
    work = Path(folder)
    (work / 'peek.c').write_text(poll_probe)
    for flags in (['-D__PCBIOS__', '-DCONCURRENT=0'],
                  ['-D__VTCMD__', '-DCONCURRENT=0'],
                  ['-D__PCBIOS__', '-DCONCURRENT=1']):
        subprocess.run([os.environ.get('CC_HOST', 'cc'), '-std=gnu89',
                        '-D__CPM86__', *flags, '-fsanitize=address,undefined',
                        '-I' + str(root), str(work / 'peek.c'),
                        str(root / 'keyboard.c'), '-o', str(work / 'peek')],
                       check=True)
        subprocess.run([str(work / 'peek')], check=True, timeout=10)
