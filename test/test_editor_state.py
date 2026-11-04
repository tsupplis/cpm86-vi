#!/usr/bin/env python3
"""Host regression tests for save/read failures, replacement and repeat search."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def function(source, signature):
    start = source.index(signature)
    pos = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[pos] == '{') - (source[pos] == '}')
        pos += 1
    return source[start:pos]


HARNESS = r'''
#include <assert.h>
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stevie.h"

static const char *input;
static int quit_calls, reject_save;
static char last_output[256];
void windgoto(int r, int c) {}
void windcolor(int fg) {}
void windcolorreset(void) {}
void windputc(int c) {}
void windrefresh(void) {}
void windstr(char *s) {
    snprintf(last_output, sizeof last_output, "%s", s);
}
void updatescreen(void) {}
void cursupdate(void) {}
void screenclear(void) {}
void beep(void) {}
void help(void) {}
void getout(void) { quit_calls++; }
void vi_key_exit(void) { assert(0); }
char *viversion(void) { return "test"; }
int vgetc(void) { assert(input && *input); return (unsigned char)*input++; }
void beginline(void) {
    while(vi_curs_char > vi_file_mem && vi_curs_char[-1] != '\n')
        vi_curs_char--;
}
int oneright(void) { assert(0); return 0; }
int oneleft(void) { assert(0); return 0; }
int oneup(int n) { assert(0); return 0; }
int onedown(int n) { assert(0); return 0; }
void opencmd(void) { assert(0); }
int issepchar(int c) { return strchr(WORDSEP, c) != NULL; }
int cntlines(char *a, char *b) {
    int n = 1;
    while(a < b) if(*a++ == '\n') n++;
    return n;
}
void fileinfo(void) {}
void gotoline(int n) {}
void yankline(int n) { assert(0); }
void putline(int n) { assert(0); }
void inschar(int c) { assert(0); }
void delchar(void) { assert(0); }
void deleol(void) { assert(0); }
void delword(int n) { assert(0); }
void delline(int n) { assert(0); }
void stuffin(char *s) { assert(0); }
void octchars(void) {}
void hexchars(void) {}
void decchars(void) {}
void addtobuff(char *s, int a, int b, int c, int d, int e, int f) {
    int values[6], i;
    values[0]=a; values[1]=b; values[2]=c;
    values[3]=d; values[4]=e; values[5]=f;
    for(i=0; i<6; i++) {
        *s++ = values[i];
        if(!values[i]) return;
    }
}
const char *vi_save_file(const char *n, const char *a, const char *b, int binary) {
    assert(a == vi_file_mem && b == vi_file_end);
    return reject_save ? "Injected save failure" : NULL;
}
long vi_file_length(const char *name) { return -1L; }
'''

CHECKS = r'''
static void load(const char *s) {
    memset(vi_file_mem, 0, FILELENG);
    memcpy(vi_file_mem, s, strlen(s));
    vi_file_end = vi_file_mem + strlen(s);
    vi_top_char = vi_curs_char = vi_file_mem;
    vi_changed = vi_binary = vi_renum = 0;
    resetundo();
}
static void command(const char *s) {
    input = s;
    readcmdline(':');
    assert(!*input);
}
static void check_save(void) {
    load("abc\n");
    reject_save = 1;
    vi_changed = 1;
    command("w\n");
    assert(vi_changed && !strcmp(last_output, "Injected save failure"));
    command("q\n"); assert(quit_calls == 0);
    command("wq\n"); assert(vi_changed && quit_calls == 0);
    command("x\n"); assert(vi_changed && quit_calls == 0);
    reject_save = 0;
    command("w\n"); assert(!vi_changed);
    command("q\n"); assert(quit_calls == 1);
    load("abc\n");
    reject_save = 1;
    command("w\n"); assert(!vi_changed);
    reject_save = 0;
}
static void check_read(void) {
    char *end, *cursor, *top, *name;
    FILE *f;
    int dirty;
    for(dirty=0; dirty<=1; dirty++) {
        load("first\nsecond\n");
        vi_changed = dirty;
        end = vi_file_end; cursor = vi_curs_char;
        top = vi_top_char; name = vi_file_name;
        command("r absent.txt\n");
        assert(vi_file_end == end && vi_curs_char == cursor);
        assert(vi_top_char == top && vi_file_name == name);
        assert(vi_changed == dirty);
        assert(!memcmp(vi_file_mem, "first\nsecond\n", 13));
        assert(!strcmp(last_output, "Unable to open file for reading!"));
    }
    load("");
    assert(readfile("absent.txt", vi_file_mem, 0) == 1);
    assert(vi_file_end == vi_file_mem);
    f = fopen("exists.txt", "wb"); assert(f);
    assert(fputs("read\r\n\032ignored", f) >= 0);
    assert(!fclose(f));
    assert(readfile("exists.txt", vi_file_mem, 1) == 0);
    assert(vi_file_end == vi_file_mem + 5);
    assert(!memcmp(vi_file_mem, "read\n", 5));
}
static void check_replace(void) {
    const char *replacement[3] = {"X", "\n", "\r"};
    int i, before;
    for(i=0; i<3; i++) {
        load("abc\n");
        vi_curs_char++;
        if(i == 2) vi_binary = 1;
        before = quit_calls;
        input = replacement[i];
        normal('r');
        assert(vi_file_mem[1] == replacement[i][0]);
        assert(vi_changed && vi_undo_changed == 0);
        command("q\n"); assert(quit_calls == before);
    }
}
static void check_search(void) {
    int i;
    load("a a a\n");
    dosearch(FORWARD, "a"); assert(vi_curs_char == vi_file_mem + 2);
    for(i=0; i<20; i++) repsearch();
    assert(vi_curs_char == vi_file_mem);
    input = "/\n"; readcmdline('/');
    assert(vi_curs_char == vi_file_mem + 2);
    input = "?\n"; readcmdline('?');
    assert(vi_curs_char == vi_file_mem + 4);
    vi_curs_char = vi_file_mem + 5;
    dosearch(BACKWARD, "a"); assert(vi_curs_char == vi_file_mem + 4);
    for(i=0; i<20; i++) repsearch();
    assert(vi_curs_char >= vi_file_mem && vi_curs_char < vi_file_end);
    dosearch(FORWARD, "missing");
    repsearch();
    assert(!strcmp(last_output, "Pattern not found"));
    assert(!vi_changed);
}
int main(int argc, char **argv) {
    vi_file_mem = calloc(FILELENG, 1); assert(vi_file_mem);
    vi_file_max = vi_file_mem + FILELENG;
    vi_file_name = "TEST.TXT";
    vi_rows = 25; vi_columns = 80;
    assert(argc == 2);
    if(!strcmp(argv[1], "save")) check_save();
    else if(!strcmp(argv[1], "read")) check_read();
    else if(!strcmp(argv[1], "replace")) check_replace();
    else if(!strcmp(argv[1], "search")) check_search();
    else assert(0);
    clearlastmess();
    free(vi_file_mem);
    printf("PASS: %s\n", argv[1]);
    return 0;
}
'''


def main():
    source = (ROOT / 'main.c').read_text()
    globals_ = source[source.index('int vi_rows;'):source.index('int main(')]
    readfile = function(source, 'int readfile(char *fname, char *fromp,')
    with tempfile.TemporaryDirectory(prefix='vi-editor-state-') as directory:
        work = Path(directory)
        harness = work / 'check.c'
        harness.write_text(HARNESS + globals_ + readfile + CHECKS)
        binary = work / 'check'
        subprocess.run([
            os.environ.get('CC_HOST', 'cc'), '-std=c99', '-g',
            '-fsanitize=address,undefined', '-I', str(ROOT), str(harness),
            str(ROOT / 'cmdline.c'), str(ROOT / 'normal.c'),
            str(ROOT / 'linefunc.c'), '-o', str(binary),
        ], check=True)
        failed = []
        for case in ('save', 'read', 'replace', 'search'):
            result = subprocess.run([str(binary), case], cwd=work)
            if result.returncode:
                failed.append(case)
        if failed:
            raise SystemExit('Failed: ' + ', '.join(failed))


if __name__ == '__main__':
    main()
