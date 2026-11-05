#!/usr/bin/env python3
"""Host regressions for editor state, EOF deletion and file/string insertion."""
from pathlib import Path
import os
import subprocess
import sys
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
#include "yankmem.h"

unsigned char vi_char_width[256];
static const char *input;
static int quit_calls, reject_save;
static char last_output[256];
static jmp_buf input_done;
static void run_edit(const char *s);
static int editing, limit_messages;
static int keyboard_burst;
static int terminal_writes, cursor_visible = 1, screen_updates;
static unsigned long edit_moves, edit_moved_bytes;
void windgoto(int r, int c) {}
void windcursor(int on) { cursor_visible = on; }
void windcolor(int fg) {}
void windcolorreset(void) {}
void windputc(int c) { terminal_writes++; }
void windrefresh(void) {}
void windstr(char *s) {
    snprintf(last_output, sizeof last_output, "%s", s);
    if(strstr(s, "full") || strstr(s, "too long") || strstr(s, "too big"))
        limit_messages++;
}
void updatescreen(void) { screen_updates++; }
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
int windpeek(void) {
    return keyboard_burst && input && *input ? (unsigned char)*input : -1;
}
void beginline(void) {
    while(vi_curs_char > vi_file_mem && vi_curs_char[-1] != '\n')
        vi_curs_char--;
}
int oneright(void) { assert(0); return 0; }
int oneleft(void) { assert(0); return 0; }
int oneup(unsigned n) { assert(0); return 0; }
int onedown(unsigned n) { assert(0); return 0; }
int issepchar(int c) { return strchr(WORDSEP, c) != NULL; }
unsigned long cntlines(char *a, char *b) {
    unsigned long n = 1;
    while(a < b) if(*a++ == '\n') n++;
    return n;
}
static unsigned goto_count;
static int goto_calls;
void gotoline(unsigned n) { goto_count = n; goto_calls++; }
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
static int fail_yank_store, fail_yank_load, fail_message_alloc;
extern unsigned char test_yank_memory[];
static int test_yank_store(const char *source, unsigned length) {
    return fail_yank_store ? 0 : vi_yank_store(source, length);
}
static int test_yank_load(unsigned offset, char *destination, unsigned length) {
    if(fail_yank_load) {
        memset(destination, 'X', length);
        return 0;
    }
    return vi_yank_load(offset, destination, length);
}
void *test_message_malloc(size_t size) {
    return fail_message_alloc ? NULL : malloc(size);
}
static int fail_string_alloc, string_alloc_calls, string_live;
static void *string_blocks[32];
void *test_string_malloc(size_t size) {
    void *p;
    int i;
    string_alloc_calls++;
    if(fail_string_alloc) return NULL;
    p = malloc(size);
    assert(p);
    for(i=0; i<32 && string_blocks[i]; i++);
    assert(i < 32);
    string_blocks[i] = p;
    string_live++;
    return p;
}
void test_string_free(void *p) {
    int i;
    for(i=0; i<32 && string_blocks[i] != p; i++);
    assert(i < 32 && p != NULL);
    string_blocks[i] = NULL;
    string_live--;
    free(p);
}
'''

CHECKS = r'''
static void load(const char *s) {
    vi_mark = NULL;
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
    f = fopen("insert.txt", "wb"); assert(f);
    for(i=0; i<=FILELENG; i++) assert(putc('x', f) != EOF);
    assert(!fclose(f));
    load("");
    assert(readfile("insert.txt", vi_file_mem, 1) == -1);
    expect("");
    assert(!vi_changed && strstr(last_output, "File too long") != NULL);
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
    load("");
    memset(vi_file_mem, 'a', FILELENG - 2U);
    vi_file_end = vi_file_mem + FILELENG - 2U;
    vi_curs_char = vi_file_mem + 1;
    edit_moves = edit_moved_bytes = 0;
    inschar('X');
    assert(edit_moves == 1 && edit_moved_bytes == FILELENG - 3U);
    assert(vi_curs_char == vi_file_mem + 2 && vi_file_mem[1] == 'X');
    assert(vi_file_mem[FILELENG - 2U] == 'a');
    vi_file_max = vi_file_end + 1;
    inschar('Y');
    assert(edit_moves == 1);
}
static void check_insert_backspace(void) {
    unsigned length = FILELENG - 3U;
    load("tail\n");
    run_edit("iab\bC\033");
    expect("aCtail\n");
    assert(vi_ninsert == 2);
    run_edit("u"); expect("tail\n"); assert(!vi_changed);
    run_edit("."); expect("aCtail\n");
    load("tail\n");
    run_edit("iX\n\bY\033");
    expect("XYtail\n");
    run_edit("u"); expect("tail\n"); assert(!vi_changed);
    load("tail\n");
    run_edit("i\b\033");
    expect("tail\n"); assert(!vi_changed);
    load("");
    memset(vi_file_mem, 'a', length);
    vi_file_end = vi_file_mem + length;
    edit_moves = edit_moved_bytes = 0;
    run_edit("iX\b\033");
    assert(vi_file_end == vi_file_mem + length && vi_curs_char == vi_file_mem);
    assert(edit_moves == 2 && edit_moved_bytes == 2UL * length);
    while (length != 0)
        assert(vi_file_mem[--length] == 'a');
    load("x");
    edit_moves = 0;
    delchar(); expect(""); assert(vi_changed && edit_moves == 0);
    delchar(); expect(""); assert(edit_moves == 0);
}
static void check_keyboard_batch(void) {
    int count, i;
    char keys[12];
    for (count = 1; count <= 9; count++) {
        load("tail\n");
        keys[0] = 'i';
        for (i = 0; i < count; i++) keys[i + 1] = 'A' + i;
        strcpy(keys + count + 1, "\033");
        edit_moves = 0;
        keyboard_burst = 1;
        run_edit(keys);
        keyboard_burst = 0;
        assert(edit_moves == (unsigned)(count + 1) / 2);
        assert(vi_ninsert == count && vi_file_end == vi_file_mem + count + 5);
        assert(!memcmp(vi_file_mem, keys + 1, count));
        assert(!memcmp(vi_file_mem + count, "tail\n", 5));
        run_edit("u"); expect("tail\n"); assert(!vi_changed);
        run_edit("."); assert(!memcmp(vi_file_mem, keys + 1, count));
    }
    keyboard_burst = 1;
    check_insert_backspace();
    load("tail\n");
    run_edit("iab\tcd\033"); expect("ab    cdtail\n");
    load("tail\n");
    run_edit("iab\026\033cd\033"); expect("ab\033cdtail\n");
    load("tail\n");
    vi_file_max = vi_file_end + 3;
    run_edit("iABC\033"); expect("Atail\n");
    assert(vi_ninsert == 1 && strstr(last_output, "Mode"));
    keyboard_burst = 0;
}
static void check_single_mark(void) {
    FILE *f;
    char *saved, *maximum;
    unsigned length;
    load("abc\n");
    vi_curs_char += 2;
    normal('\'');
    assert(vi_curs_char == vi_file_mem + 2 && strstr(last_output, "not set"));
    strcpy(vi_undo_buff, "rZ"); strcpy(vi_redo_buff, "rX");
    normal('m');
    assert(vi_mark == vi_file_mem + 2 && !vi_changed);
    assert(!strcmp(vi_undo_buff, "rZ") && !strcmp(vi_redo_buff, "rX"));
    vi_curs_char = vi_file_mem;
    normal('\''); assert(vi_curs_char == vi_file_mem + 2);
    normal('\''); assert(vi_curs_char == vi_mark);
    vi_renum = VI_COUNT_MAX + 1UL;
    vi_curs_char = vi_file_mem;
    normal('m'); assert(vi_mark == vi_file_mem + 2);
    normal('\''); assert(vi_curs_char == vi_file_mem);
    vi_renum = 0;
    run_edit("iX\033"); assert(vi_mark == vi_file_mem + 3);
    run_edit("u"); expect("abc\n"); assert(vi_mark == vi_file_mem + 2);
    run_edit("."); expect("Xabc\n"); assert(vi_mark == vi_file_mem + 3);
    vi_curs_char = vi_file_mem; normal('m');
    run_edit("u"); expect("abc\n"); assert(vi_mark == NULL);
    load("abc\n");
    vi_curs_char++; normal('m');
    input = "Z"; normal('r'); assert(vi_mark == vi_file_mem + 1);
    vi_curs_char = vi_file_mem; delchar();
    assert(vi_mark == vi_file_mem);
    delchar(); assert(vi_mark == NULL);
    load("abc\n");
    normal('m'); run_edit("xu"); expect("abc\n"); assert(vi_mark == NULL);
    load("one two\n");
    vi_curs_char += 5; normal('m');
    vi_curs_char = vi_file_mem; delword(1);
    expect("two\n"); assert(vi_mark == vi_file_mem + 1);
    load("one\ntwo\n");
    vi_curs_char += 5; normal('m');
    vi_curs_char = vi_file_mem; run_edit("ddu");
    expect("one\ntwo\n"); assert(vi_mark == vi_file_mem + 5);
    load("one\ntwo\n");
    vi_curs_char += 3; normal('m');
    run_edit("Ju"); expect("one\ntwo\n"); assert(vi_mark == NULL);
    load("\ta\nb\n\tc");
    vi_curs_char += 3; normal('m');
    run_edit("3<<u3>>u"); expect("\ta\nb\n\tc");
    assert(vi_mark == vi_file_mem + 3);
    vi_curs_char = vi_file_mem; normal('m');
    run_edit("<<u"); expect("\ta\nb\n\tc"); assert(vi_mark == NULL);
    load("keep\n");
    assert(yankline(1));
    load("tail\n"); vi_curs_char++; normal('m');
    fail_yank_load = 1; putline(1); fail_yank_load = 0;
    expect("tail\n"); assert(vi_mark == vi_file_mem + 1);
    putline(1); expect("keep\ntail\n"); assert(vi_mark == vi_file_mem + 6);
    f = fopen("mark.txt", "wb"); assert(f);
    assert(fputs("XY\n", f) >= 0 && !fclose(f));
    load("tail\n"); vi_curs_char++; normal('m');
    assert(readfile("mark.txt", vi_file_mem, 1) == 0);
    expect("XY\ntail\n"); assert(vi_mark == vi_file_mem + 4);
    saved = vi_mark;
    fail_after = 1;
    assert(readfile("mark.txt", vi_file_mem, 1) == -1);
    fail_after = -1; read_failed = 0;
    expect("XY\ntail\n"); assert(vi_mark == saved);
    fail_close = 1;
    assert(readfile("mark.txt", vi_file_mem, 1) == -1);
    fail_close = 0; assert(vi_mark == saved);
    maximum = vi_file_max; vi_file_max = vi_file_end;
    inschar('!'); assert(vi_mark == saved);
    assert(readfile("mark.txt", vi_file_mem, 1) == -1 && vi_mark == saved);
    vi_file_max = maximum;
    command("f renamed.txt\n"); assert(vi_mark == saved);
    vi_changed = 1;
    command("e mark.txt\n"); assert(vi_mark == saved);
    command("e! mark.txt\n"); expect("XY\n"); assert(vi_mark == NULL);
    normal('m');
    command("e! no-such-mark-file.txt\n"); expect(""); assert(vi_mark == NULL);
    normal('m'); assert(vi_mark == NULL && strstr(last_output, "No character"));
    load("");
    length = FILELENG - 2U;
    memset(vi_file_mem, 'a', length);
    vi_file_end = vi_file_mem + length;
    vi_curs_char = vi_file_end - 1; normal('m');
    vi_curs_char = vi_file_mem; inschar('X');
    assert(vi_mark == vi_file_mem + length);
    delchar(); assert(vi_mark == vi_file_mem + length - 1);
    normal('\''); assert(vi_curs_char == vi_mark);
    delchar(); assert(vi_mark == NULL);
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
    int before = quit_calls, plain_writes, before_updates;
    load("abc\n");
    terminal_writes = 0;
    command("v\n");
    plain_writes = terminal_writes;
    terminal_writes = 0;
    command("vX\b\n");
    assert(!strcmp(last_output, "test"));
    assert(terminal_writes == plain_writes + 2 && cursor_visible);
    load("abc\n");
    before_updates = screen_updates;
    run_edit("i\t\033");
    expect("    abc\n");
    assert(screen_updates == before_updates + 3);
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
static void check_count_limits(void) {
    static const char *rejected[] = {
        "65536dd", "65536cw", "65536yy", "65536>>", "65536<<",
        "65536rZ", "65536~", "9999999999999999999999999999999999999999dd",
        "65536:q!\n", "65536/abc\n", "65536?abc\n"
    };
    unsigned i;
    int calls, quits = quit_calls;
    for(i=0; i<sizeof rejected/sizeof rejected[0]; i++) {
        load("abc\n");
        strcpy(vi_undo_buff, "rZ"); strcpy(vi_redo_buff, "rX");
        vi_uncurs_char=vi_file_mem;
        run_edit(rejected[i]);
        expect("abc\n");
        assert(!vi_changed && vi_state==NORMAL && vi_renum==0);
        assert(!strcmp(vi_undo_buff, "rZ") && !strcmp(vi_redo_buff, "rX"));
        assert(strstr(last_output, "count too large") && quit_calls==quits);
    }
    load("abc\n"); run_edit("65536ddx"); expect("bc\n");
    load("abc\n"); run_edit("65536/abc\nx"); expect("bc\n");
    load("abc\n");
    command("65535\n"); assert(goto_count==65535U);
    command("00040000\n"); assert(goto_count==40000U);
    calls=goto_calls;
    command("65536\n"); assert(goto_calls==calls);
    command("99999999999999999999999999999\n"); assert(goto_calls==calls);
    assert(strstr(last_output, "count too large"));
    run_edit("65535dd"); expect("");
    assert(!strcmp(vi_redo_buff, "65535dd"));
    run_edit("u"); expect("abc\n");
    free(vi_file_mem);
    vi_file_mem=malloc(40001U); assert(vi_file_mem);
    memset(vi_file_mem, 'a', 40000U);
    vi_file_end=vi_file_mem+40000U; vi_file_max=vi_file_end+1;
    vi_top_char=vi_curs_char=vi_file_mem;
    resetundo();
    run_edit("40000~");
    assert(!strcmp(vi_undo_buff, "40000~") && !strcmp(vi_redo_buff, "40000~"));
    assert(vi_curs_char==vi_file_end-1);
    for(i=0; i<40000U; i++) assert(vi_file_mem[i]=='A');
    run_edit("u");
    for(i=0; i<40000U; i++) assert(vi_file_mem[i]=='a');
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
    char *saved_name = vi_file_name;
    memset(name, 'a', sizeof name-1); name[sizeof name-1]=0;
    load("abc\n");
    vi_file_name=name; vi_changed=1;
    fileinfo(); assert(strlen(last_output) < 128);
    filemess("message"); assert(strlen(last_output) < 128);
    assert(readfile(name, vi_file_mem, 1));
    assert(!strcmp(last_output, "Unable to open file for reading!"));
    expect("abc\n");
    vi_file_name=saved_name;
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
    int dirty, command_index;
    load("first\n");
    fail_yank_store = 1;
    input="y"; normal('y');
    fail_yank_store = 0;
    expect("first\n");
    assert(savednum == 0 && !vi_changed && vi_state == NORMAL);
    for(dirty=0; dirty<=1; dirty++) {
        for(command_index=0; command_index<3; command_index++) {
            load("keep\n");
            yankline(1);
            assert(savednum == 5 && savedcount == 1);
            load("first\nsecond line\n");
            vi_curs_char = vi_file_mem + 8;
            vi_top_char = vi_file_mem + 6;
            vi_changed = dirty;
            strcpy(vi_undo_buff, "rZ");
            strcpy(vi_redo_buff, "rX");
            vi_uncurs_char = vi_file_mem + 1;
            fail_yank_store = 1;
            if(command_index == 0) { input="y"; normal('y'); }
            else if(command_index == 1) { input="d"; normal('d'); }
            else { input="c"; normal('c'); }
            fail_yank_store = 0;
            expect("first\nsecond line\n");
            assert(vi_changed == dirty && vi_state == NORMAL);
            assert(vi_curs_char == vi_file_mem+8 && vi_top_char == vi_file_mem+6);
            assert(!strcmp(vi_undo_buff, "rZ") && !strcmp(vi_redo_buff, "rX"));
            assert(vi_uncurs_char == vi_file_mem+1);
            assert(savednum == 5 && savedcount == 1 && savedlast == '\n');
            assert(!memcmp(test_yank_memory, "keep\n", 5));
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
    assert(!memcmp(test_yank_memory, "second line\n", 12));
    vi_renum=2; input="y"; normal('y');
    assert(savednum == 16 && savedcount == 2);
    assert(!memcmp(test_yank_memory, "second line\nlast", 16));
    load("");
    memset(vi_file_mem, 'a', FILELENG);
    vi_file_end=vi_file_max;
    input="y"; normal('y');
    assert(savednum == FILELENG && savedcount == 1 && savedlast == 'a');
    for(i=0; i<FILELENG; i++) assert(test_yank_memory[i] == 'a');
    load("abc\nlast");
    vi_curs_char=vi_file_mem+4;
    input="d"; normal('d'); expect("abc\n");
    run_edit("u"); expect("abc\nlast");
    load("abc\nlast");
    vi_curs_char=vi_file_mem+4;
    input="c"; normal('c'); expect("abc\n");
    assert(vi_state == INSERT && savednum == 4 && savedcount == 1);
    assert(!memcmp(test_yank_memory, "last", 4));
    load(""); input="y"; normal('y');
    assert(savednum == 0 && savedcount == 0 && savedlast == 0);
}
static void check_yank_message_failure(void) {
    load("keep\n"); yankline(1);
    load("replacement\n");
    fail_yank_store=fail_message_alloc=1;
    input="d"; normal('d');
    assert(strstr(last_output, "yank") && strstr(last_output, "cancelled"));
    expect("replacement\n");
    assert(!vi_changed && vi_state == NORMAL);
    clearlastmess();
    fail_yank_store=fail_message_alloc=0;
    normal('P'); expect("keep\nreplacement\n");
}
static void check_put_failures(void) {
    int dirty, above;
    load("saved"); assert(yankline(1));
    for(dirty=0; dirty<=1; dirty++) {
        for(above=0; above<=1; above++) {
            load("first\nlast");
            vi_curs_char=vi_file_mem+8;
            vi_top_char=vi_file_mem+6;
            vi_changed=dirty;
            strcpy(vi_undo_buff, "rZ"); strcpy(vi_redo_buff, "rX");
            vi_uncurs_char=vi_file_mem+1;
            fail_yank_load=1;
            putline(above);
            fail_yank_load=0;
            expect("first\nlast");
            assert(vi_changed==dirty && vi_curs_char==vi_file_mem+8);
            assert(vi_top_char==vi_file_mem+6 && vi_uncurs_char==vi_file_mem+1);
            assert(!strcmp(vi_undo_buff,"rZ") && !strcmp(vi_redo_buff,"rX"));
            assert(strstr(last_output,"yank") && strstr(last_output,"cancelled"));
        }
    }
    /* A rejected P must not move the cursor to the beginning of its line. */
    load("first\nlast"); vi_curs_char=vi_file_mem+8;
    vi_file_max=vi_file_end+5;
    putline(1); expect("first\nlast");
    assert(vi_curs_char==vi_file_mem+8 && !vi_changed);
    vi_file_max=vi_file_mem+FILELENG;
    putline(1); expect("first\nsaved\nlast");
}
static void check_large_binary_put(void) {
    int i;
    load("");
    for(i=0; i<FILELENG-1; i++) vi_file_mem[i]=(char)(i%251);
    vi_file_end=vi_file_mem+FILELENG-1;
    assert(yankline(FILELENG));
    load("");
    putline(1);
    assert(vi_file_end==vi_file_mem+FILELENG-1 && vi_changed);
    for(i=0; i<FILELENG-1; i++) assert(vi_file_mem[i]==(char)(i%251));
    assert(vi_curs_char==vi_file_mem);
}
static void check_full_buffer(void) {
    int i;
    assert(FILELENG == VI_YANK_CAPACITY);
    load("");
    memset(vi_file_mem, 'a', FILELENG);
    vi_file_mem[FILELENG-1] = '\n';
    vi_file_end = vi_file_max;
    vi_renum = FILELENG; input = "y"; normal('y');
    assert(savednum == FILELENG && !vi_changed);
    vi_renum = FILELENG; input = "d"; normal('d');
    assert(vi_file_end == vi_file_mem && vi_changed);
    run_edit("u");
    assert(vi_file_end == vi_file_max);
    for(i=0; i<FILELENG-1; i++) assert(vi_file_mem[i] == 'a');
    assert(vi_file_mem[FILELENG-1] == '\n');
    vi_changed = 0;
    vi_curs_char = vi_file_mem;
    inschar('X');
    assert(vi_file_end == vi_file_max && !vi_changed);
    assert(vi_curs_char == vi_file_mem && vi_file_mem[0] == 'a');
    normal('P');
    assert(vi_file_end == vi_file_max && !vi_changed);
    for(i=0; i<FILELENG-1; i++) assert(vi_file_mem[i] == 'a');
}
static void check_capacity(void) {
    static unsigned sizes[] = {32767U, 32768U, 40000U, 40064U};
    char *original = vi_file_mem;
    char expected[40];
    unsigned i;
    vi_file_mem = calloc(40065U, 1); assert(vi_file_mem);
    for(i=0; i<sizeof sizes/sizeof sizes[0]; i++) {
        vi_file_max = vi_file_mem + sizes[i];
        load("abc\n");
        run_edit("oZ\033"); expect("abc\nZ\n");
        load("abc\n");
        run_edit("OZ\033"); expect("Z\nabc\n");
        load("");
        run_edit("i\t\033"); expect("    \n");
        load("keep\n"); assert(yankline(1));
        load(""); putline(1); expect("keep\n");
        memset(vi_file_mem, 'x', sizes[i]);
        vi_file_end = vi_file_max;
        vi_curs_char = vi_file_end - 1;
        command(".=\n");
        sprintf(expected, "character %u", sizes[i]);
        assert(strstr(last_output, expected) != NULL);
    }
    free(vi_file_mem);
    vi_file_mem = original;
    vi_file_max = vi_file_mem + FILELENG;
    load("");
}
static void check_string_failures(void) {
    char *name, *cursor;
    int calls, live, dirty;
    load("a b a b a\n");
    dosearch(FORWARD, "b");
    assert(vi_curs_char == vi_file_mem+2);
    calls = string_alloc_calls; live = string_live;
    fail_string_alloc = 1;
    assert(strsave("test") == NULL);
    dosearch(BACKWARD, "a");
    assert(vi_curs_char == vi_file_mem+2 && string_live == live);
    assert(strstr(last_output, "unable to find memory"));
    calls = string_alloc_calls;
    repsearch();
    assert(vi_curs_char == vi_file_mem+6 && string_alloc_calls == calls);
    fail_string_alloc = 0;
    for(dirty=0; dirty<=1; dirty++) {
        load("keep\ntext\n");
        vi_changed=dirty; vi_curs_char++;
        strcpy(vi_undo_buff,"rZ"); strcpy(vi_redo_buff,"rX");
        vi_uncurs_char=vi_file_mem;
        name=vi_file_name; cursor=vi_curs_char;
        fail_string_alloc=fail_message_alloc=1;
        command("f replacement.txt\n");
        assert(vi_file_name == name && strstr(last_output,"unable to find memory"));
        command("e! replacement.txt\n");
        assert(vi_file_name == name && vi_curs_char == cursor);
        assert(vi_changed == dirty);
        expect("keep\ntext\n");
        assert(!strcmp(vi_undo_buff,"rZ") && !strcmp(vi_redo_buff,"rX"));
        assert(readfile("replacement.txt",vi_file_mem,0) == -1);
        assert(vi_file_name == name);
        expect("keep\ntext\n");
        fail_string_alloc=fail_message_alloc=0;
    }
}
static void check_filename_ownership(void) {
    char *same;
    int i, live, calls;
    seed("opened\n");
    assert(vi_set_filename("XXinsert.txt"));
    assert(vi_set_filename(vi_file_name+2));
    assert(!strcmp(vi_file_name,"insert.txt"));
    same=vi_file_name; calls=string_alloc_calls;
    fail_string_alloc=1;
    assert(vi_set_filename(vi_file_name));
    assert(vi_file_name == same && string_alloc_calls == calls);
    fail_string_alloc=0;
    live=string_live;
    for(i=0; i<200; i++) {
        command("f first.txt\n");
        command("f second.txt\n");
        command("e! insert.txt\n");
        expect("opened\n");
        assert(!vi_changed && vi_uncurs_char == NULL);
        command("e!\n");
        expect("opened\n");
        assert(string_live == live);
    }
    assert(vi_set_filename("XXinsert.txt"));
    load("");
    assert(!readfile(vi_file_name+2,vi_file_mem,0));
    assert(!strcmp(vi_file_name,"insert.txt"));
    expect("opened\n");
}
static void check_quality_commands(void) {
    static const struct {
        const char *before, *keys, *after;
        int changed, untouched;
    } cases[] = {
        {"","J","",0,1}, {"",">>","",0,1}, {"","<<","",0,1},
        {"\n","<<","\n",0,1}, {"plain","<<","plain",0,1},
        {"\ta\nb\n\tc","3<<u","\ta\nb\n\tc",0},
        {"\ta\nb\n\tc","3<<uu","a\nb\nc",1},
        {"a\nb\nc","3>>u","a\nb\nc",0},
        {"a\nb\nc","3>>uu","\ta\n\tb\n\tc",1},
        {"\t","<<u","\t",0}, {"a\n\t","2<<u","a\n\t",0},
        {"a\n\t\n","2<<u","a\n\t\n",0},
        {"a\nb","Ju","a\nb",0}, {"a\nb","Juu","ab",1},
        {"a\n\n","Ju","a\n\n",0}, {"\n\n","Ju","\n\n",0},
        {"\na","Ju","\na",0}, {"a\nb\nc","J.","abc",1},
        {"a\nb\nc","2>>.","\t\ta\n\t\tb\nc",1},
        {"\ta\nb\n\tc","3<<.u","\ta\nb\n\tc",0},
        {"a\nb","3>\033","a\nb",0,1},
        {"a\nb","65536>>","a\nb",0,1},
        {"a\nb",":f other\033","a\nb",0,1},
        {"abc\n","2~.","ABC\n",1},
        {"a\nb\nc","2dd","c",1},
        {"a\nb","65535>>u","a\nb",0},
        {"\ta\nb","65535<<u","\ta\nb",0},
        {"a\nb","JJu","a\nb",0},
        {"a\nb","J.u","a\nb",0},
        {"a\nb","J<<u","a\nb",0},
        {"a\nb","RZ\033Ju","Z\nb",1},
        {"\ta\nb\nc\nd\ne\nf\ng\n\th\n\ti","9<<u",
         "\ta\nb\nc\nd\ne\nf\ng\n\th\n\ti",0}
    };
    unsigned i;
    int dirty;
    for(dirty=0; dirty<=1; dirty++)
        for(i=0; i<sizeof cases/sizeof cases[0]; i++) {
            load(cases[i].before);
            vi_changed=dirty;
            strcpy(vi_undo_buff,"rZ"); strcpy(vi_redo_buff,"rX");
            vi_uncurs_char=vi_file_mem;
            run_edit(cases[i].keys);
            if(vi_file_end-vi_file_mem != (long)strlen(cases[i].after) ||
               memcmp(vi_file_mem,cases[i].after,strlen(cases[i].after)) ||
               vi_changed != (dirty || cases[i].changed)) {
                fprintf(stderr,"Quality corpus failure: case %u, dirty %d\n",i,dirty);
                assert(0);
            }
            assert(vi_state == NORMAL && vi_curs_char >= vi_file_mem &&
                   (vi_curs_char < vi_file_end || vi_curs_char == vi_file_mem));
            if(cases[i].untouched) {
                assert(!strcmp(vi_undo_buff,"rZ") && !strcmp(vi_redo_buff,"rX"));
                assert(vi_uncurs_char==vi_file_mem);
            }
        }
}
static void check_quality_rejections(void) {
    int dirty, i;
    char many_lines[16385];
    char *cursor, *maximum=vi_file_mem+FILELENG;
    for(dirty=0; dirty<=1; dirty++) {
        load("a\nb\nc");
        vi_changed=dirty; vi_curs_char++;
        vi_file_max=vi_file_end+3;
        strcpy(vi_undo_buff,"rZ"); strcpy(vi_redo_buff,"rX");
        vi_uncurs_char=vi_file_mem; cursor=vi_curs_char;
        vi_renum=3; input=">"; normal('>');
        expect("a\nb\nc");
        assert(vi_changed==dirty && vi_curs_char==cursor);
        assert(!strcmp(vi_undo_buff,"rZ") && !strcmp(vi_redo_buff,"rX"));
        vi_file_max=maximum;
        load("plain");
        vi_changed=dirty; vi_curs_char++;
        strcpy(vi_undo_buff,"rZ"); strcpy(vi_redo_buff,"rX");
        vi_uncurs_char=vi_file_mem; cursor=vi_curs_char;
        vi_renum=3; input="<"; normal('<');
        normal('J');
        expect("plain");
        assert(vi_changed==dirty && vi_curs_char==cursor);
        assert(!strcmp(vi_undo_buff,"rZ") && !strcmp(vi_redo_buff,"rX"));
        load("");
        memset(vi_file_mem,'\n',8193); vi_file_end=vi_file_mem+8193;
        strcpy(vi_undo_buff,"rZ"); strcpy(vi_redo_buff,"rX");
        vi_changed=dirty;
        run_edit("8193>>");
        assert(vi_file_end==vi_file_mem+8193 && vi_changed==dirty);
        for(i=0;i<8193;i++) assert(vi_file_mem[i]=='\n');
        assert(!strcmp(vi_undo_buff,"rZ") && !strcmp(vi_redo_buff,"rX"));
        assert(strstr(last_output,"too big for undo"));
        load("");
        memset(vi_file_mem,'a',FILELENG); vi_file_mem[2]='\n';
        vi_file_end=vi_file_max; vi_changed=dirty;
        run_edit("Ju");
        assert(vi_file_end==vi_file_max && vi_changed==dirty);
        for(i=0;i<FILELENG;i++) assert(vi_file_mem[i]==(i==2?'\n':'a'));
        vi_file_mem[0]='\t';
        run_edit("<<u");
        assert(vi_file_end==vi_file_max && vi_changed==dirty);
        assert(vi_file_mem[0]=='\t');
        for(i=1;i<FILELENG;i++) assert(vi_file_mem[i]==(i==2?'\n':'a'));
        for(i=0;i<8191;i++) {
            many_lines[2*i]='x'; many_lines[2*i+1]='\n';
        }
        strcpy(many_lines+16382,"\tx");
        load(many_lines); vi_changed=dirty;
        run_edit("8192<<u");
        expect(many_lines); assert(vi_changed==dirty);
    }
}
int main(int argc, char **argv) {
    assert(vi_yank_init());
    vi_file_mem = calloc(FILELENG, 1); assert(vi_file_mem);
    vi_file_max = vi_file_mem + FILELENG;
    vi_file_name = strsave("TEST.TXT"); assert(vi_file_name);
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
    else if(!strcmp(argv[1], "insert-backspace")) check_insert_backspace();
    else if(!strcmp(argv[1], "keyboard-batch")) check_keyboard_batch();
    else if(!strcmp(argv[1], "single-mark")) check_single_mark();
    else if(!strcmp(argv[1], "search-bounds")) check_search_bounds();
    else if(!strcmp(argv[1], "command-limits")) check_command_limits();
    else if(!strcmp(argv[1], "count-limits")) check_count_limits();
    else if(!strcmp(argv[1], "delete-limits")) check_delete_limits();
    else if(!strcmp(argv[1], "insert-limits")) check_insert_limits();
    else if(!strcmp(argv[1], "literal-limits")) check_literal_limits();
    else if(!strcmp(argv[1], "replay-limits")) check_replay_limits();
    else if(!strcmp(argv[1], "file-insert-limits")) check_file_insert_limits();
    else if(!strcmp(argv[1], "long-messages")) check_long_messages();
    else if(!strcmp(argv[1], "yank-failures")) check_yank_failures();
    else if(!strcmp(argv[1], "yank-success")) check_yank_success();
    else if(!strcmp(argv[1], "yank-message-failure")) check_yank_message_failure();
    else if(!strcmp(argv[1], "put-failures")) check_put_failures();
    else if(!strcmp(argv[1], "large-binary-put")) check_large_binary_put();
    else if(!strcmp(argv[1], "full-buffer")) check_full_buffer();
    else if(!strcmp(argv[1], "capacity")) check_capacity();
    else if(!strcmp(argv[1], "string-failures")) check_string_failures();
    else if(!strcmp(argv[1], "filename-ownership")) check_filename_ownership();
    else if(!strcmp(argv[1], "quality-commands")) check_quality_commands();
    else if(!strcmp(argv[1], "quality-rejections")) check_quality_rejections();
    else assert(0);
    clearlastmess();
    vi_yank_close();
    free(vi_file_mem);
    test_string_free(vi_file_name);
    printf("PASS: %s\n", argv[1]);
    return 0;
}
'''


def main():
    source = (ROOT / 'main.c').read_text()
    globals_ = source[source.index('#ifdef VI_DOS1_COM'):source.index('int main(')]
    readfile = function(source, 'int readfile(char *fname, char *fromp,')
    misc = (ROOT / 'misccmds.c').read_text()
    primitives = ('static int canincrease(unsigned n);\n'
                  'static void appchar(int c);\n'
                  'static unsigned savednum, savedcount;\n'
                  'static int savedlast;\n')
    primitives += r'''
static void *edit_memmove(void *to, const void *from, size_t length) {
    edit_moves++;
    edit_moved_bytes += length;
    return memmove(to, from, length);
}
#define memmove edit_memmove
'''
    primitives += '#define vi_yank_store test_yank_store\n'
    primitives += '#define vi_yank_load test_yank_load\n'
    primitives += function(misc, 'int yankline(unsigned n)') + '\n'
    for signature in ('static int canincrease(unsigned n)\n', 'void insstr(char *s)',
                      'void inschar(int c)', 'void delchar(void)',
                      'int deleol(void)', 'int delword(int deltrailing)',
                      'void fileinfo(void)', 'void putline(int k)',
                      'void delline(unsigned nlines)', 'static void appchar(int c)\n',
                      'void opencmd(void)'):
        primitives += function(misc, signature) + '\n'
    primitives += '\n#undef memmove\n'
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
        line_source = work / 'lines.c'
        line_source.write_text(
            '#include <stdlib.h>\nvoid *test_string_malloc(size_t);\n'
            'void test_string_free(void *);\n'
            '#define malloc test_string_malloc\n#define free test_string_free\n'
            f'#include "{ROOT / "linefunc.c"}"\n')
        command_source.write_text(
            '#include <stdlib.h>\nvoid *test_message_malloc(size_t);\n'
            '#define malloc test_message_malloc\n'
            f'#include "{ROOT / "cmdline.c"}"\n')
        harness.write_text(HARNESS + globals_ + primitives + queue + editor +
                           '#define getc test_getc\n#define ferror test_ferror\n'
                           '#define fclose test_fclose\n' + readfile +
                           '\n#undef getc\n#undef ferror\n#undef fclose\n' + CHECKS)
        binary = work / 'check'
        failed = []
        cases = ('save', 'read', 'replace', 'search', 'insert-read',
                 'read-limits', 'read-errors', 'word-eof', 'bulk-insert',
                 'insert-backspace',
                 'keyboard-batch',
                 'single-mark',
                 'search-bounds', 'command-limits', 'count-limits', 'delete-limits',
                 'insert-limits', 'literal-limits', 'replay-limits',
                 'file-insert-limits', 'long-messages', 'yank-failures',
                 'yank-success', 'yank-message-failure', 'put-failures',
                 'large-binary-put', 'full-buffer', 'capacity', 'string-failures',
                 'filename-ownership', 'quality-commands', 'quality-rejections')
        selected = sys.argv[1:] or cases
        if any(case not in cases for case in selected):
            raise SystemExit('Unknown editor-state test case')
        for profile, flags in (
                ('38016', []), ('DOS1-EXE-38016', ['-D__PCDOS__=11']),
                ('DOS1-COM-18432', ['-D__PCDOS__=11', '-DVI_DOS1_COM'])):
            subprocess.run([
                os.environ.get('CC_HOST', 'cc'), '-std=c99', '-g',
                '-fsanitize=address,undefined', *flags, '-I', str(ROOT), str(harness),
                str(command_source), str(ROOT / 'normal.c'),
                str(line_source), str(ROOT / 'yankmem.c'),
                str(ROOT / 'test/yankmock.c'), '-o', str(binary),
            ], check=True)
            for case in selected:
                try:
                    result = subprocess.run([str(binary), case], cwd=work, timeout=10)
                except subprocess.TimeoutExpired:
                    failed.append(profile + ': ' + case + ' (timed out)')
                    continue
                if result.returncode:
                    failed.append(profile + ': ' + case)
            print('EDITOR STATE PROFILE:', profile, flush=True)
        if failed:
            raise SystemExit('Failed: ' + ', '.join(failed))


if __name__ == '__main__':
    main()
