#!/usr/bin/env python3
"""Host regression of the editor's actual linewise yank/delete/paste functions.

Run: python3 test_eof_lines.py
Uses the same dd/undo sequence as normal.c, with screen and undo bookkeeping
stubbed out. Compiler sanitizers catch physical memory errors as well.
"""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent


def function(source, signature):
    start = source.index(signature)
    pos = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[pos] == '{') - (source[pos] == '}')
        pos += 1
    return source[start:pos]


def main():
    source = (ROOT / 'misccmds.c').read_text()
    lines = (ROOT / 'linefunc.c').read_text()
    harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define NORMAL 0
#define CHANGED vi_changed=1
static char memory[512];
char *vi_file_mem=memory, *vi_file_end, *vi_file_max=memory+sizeof memory;
char *vi_curs_char, *vi_uncurs_char;
int vi_renum, vi_changed, vi_state;
char vi_undo_buff[1024], vi_redo_buff[1024];
static char *savedline;
static int savednum, savedcount;
void message(char *s) {(void)s;}
void updatescreen(void) {}
void resetundo(void) {}
void beginline(void) {
    while(vi_curs_char > vi_file_mem && vi_curs_char[-1] != '\n')
        vi_curs_char--;
}
void inschar(int c);
static int canincrease(int n);
'''
    harness += function(lines, 'char *prevline(char *curr)')
    for sig in ('static int canincrease(int n)\n', 'void inschar(int c)',
                'void yankline(int n)', 'void putline(int k)',
                'void delline(int nlines)'):
        harness += '\n' + function(source, sig)
    harness += r'''
void load(const char *disk) {
    const unsigned char *p=(const unsigned char *)disk;
    memset(memory, 0, sizeof memory);
    vi_file_end=memory;
    /* Match readfile's text handling: discard CR, stop at SUB. */
    while(*p && *p!=26) {
        if(*p!='\r') *vi_file_end++=*p;
        p++;
    }
    memory[400]='\n'; /* deterministic unused bytes beyond logical EOF */
    vi_curs_char=memory;
}
void expect(const char *s) {
    assert(vi_file_end-memory==(long)strlen(s));
    assert(memcmp(memory,s,strlen(s))==0);
    assert(vi_curs_char>=memory && vi_curs_char<=vi_file_end);
}
void roundtrip(const char *disk, int offset, int count, const char *deleted,
               const char *original) {
    char *before;
    int below;
    load(disk);
    vi_curs_char=memory+offset;
    beginline(); before=vi_curs_char;
    vi_renum=count;
    yankline(count);
    assert(savednum<=vi_file_end-before);
    delline(count);
    beginline();
    below=vi_curs_char<before;
    expect(deleted);
    /* normal.c chooses p after backing up, otherwise P; u replays it. */
    putline(below?0:1);
    expect(original);
}
int main(void) {
    roundtrip("first line\r\nsecond line\032",11,1,"first line\n",
              "first line\nsecond line");
    roundtrip("first line\nsecond line",11,1,"first line\n",
              "first line\nsecond line");
    roundtrip("first line\r\nsecond line\r\n\032",11,1,"first line\n",
              "first line\nsecond line\n");
    roundtrip("only\032",0,1,"","only");
    roundtrip("first\nsecond\nlast\032",6,9,"first\n","first\nsecond\nlast");
    roundtrip("first\nsecond\032",0,9,"","first\nsecond");
    roundtrip("a\n\n",2,1,"a\n","a\n\n");
    roundtrip("a\nlast",0,1,"last","a\nlast");
    load("a\nlast"); vi_curs_char=memory+2; yankline(1);
    vi_curs_char=memory; putline(1); expect("last\na\nlast");
    load("a\nlast"); vi_curs_char=memory+2; yankline(1);
    putline(0); expect("a\nlast\nlast");
    load("a\nlast"); vi_curs_char=memory+2; yankline(99);
    assert(savedcount==1);
    free(savedline);
    puts("PASS: 11 EOF line deletion/undo/paste checks");
    return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix='vi-eof-') as tmp:
        cfile = Path(tmp) / 'check.c'
        exe = Path(tmp) / 'check'
        cfile.write_text(harness)
        subprocess.run([os.environ.get('CC', 'cc'), '-g', '-fsanitize=address,undefined',
                        str(cfile), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    main()
