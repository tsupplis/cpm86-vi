#!/usr/bin/env python3
"""Test the keyboard module through its public API; mock only hardware calls."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'keyboard.c').read_text()
STUB = r'''
#ifndef TEST_SGTTY_H
#define TEST_SGTTY_H
struct sgttyb { int sg_flags; };
#define CRMOD 16
#define CBREAK 2
#define TIOCSETP 1
int ioctl(int, int, struct sgttyb *);
#endif
'''
PROBE = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "keyboard.h"
#include "sgtty.h"
static int version, keys[128], count, offset, reads, bios_reads, waits;
static int expansions, resets, modes;
static int is_concurrent(void) {
    return (version & 255) >= 0x30 && ((version >> 8) & 5);
}
static void queue(int key) { assert(count < 128); keys[count++] = key; }
static int take_key(void) {
    int key;
    assert(offset < count); key = keys[offset++];
    if (offset == count) count = offset = 0;
    bios_reads++;
    return key;
}
static void on_wait(void) { waits++; queue('z'); }
int osver(void) { return version & 255; }
int ostype(void) { return version >> 8; }
int dosplus_crtreset(void) { resets++; return 0; }
int ioctl(int fd, int request, struct sgttyb *s) {
    assert(fd == 0 && request == TIOCSETP && s->sg_flags == (CRMOD|CBREAK));
    modes++; return 0;
}
int bdos(int fn, int arg) {
    int key;
    if (fn == 2) {
        assert(is_concurrent());
        assert(arg == 27 || arg == '6' || arg == '7');
        expansions++; return 0;
    }
    if (fn == 11) { assert(is_concurrent()); return count ? 255 : 0; }
    assert(fn == 6);
    assert(arg == (is_concurrent() ? 253 : 255));
    reads++;
    if (!count) { assert(arg == 255); return 0; }
    key = keys[offset++];
    if (offset == count) count = offset = 0;
    return key;
}
#include "keyos.c"
int vi_bios_key_read(void) { return take_key(); }
int vi_bios_key_ready(void) { return count != 0; }
#include "keys.c"
static void expect(int value) {
    int before = reads + bios_reads;
    assert(vi_key_peek() == value);
    before = reads + bios_reads;
    assert(vi_key_peek() == value);
    assert(vi_key_read() == value);
    assert(reads + bios_reads == before);
}
static void decode(int input, int expected, int navigation) {
    int direct;
    assert(vi_key_decode_command(input, &direct) == expected);
    assert(direct == navigation);
}
static void check_closed(void) {
    assert(expansions == (is_concurrent() ? 4 : 0));
}
int main(void) {
    int versions[] = {0x1022,0x1431,0x1441,0x1041};
    int v, i, before;
    int scans[] = {0x48,0x50,0x4d,0x4b,0x47,0x49,0x52,0x4f,0x51,0x53};
    int concurrent[] = {0xc8,0xd0,0xcd,0xcb,0xc7,0xc9,0xd2,0xcf,0xd1,0xd3};
    char mapped[] = "ABCDHIL\032\n\177";
    for (v=0; v<4; v++) {
#ifdef __CPM86__
        version = versions[v];
#else
        version = 0;
#endif
        expansions = modes = reads = bios_reads = waits = 0;
        vi_key_init(on_wait);
#ifdef __CPM86__
        assert(modes == 1);
#endif
        assert(expansions == (is_concurrent() ? 2 : 0));
        assert(vi_key_peek() == -1 && waits == 0);
        queue('a'); queue('b'); queue(233);
        expect('a'); expect('b'); expect(233);
        assert(vi_key_peek() == -1 && waits == 0);
        queue(27); queue(8); queue(0x11);
        expect(27); expect(8); expect(0x11);
        for(i=0;i<10;i++) {
            if (is_concurrent()) queue(concurrent[i]);
#if defined(__PCBIOS__) || defined(__MSDOS__)
            else queue(scans[i] << 8);
#else
            else {
                if (i<7) {
                    queue(27);
#ifdef __VT100__
                    queue('[');
#endif
                }
                queue(mapped[i]);
            }
#endif
            if(i<7) {
                expect(27);
#ifdef __VT100__
                expect('[');
#endif
            }
            expect(mapped[i]);
        }
        assert(vi_key_peek() == -1);
        if (is_concurrent()) assert(bios_reads == 0);
#if defined(__PCBIOS__) || defined(__MSDOS__)
        if(!is_concurrent()) {
            queue(0x3b00); assert(vi_key_peek() == -1 && waits == 0);
            assert(vi_key_read() == 'z' && waits == 1);
        }
#endif
        decode('x','x',0);
        decode(27,-1,0);
#ifdef __VT100__
        decode('[',-1,1);
#endif
        decode('A','k',1);
        decode(27,-1,0); decode('x','x',0);
        decode(27,-1,0); decode(27,-1,0);
#ifdef __VT100__
        decode('[',-1,1);
#endif
        decode('H','0',1);
        decode(26,'$',1); decode(10,6,1);
#ifdef __CPM86__
        decode(0x13,'h',0); decode(0x04,'l',0);
        decode(0x11,-1,0); decode('E','0',0);
        decode(0x11,-1,0); decode('X','$',0);
        decode(0x11,-1,0); decode('?',-1,0);
#else
        decode(0x11,0x11,0);
#endif
        /* Closing clears buffered bytes and incomplete decoder prefixes. */
        queue('q'); assert(vi_key_peek() == 'q');
        decode(27,-1,0);
        before = expansions;
        vi_key_close(); vi_key_close();
        assert(expansions == before + (is_concurrent() ? 2 : 0));
        vi_key_init(on_wait);
        assert(vi_key_peek() == -1);
        decode('A','A',0);
        vi_key_close();
    }
    /* Application-owned atexit cleanup must also run on error exit paths. */
    expansions = 0;
    assert(atexit(check_closed) == 0);
    assert(atexit(vi_key_close) == 0);
    vi_key_init(on_wait);
    puts("PASS: OS dispatch, read/peek, navigation, literals, decoding, lifecycle");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='vi-keyboard-') as directory:
    work = Path(directory)
    (work / 'sgtty.h').write_text(STUB)
    (work / 'keys.c').write_text(source)
    (work / 'probe.c').write_text(PROBE)
    profiles = [('cpm52', ['-D__CPM86__', '-D__VTCMD__', '-D__VT52__']),
                ('cpm100', ['-D__CPM86__', '-D__VTCMD__', '-D__VT100__']),
                ('cpmbios', ['-D__CPM86__', '-D__PCBIOS__']),
                ('dos1', ['-D__MSDOS__=1']), ('dos2', ['-D__MSDOS__=2'])]
    for name, flags in profiles:
        subprocess.run([os.environ.get('CC_HOST', 'cc'), '-std=gnu89',
                        '-fsanitize=address,undefined', *flags,
                        '-I'+str(work), '-I'+str(ROOT), str(work/'probe.c'),
                        '-o', str(work/'probe')], check=True)
        subprocess.run([str(work/'probe')], check=True, timeout=10)
        print(name, 'PASS', flush=True)
