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
#include <setjmp.h>
#include "stevie.h"

static const char *input;
static int quit_calls, reject_save;
static char last_output[256];
static jmp_buf input_done;
static int editing, limit_messages;
void windgoto(int r, int c) {}
void windcolor(int fg) {}
void windcolorreset(void) {}
void windputc(int c) {}
void windrefresh(void) {}
void windstr(char *s) {
    snprintf(last_output, sizeof last_output, "%s", s);
    if(strstr(s, "full") || strstr(s, "too long") || strstr(s, "too big"))
        limit_messages++;
}
void updatescreen(void) {}
void cursupdate(void) {}
void screenclear(void) {}
void beep(void) {}
void help(void) {}
void getout(void) { quit_calls++; }
void vi_key_exit(void) { assert(0); }
char *viversion(void) { return "test"; }
int windgetc(void) {
    if(editing && (!input || !*input)) longjmp(input_done, 1);
    assert(input && *input); return (unsigned char)*input++;
}
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
void gotoline(int n) {}
void octchars(void) {}
void hexchars(void) {}
void decchars(void) {}
int hextoint(int c) {
    if(c >= '0' && c <= '9') return c-'0';
    if(c >= 'a' && c <= 'f') return c-'a'+10;
    return -1;
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
static int fail_yank_alloc, fail_message_alloc;
static size_t yank_request;
static void *test_yank_realloc(void *ptr, size_t size) {
    yank_request = size;
    return fail_yank_alloc ? NULL : realloc(ptr, size);
}
void *test_message_malloc(size_t size) {
    return fail_message_alloc ? NULL : malloc(size);
}
'''

CHECKS = r'''
static void load(const char *s) {
    memset(vi_file_mem, 0, FILELENG);
    memcpy(vi_file_mem, s, strlen(s));
    vi_file_end = vi_file_mem + strlen(s);
    vi_top_char = vi_curs_char = vi_file_mem;
    vi_changed = vi_binary = vi_renum = 0;
    vi_state = NORMAL;
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
static void check_search_bounds(void) {
    char *before;
    int i, dir;
    for(dir=FORWARD; dir<=BACKWARD; dir++) {
        load(""); dosearch(dir, "long pattern"); expect("");
        load("a"); before=vi_curs_char;
        dosearch(dir, "long pattern"); assert(vi_curs_char == before);
        dosearch(dir, ""); assert(vi_curs_char == before);
        dosearch(dir, "a"); assert(vi_curs_char == vi_file_mem);
        load("aaab");
        dosearch(dir, "aab"); assert(vi_curs_char == vi_file_mem+1);
        load("a a a");
        vi_curs_char = vi_file_mem + 2;
        dosearch(dir, "a");
        assert(vi_curs_char == vi_file_mem + (dir == FORWARD ? 4 : 0));
        repsearch();
        assert(vi_curs_char == vi_file_mem + (dir == FORWARD ? 0 : 4));
    }
    memset(vi_file_mem, 'a', FILELENG);
    vi_file_end = vi_file_max;
    vi_curs_char = vi_file_end-1;
    dosearch(FORWARD, "zzzzzz");
    dosearch(BACKWARD, "zzzzzz");
    for(i=0; i<20; i++) repsearch();
    assert(vi_curs_char == vi_file_end-1);
}
static void check_command_limits(void) {
    char command_text[1200];
    int before = quit_calls;
    load("abc\n");
    memset(command_text, ' ', 99);
    command_text[0]='v'; command_text[99]='\n'; command_text[100]=0;
    command(command_text); assert(!strcmp(last_output, "test"));
    memset(command_text, ' ', 1100);
    command_text[0]='q'; command_text[1]='!';
    command_text[1100]='\n'; command_text[1101]=0;
    command(command_text); assert(quit_calls == before);
    assert(strstr(last_output, "cancelled"));
    memset(command_text, 'a', 100);
    strcpy(command_text+100, "\025v\n");
    command(command_text); assert(!strcmp(last_output, "test"));
    memset(command_text, 'a', 100);
    memset(command_text+100, '\b', 99);
    strcpy(command_text+199, "v\n");
    command(command_text); assert(!strcmp(last_output, "test"));
    memset(command_text, 'a', 100);
    strcpy(command_text+100, "\033");
    input=command_text; readcmdline(':');
    assert(vi_state == NORMAL);
    memset(command_text, 'a', 98); command_text[98]='\n'; command_text[99]=0;
    load("");
    memset(vi_file_mem, 'a', 98); vi_file_end=vi_file_mem+98;
    input=command_text; readcmdline('/');
    assert(!strstr(last_output, "cancelled"));
    memset(command_text, 'a', 99); command_text[99]='\n'; command_text[100]=0;
    input=command_text; readcmdline('?');
    assert(strstr(last_output, "cancelled"));
}
static void long_word(int n) {
    load("");
    memset(vi_file_mem, 'a', n);
    vi_file_mem[n]='\n';
    vi_file_end=vi_file_mem+n+1;
}
static void run_edit(const char *s);
static void check_delete_limits(void) {
    char *cursor;
    int mode;
    for(mode=0; mode<4; mode++) {
        long_word(1022);
        strcpy(vi_undo_buff, "rZ"); strcpy(vi_redo_buff, "rX");
        vi_uncurs_char=vi_file_mem+1; cursor=vi_curs_char;
        if(mode==0) normal('D');
        else if(mode==1) { input="w"; normal('d'); }
        else if(mode==2) normal('C');
        else { input="w"; normal('c'); }
        assert(vi_file_end == vi_file_mem+1023 && !vi_changed);
        assert(vi_curs_char == cursor && vi_state == NORMAL);
        assert(!strcmp(vi_undo_buff, "rZ") && !strcmp(vi_redo_buff, "rX"));
        assert(vi_uncurs_char == vi_file_mem+1);
    }
    long_word(1021); normal('D'); expect("\n");
    assert(strlen(vi_undo_buff) == 1023 && vi_changed);
    long_word(1021); input="w"; normal('d'); expect("\n");
    assert(strlen(vi_undo_buff) == 1023 && vi_changed);
    long_word(1022);
    vi_uncurs_char=vi_file_mem; vi_undel_chars=1022;
    normal('u');
    assert(vi_undel_chars == 1022 && vi_file_end == vi_file_mem+1023);
    assert(!vi_changed);
}
static void run_edit(const char *s) {
    input=s; editing=1;
    if(!setjmp(input_done)) edit();
    editing=0;
}
static void check_insert_limits(void) {
    char script[1600];
    load("\n");
    script[0]='i'; memset(script+1, 'a', 1500);
    strcpy(script+1501, "\bZ\033");
    run_edit(script);
    assert(vi_state == NORMAL && limit_messages > 0);
    assert(vi_ninsert == 1020 && vi_ins_ptr-vi_ins_buff == 1021);
    assert(vi_file_end == vi_file_mem+1021 && vi_file_mem[1019] == 'Z');
    assert(strlen(vi_redo_buff) == 1022);
    load("");
    script[0]='i'; memset(script+1, 'a', 1500);
    strcpy(script+1501, "\033");
    run_edit(script);
    assert(vi_ninsert == 1021 && vi_file_end == vi_file_mem+1021);
    assert(vi_file_end[-1] == '\n' && strlen(vi_redo_buff) == 1023);
    run_edit("u"); expect("");
    run_edit("."); assert(vi_file_end == vi_file_mem+1021);
    assert(vi_file_end[-1] == '\n');
    long_word(1021);
    normal('D'); expect("\n");
    run_edit("u");
    assert(vi_file_end == vi_file_mem+1022);
    assert(vi_file_mem[1020] == 'a' && vi_file_mem[1021] == '\n');
    long_word(1021);
    vi_file_end--;
    normal('D'); expect("");
    run_edit("u");
    assert(vi_file_end == vi_file_mem+1021 && vi_file_end[-1] == 'a');
    load("z\n");
    script[0]='c'; script[1]='w'; memset(script+2, 'a', 1500);
    strcpy(script+1502, "\033");
    run_edit(script);
    assert(vi_ninsert == 1019 && vi_ins_ptr-vi_ins_buff == 1021);
    assert(vi_file_end == vi_file_mem+1020 && vi_state == NORMAL);
}
static void check_literal_limits(void) {
    char script[1600];
    load("\n");
    script[0]='i'; memset(script+1, 'a', 1020);
    strcpy(script+1021, "\026Z\03041\033");
    run_edit(script);
    assert(vi_ninsert == 1020 && vi_file_end == vi_file_mem+1021);
    assert(vi_file_end[-2] == 'a' && vi_state == NORMAL);
    load("\n");
    run_edit("i\026\t\03041\033");
    expect("\tA\n");
    assert(vi_ninsert == 2);
    load("\n");
    script[0]='i'; memset(script+1, '\t', 300);
    strcpy(script+301, "\033");
    run_edit(script);
    assert(vi_ninsert == 1020 && vi_file_end == vi_file_mem+1021);
}
static void check_file_insert_limits(void) {
    load("abc\n");
    vi_file_max=vi_file_end+3;
    run_edit("iXY\bZ\033");
    expect("Zabc\n");
    assert(limit_messages > 0 && vi_state == NORMAL);
    vi_file_max=vi_file_end+1;
    strcpy(vi_undo_buff, "rX");
    normal('O');
    assert(vi_state == NORMAL && vi_curs_char >= vi_file_mem);
    assert(!strcmp(vi_undo_buff, "rX"));
    normal('o'); expect("Zabc\n");
    assert(!strcmp(vi_undo_buff, "rX"));
}
static void check_long_messages(void) {
    char name[400];
    memset(name, 'a', sizeof name-1); name[sizeof name-1]=0;
    load("abc\n");
    vi_file_name=name; vi_changed=1;
    fileinfo(); assert(strlen(last_output) < 128);
    filemess("message"); assert(strlen(last_output) < 128);
    assert(readfile(name, vi_file_mem, 1));
    assert(!strcmp(last_output, "Unable to open file for reading!"));
    expect("abc\n");
    vi_file_name="TEST.TXT";
}
static void check_replay_limits(void) {
    char text[1024];
    int i;
    memset(text, 'a', 1023); text[1023]=0;
    load("abc\n");
    stuffin("");
    assert(!anyinput());
    stuffin(text); assert(anyinput());
    stuffin("x");
    for(i=0; i<800; i++) assert(vgetc() == 'a');
    text[800]=0;
    stuffin(text);
    for(i=0; i<1023; i++) assert(vgetc() == 'a');
    assert(!anyinput());
    text[0]=(char)0xe9; text[1]=0;
    stuffin(text); assert(vgetc() == 0xe9);
    memset(text, 'a', 1023); text[1023]=0;
    stuffin(text);
    strcpy(vi_undo_buff, "rZ");
    vi_uncurs_char=vi_file_mem+1;
    normal('u');
    assert(!strcmp(vi_undo_buff, "rZ") && vi_curs_char == vi_file_mem);
    for(i=0; i<1023; i++) assert(vgetc() == 'a');
    assert(!anyinput());
}
static void check_yank_failures(void) {
    char *old;
    int dirty, command_index;
    load("first\n");
    fail_yank_alloc = 1;
    input="y"; normal('y');
    fail_yank_alloc = 0;
    expect("first\n");
    assert(savedline == NULL && !vi_changed && vi_state == NORMAL);
    for(dirty=0; dirty<=1; dirty++) {
        for(command_index=0; command_index<3; command_index++) {
            load("keep\n");
            yankline(1);
            assert(savednum == 5 && savedcount == 1);
            old = savedline;
            load("first\nsecond line\n");
            vi_curs_char = vi_file_mem + 8;
            vi_top_char = vi_file_mem + 6;
            vi_changed = dirty;
            strcpy(vi_undo_buff, "rZ");
            strcpy(vi_redo_buff, "rX");
            vi_uncurs_char = vi_file_mem + 1;
            fail_yank_alloc = 1;
            if(command_index == 0) { input="y"; normal('y'); }
            else if(command_index == 1) { input="d"; normal('d'); }
            else { input="c"; normal('c'); }
            fail_yank_alloc = 0;
            expect("first\nsecond line\n");
            assert(vi_changed == dirty && vi_state == NORMAL);
            assert(vi_curs_char == vi_file_mem+8 && vi_top_char == vi_file_mem+6);
            assert(!strcmp(vi_undo_buff, "rZ") && !strcmp(vi_redo_buff, "rX"));
            assert(vi_uncurs_char == vi_file_mem+1);
            assert(savedline == old && savednum == 5 && savedcount == 1);
            assert(!memcmp(savedline, "keep\n", 6));
            assert(strstr(last_output, "yank") && strstr(last_output, "cancelled"));
        }
    }
    load("target\n");
    normal('P'); expect("keep\ntarget\n");
}
static void check_yank_success(void) {
    int i;
    load("first\nsecond line\nlast");
    vi_curs_char += 8;
    input="y"; normal('y');
    assert(vi_curs_char == vi_file_mem+8 && !vi_changed);
    assert(savednum == 12 && savedcount == 1);
    assert(!memcmp(savedline, "second line\n", 13));
    vi_renum=2; input="y"; normal('y');
    assert(savednum == 16 && savedcount == 2);
    assert(!memcmp(savedline, "second line\nlast", 17));
    load("");
    memset(vi_file_mem, 'a', FILELENG);
    vi_file_end=vi_file_max;
    input="y"; normal('y');
    assert(yank_request == FILELENG+1);
    assert(savednum == FILELENG && savedcount == 1 && savedline[FILELENG] == 0);
    for(i=0; i<FILELENG; i++) assert(savedline[i] == 'a');
    load("abc\nlast");
    vi_curs_char=vi_file_mem+4;
    input="d"; normal('d'); expect("abc\n");
    run_edit("u"); expect("abc\nlast");
    load("abc\nlast");
    vi_curs_char=vi_file_mem+4;
    input="c"; normal('c'); expect("abc\n");
    assert(vi_state == INSERT && savednum == 4 && savedcount == 1);
    assert(!memcmp(savedline, "last", 5));
    load(""); input="y"; normal('y');
    assert(savednum == 0 && savedcount == 0 && savedline[0] == 0);
}
static void check_yank_message_failure(void) {
    load("keep\n"); yankline(1);
    load("replacement\n");
    fail_yank_alloc=fail_message_alloc=1;
    input="d"; normal('d');
    assert(strstr(last_output, "yank") && strstr(last_output, "cancelled"));
    expect("replacement\n");
    assert(!vi_changed && vi_state == NORMAL);
    clearlastmess();
    fail_yank_alloc=fail_message_alloc=0;
    normal('P'); expect("keep\nreplacement\n");
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
    else if(!strcmp(argv[1], "search-bounds")) check_search_bounds();
    else if(!strcmp(argv[1], "command-limits")) check_command_limits();
    else if(!strcmp(argv[1], "delete-limits")) check_delete_limits();
    else if(!strcmp(argv[1], "insert-limits")) check_insert_limits();
    else if(!strcmp(argv[1], "literal-limits")) check_literal_limits();
    else if(!strcmp(argv[1], "replay-limits")) check_replay_limits();
    else if(!strcmp(argv[1], "file-insert-limits")) check_file_insert_limits();
    else if(!strcmp(argv[1], "long-messages")) check_long_messages();
    else if(!strcmp(argv[1], "yank-failures")) check_yank_failures();
    else if(!strcmp(argv[1], "yank-success")) check_yank_success();
    else if(!strcmp(argv[1], "yank-message-failure")) check_yank_message_failure();
    else assert(0);
    clearlastmess();
    free(savedline);
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
    primitives = ('static int canincrease(int n);\n'
                  'static char *savedline;\nstatic int savednum, savedcount;\n')
    primitives += '#define realloc test_yank_realloc\n'
    primitives += function(misc, 'int yankline(int n)') + '\n'
    primitives += '#undef realloc\n'
    for signature in ('static int canincrease(int n)\n', 'void insstr(char *s)',
                      'void inschar(int c)', 'void delchar(void)',
                      'int deleol(void)', 'int delword(int deltrailing)',
                      'void fileinfo(void)', 'void putline(int k)',
                      'void delline(int nlines)'):
        primitives += function(misc, signature) + '\n'
    queue = source[source.index('static char getcbuff'): ]
    edit = (ROOT / 'edit.c').read_text()
    editor = ('static void donormal(int c);\nstatic void insertchar(int c);\n'
              'static int gethexchar(void);\n'
              'static int insertroom(int n, int reserve_eof);\n'
              'static int insertbyte(int c, int reserve_eof);\n')
    for signature in ('void edit(void)', 'static void donormal(int c)\n',
                      'static int insertroom(int n, int reserve_eof)\n',
                      'static int insertbyte(int c, int reserve_eof)\n',
                      'static void insertchar(int c)\n', 'static int gethexchar(void) {'):
        editor += function(edit, signature) + '\n'
    with tempfile.TemporaryDirectory(prefix='vi-editor-state-') as directory:
        work = Path(directory)
        harness = work / 'check.c'
        command_source = work / 'commands.c'
        command_source.write_text(
            '#include <stdlib.h>\nvoid *test_message_malloc(size_t);\n'
            '#define malloc test_message_malloc\n'
            f'#include "{ROOT / "cmdline.c"}"\n')
        harness.write_text(HARNESS + globals_ + primitives + queue + editor +
                           '#define getc test_getc\n#define ferror test_ferror\n'
                           '#define fclose test_fclose\n' + readfile +
                           '\n#undef getc\n#undef ferror\n#undef fclose\n' + CHECKS)
        binary = work / 'check'
        subprocess.run([
            os.environ.get('CC_HOST', 'cc'), '-std=c99', '-g',
            '-fsanitize=address,undefined', '-I', str(ROOT), str(harness),
            str(command_source), str(ROOT / 'normal.c'),
            str(ROOT / 'linefunc.c'), '-o', str(binary),
        ], check=True)
        failed = []
        for case in ('save', 'read', 'replace', 'search', 'insert-read',
                     'read-limits', 'read-errors', 'word-eof', 'bulk-insert',
                     'search-bounds', 'command-limits', 'delete-limits',
                     'insert-limits', 'literal-limits', 'replay-limits',
                     'file-insert-limits', 'long-messages', 'yank-failures',
                     'yank-success', 'yank-message-failure'):
            try:
                result = subprocess.run([str(binary), case], cwd=work, timeout=10)
            except subprocess.TimeoutExpired:
                failed.append(case + ' (timed out)')
                continue
            if result.returncode:
                failed.append(case)
        if failed:
            raise SystemExit('Failed: ' + ', '.join(failed))


if __name__ == '__main__':
    main()
