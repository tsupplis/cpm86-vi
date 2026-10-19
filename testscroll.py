#!/usr/bin/env python3
"""Test real cursor/viewport and renderer functions with status-row guards."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
root=Path(__file__).resolve().parent

def function(filename, signature):
    text=(root/filename).read_text(); start=re.search(re.escape(signature)+r'\s*\{',text).start()
    brace=text.index('{',start); depth=1; end=brace+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}'); end+=1
    return text[start:end]+'\n'

source=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stevie.h"
struct charinfo chars[256];
int vi_state=NORMAL, vi_rows=6, vi_columns=10;
int vi_curs_row, vi_curs_col, vi_curs_vcol;
char *vi_file_mem, *vi_file_end, *vi_top_char, *vi_bot_char, *vi_curs_char;
char *vi_next_scr;
static char file[4096], screen[256];
static char displays[256][17];
static int renders;
static void check(int ok, char *why) { if (!ok) { fprintf(stderr,"FAIL: %s\n",why); exit(1); } }
static void guard(void) {
    int i;
    check(vi_curs_row>=0 && vi_curs_row<vi_rows-1,"cursor stays in document viewport");
    check(vi_curs_col>=0 && vi_curs_col<vi_columns,"cursor column in range");
    for(i=(vi_rows-1)*vi_columns;i<vi_rows*vi_columns;i++)
        check(screen[i]=='Z',"renderer leaves status row untouched");
}
'''
source+=function('main.c','static void filetonext(void)')
source+='void updatescreen(void) { renders++; filetonext(); }\n'
for signature in ['static void cursor_position(void)','static char *next_screen_row(char *p)','void cursupdate(void)']:
    source+=function('edit.c',signature)
for signature in ['char *nextline(char *curr)','char *prevline(char *curr)','char *coladvance(char *p, int col)']:
    source+=function('linefunc.c',signature)
source+=function('edit.c','int oneup(int n)')+function('edit.c','int onedown(int n)')
source+=r'''
static void load(char *text) {
    strcpy(file,text); vi_file_mem=file; vi_file_end=file+strlen(file);
    vi_top_char=vi_curs_char=file; vi_next_scr=screen;
    memset(screen,'Z',sizeof(screen)); renders=0;
    cursupdate(); updatescreen(); guard();
}
int main(void) {
    int i, j;
    char lines[1024];
    for(i=0;i<256;i++) {
        displays[i][0]=(char)i; displays[i][1]=0;
        chars[i].ch_size=1; chars[i].ch_str=displays[i];
    }
    chars[1].ch_size=2; chars[1].ch_str="^A";
    chars[9].ch_size=8; chars[9].ch_str="        ";
    lines[0]=0; for(i=0;i<20;i++) strcat(lines,"01234\n");
    load(lines);
    for(i=1;i<20;i++) {
        check(onedown(1),"down succeeds"); cursupdate(); guard();
        check(vi_top_char==file+(i>4?i-4:0)*6,"down scrolls one row at boundary");
    }
    for(i=18;i>=0;i--) {
        check(oneup(1),"up succeeds"); cursupdate(); guard();
        check(vi_top_char==file+(i<15?i:15)*6,"up scrolls one row at boundary");
    }
    vi_curs_char=file+3; cursupdate();
    check(onedown(vi_rows-1),"page down"); cursupdate(); guard();
    check(vi_curs_char==file+5*6+3,"page down retains column");
    check(oneup(vi_rows-1),"page up"); cursupdate(); guard();
    check(vi_curs_char==file+3,"page up inverse and column symmetric");
    load("1234567890\nx\n"); vi_curs_char=file+11; cursupdate(); guard();
    check(vi_top_char==file && vi_curs_row==1,"exact-width newline wraps once");
    vi_curs_char=file+10; cursupdate(); guard();
    check(vi_curs_row==0 && vi_curs_col==9,"full-row EOL never leaks to next row");
    load("\n\n\n\n\n\n");
    for(i=1;i<6;i++) { vi_curs_char=file+i; cursupdate(); guard(); }
    for(i=4;i>=0;i--) { vi_curs_char=file+i; cursupdate(); guard(); }
    memset(lines,'x',200); strcpy(lines+200,"\nend\n"); load(lines);
    for(i=0;i<204;i++) { vi_curs_char=file+i; cursupdate(); updatescreen(); guard(); }
    for(i=203;i>=0;i--) { vi_curs_char=file+i; cursupdate(); updatescreen(); guard(); }
    load("123456789\001Z\n"); vi_curs_char=file+10; cursupdate(); guard();
    check(vi_curs_row==1 && vi_curs_col==1,"expanded char straddling wrap uses renderer coordinates");
    load("\001");
    check(screen[0]=='^' && screen[1]=='A',"last expanded file character renders completely");
    vi_state=INSERT;
    load(""); guard();
    load("1234567890\nx\n"); vi_curs_char=vi_file_end; cursupdate(); updatescreen(); guard();
    puts("PASS: symmetric scrolling, paging, wrapped/blank/long lines, EOF and status-row guards");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='vi-scroll-') as folder:
    work=Path(folder); (work/'scroll.c').write_text(source)
    subprocess.run([os.environ.get('CC_HOST','cc'),'-std=gnu89','-Wno-comment','-fsanitize=address,undefined',
                    '-I'+str(root),str(work/'scroll.c'),'-o',str(work/'scroll')],check=True)
    subprocess.run([str(work/'scroll')],check=True)
