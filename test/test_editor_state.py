#!/usr/bin/env python3
"""Host regressions for editor state, EOF deletion and file/string insertion."""
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
void deleol(void) { assert(0); }
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
static int fail_after = -1, read_failed, fail_close;
static int test_getc(FILE *f) {
    if(fail_after == 0) { read_failed = 1; return EOF; }
    if(fail_after > 0) fail_after--;
    return getc(f);
}
static int test_ferror(FILE *f) { return read_failed || ferror(f); }
static int test_fclose(FILE *f) {
    int result = fclose(f);
    return fail_close ? EOF : result;
}
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
static void seed(const char *s) {
    FILE *f = fopen("insert.txt", "wb");
    assert(f && fputs(s, f) >= 0);
    assert(!fclose(f));
}
static void expect(const char *s) {
    assert(vi_file_end - vi_file_mem == (long)strlen(s));
    assert(!memcmp(vi_file_mem, s, strlen(s)));
}
static void check_insert_read(void) {
    FILE *f;
    static char binary[] = {'A', 0, 'B', 26, '\r', '\n'};
    seed("X\r\nY\032ignored");
    load("first\ntail\n");
    command("r insert.txt\n");
    expect("first\nX\nYtail\n");
    assert(vi_changed && vi_curs_char == vi_file_mem);
    load("last\n"); command("r insert.txt\n"); expect("last\nX\nY");
    load("last"); command("r insert.txt\n"); expect("lastX\nY");
    load(""); command(".r insert.txt\n"); expect("X\nY");
    load("head\ntail\n");
    vi_binary = 1;
    command("r insert.txt\n");
    expect("head\nX\r\nY\032ignoredtail\n");
    f = fopen("insert.txt", "wb"); assert(f);
    assert(fwrite(binary, 1, sizeof binary, f) == sizeof binary);
    assert(!fclose(f));
    load("a\ntail");
    vi_binary = 1;
    command("r insert.txt\n");
    assert(vi_file_end == vi_file_mem + 6 + sizeof binary);
    assert(!memcmp(vi_file_mem, "a\n", 2));
    assert(!memcmp(vi_file_mem + 2, binary, sizeof binary));
    assert(!memcmp(vi_file_mem + 2 + sizeof binary, "tail", 4));
}
static void check_read_limits(void) {
    FILE *f;
    int i, dirty;
    f = fopen("insert.txt", "wb"); assert(f);
    for(i=0; i<FILELENG; i++) assert(putc('x', f) != EOF);
    assert(!fclose(f));
    for(dirty=0; dirty<=1; dirty++) {
        load("a\ntail");
        vi_changed = dirty;
        command("r insert.txt\n");
        expect("a\ntail");
        assert(vi_changed == dirty && vi_curs_char == vi_file_mem);
        assert(strstr(last_output, "File too long") != NULL);
    }
    load("");
    assert(!readfile("insert.txt", vi_file_mem, 1));
    assert(vi_file_end == vi_file_max);
    seed("y");
    assert(readfile("insert.txt", vi_file_mem, 1) != 0);
    assert(vi_file_end == vi_file_max);
    for(i=0; i<FILELENG; i++) assert(vi_file_mem[i] == 'x');
    load("");
    seed("");
    command("r insert.txt\n"); expect("");
}
static void check_read_errors(void) {
    int dirty;
    seed("inserted");
    for(dirty=0; dirty<=1; dirty++) {
        load("a\ntail\n"); vi_changed = dirty;
        fail_after = 3;
        command("r insert.txt\n");
        fail_after = -1; read_failed = 0;
        expect("a\ntail\n"); assert(vi_changed == dirty);
        assert(strstr(last_output, "Read/close failed") != NULL);
        fail_close = 1;
        command("r insert.txt\n");
        fail_close = 0;
        expect("a\ntail\n"); assert(vi_changed == dirty);
        assert(strstr(last_output, "Read/close failed") != NULL);
    }
}
static void word(const char *before, int offset, int trailing,
                 const char *after, const char *undo) {
    load(before);
    vi_curs_char += offset;
    delword(trailing);
    expect(after);
    assert(!strcmp(vi_undo_buff, undo));
}
static void check_word_eof(void) {
    word("word", 0, 1, "", "iword\033");
    word("head word", 5, 1, "head ", "iword\033");
    word("word\nnext", 0, 1, "\nnext", "iword\033");
    word("word  next", 0, 1, "next", "iword  \033");
    word("word  next", 0, 0, "  next", "iword\033");
    word("!!!", 0, 1, "", "i!!!\033");
    word("!!! \t", 0, 1, "", "i!!! \t\033");
    word(" \t", 0, 1, "", "i \t\033");
    load(""); delword(1); expect(""); assert(!vi_changed);
    load("word");
    vi_curs_char = vi_file_end;
    delword(1); expect("word"); assert(!vi_changed);
    load("head word");
    vi_curs_char += 5; input = "w";
    normal('d'); expect("head ");
    assert(vi_changed && vi_uncurs_char == vi_file_mem + 5);
    load("head word");
    vi_curs_char += 5; input = "w";
    normal('c'); expect("head ");
    assert(vi_changed && vi_state == INSERT && vi_ins_start == vi_file_mem + 5);
}
static void check_bulk_insert(void) {
    int offset;
    for(offset=0; offset<=4; offset++) {
        load("abcd");
        vi_curs_char += offset;
        insstr("XYZ");
        assert(vi_file_end == vi_file_mem + 7);
        assert(!memcmp(vi_file_mem, "abcd", offset));
        assert(!memcmp(vi_file_mem + offset, "XYZ", 3));
        assert(!memcmp(vi_file_mem + offset + 3, "abcd" + offset, 4-offset));
        assert(vi_curs_char == vi_file_mem + offset + 3 && vi_changed);
    }
    load(""); insstr("XYZ"); expect("XYZ");
    load("abcd"); insstr(""); expect("abcd"); assert(!vi_changed);
    load("abcd");
    vi_file_max = vi_file_end + 2;
    insstr("XYZ"); expect("abcd"); assert(!vi_changed);
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
    else if(!strcmp(argv[1], "insert-read")) check_insert_read();
    else if(!strcmp(argv[1], "read-limits")) check_read_limits();
    else if(!strcmp(argv[1], "read-errors")) check_read_errors();
    else if(!strcmp(argv[1], "word-eof")) check_word_eof();
    else if(!strcmp(argv[1], "bulk-insert")) check_bulk_insert();
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
    misc = (ROOT / 'misccmds.c').read_text()
    primitives = 'static int canincrease(int n);\n'
    for signature in ('static int canincrease(int n)\n', 'void insstr(char *s)',
                      'void delchar(void)', 'void delword(int deltrailing)'):
        primitives += function(misc, signature) + '\n'
    with tempfile.TemporaryDirectory(prefix='vi-editor-state-') as directory:
        work = Path(directory)
        harness = work / 'check.c'
        harness.write_text(HARNESS + globals_ + primitives +
                           '#define getc test_getc\n#define ferror test_ferror\n'
                           '#define fclose test_fclose\n' + readfile +
                           '\n#undef getc\n#undef ferror\n#undef fclose\n' + CHECKS)
        binary = work / 'check'
        subprocess.run([
            os.environ.get('CC_HOST', 'cc'), '-std=c99', '-g',
            '-fsanitize=address,undefined', '-I', str(ROOT), str(harness),
            str(ROOT / 'cmdline.c'), str(ROOT / 'normal.c'),
            str(ROOT / 'linefunc.c'), '-o', str(binary),
        ], check=True)
        failed = []
        for case in ('save', 'read', 'replace', 'search', 'insert-read',
                     'read-limits', 'read-errors', 'word-eof', 'bulk-insert'):
            result = subprocess.run([str(binary), case], cwd=work)
            if result.returncode:
                failed.append(case)
        if failed:
            raise SystemExit('Failed: ' + ', '.join(failed))


if __name__ == '__main__':
    main()
