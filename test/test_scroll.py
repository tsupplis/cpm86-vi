#!/usr/bin/env python3
"""Test real cursor/viewport and renderer functions with status-row guards."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
root=Path(__file__).resolve().parents[1]

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
#include "yankmem.h"
struct charinfo chars[256];
int vi_state=NORMAL, vi_rows=6, vi_columns=10;
int vi_curs_col;
unsigned long vi_curs_row, vi_curs_vcol;
char *vi_file_mem, *vi_file_end, *vi_top_char, *vi_bot_char, *vi_curs_char;
static char screen_line[VI_SCREEN_MAX_COLUMNS], screen_previous[VI_SCREEN_MAX_COLUMNS];
static char file[4096], screen[VI_SCREEN_IMAGE_SIZE], reference_screen[VI_SCREEN_IMAGE_SIZE];
static char displayed[VI_SCREEN_IMAGE_SIZE];
static char displays[256][17];
static int renders, terminal_position, writes, runs;
static void check(int ok, char *why) { if (!ok) { fprintf(stderr,"FAIL: %s\n",why); exit(1); } }
static void screenerror(void) { check(0,"external screen storage"); }
void windgoto(int r, int c) {
    check(r>=0 && r<vi_rows-1 && c>=0 && c<vi_columns,"terminal cursor bounds");
    terminal_position=r*vi_columns+c;
}
void windputc(int c) {
    check(terminal_position<(vi_rows-1)*vi_columns,"no terminal writes in status row");
    displayed[terminal_position++]=(char)c;
    writes++;
}
void windputrun(const char *text, unsigned length) {
    check(length>0 && length<=vi_columns-terminal_position%vi_columns,
          "output runs stay within one row");
    runs++;
    while(length--) {
        check((unsigned char)*text>=' ',"control characters keep single-byte output");
        windputc((unsigned char)*text++);
    }
}
void windclear(void) { memset(displayed,' ',sizeof displayed); }
void windcolor(int color) { check(color==2,"tilde color"); }
void windcolorreset(void) {}
void windrefresh(void) {}
static void readscreen(unsigned image, char *destination) {
    int row;
    for(row=0; row<vi_rows; row++)
        check(vi_screen_load(image,row,destination+row*vi_columns),"read screen image");
}
static void reset_display(void) {
    int row;
    check(vi_screen_configure(vi_rows,vi_columns),"configure screen");
    memset(screen_line,'Z',sizeof screen_line);
    for(row=0; row<vi_rows; row++) {
        check(vi_screen_store(VI_SCREEN_REAL,row,screen_line),"seed real screen");
        check(vi_screen_store(VI_SCREEN_NEXT,row,screen_line),"seed next screen");
    }
    memset(displayed,'Z',sizeof displayed);
    writes=runs=0;
}
static void guard(void) {
    int i;
    readscreen(VI_SCREEN_NEXT,screen);
    check(vi_curs_row>=0 && vi_curs_row<vi_rows-1,"cursor stays in document viewport");
    check(vi_curs_col>=0 && vi_curs_col<vi_columns,"cursor column in range");
    for(i=(vi_rows-1)*vi_columns;i<vi_rows*vi_columns;i++)
        check(screen[i]=='Z',"renderer leaves status row untouched");
}
/* Frozen pre-segmentation renderer, used as the behavioral reference. */
static void reference(char *image, char **bottom) {
    int row=0, col=0, nextra=0, c, n;
    char *screenp=image, *memp=vi_top_char, *lastmemp=memp;
    char *endscreen=image+(vi_rows-1)*vi_columns, *nextrow, extra[16], *p;
    while(screenp<endscreen && (memp<vi_file_end || nextra>0)) {
        if(nextra>0) c=extra[--nextra];
        else {
            lastmemp=memp;
            c=(unsigned char)*memp++;
            if((n=chars[c].ch_size)>1) {
                p=chars[c].ch_str;
                while(n>1) extra[nextra++]=p[--n];
                c=p[0];
            }
        }
        if(c=='\n') {
            row++;
            nextrow=image+row*vi_columns;
            while(screenp!=nextrow) *screenp++=' ';
            col=0;
            continue;
        }
        if(col>=vi_columns) { row++; col=0; }
        *screenp++=c;
        col++;
    }
    *bottom=screenp>=endscreen && nextra>0 ? lastmemp : memp;
    while(screenp<endscreen) *screenp++=' ';
    if(col!=0) row++;
    else if(vi_file_end==vi_file_mem && vi_state==INSERT) row=1;
    while(row<vi_rows-1) image[row++*vi_columns]='~';
}
'''
source+=function('main.c','static void filetonext(void)')
source+=function('main.c','static void nexttoscreen(void)')
source+=function('main.c','void screenclear(void)')
source+=r'''
void updatescreen(void) {
    char *bottom;
    int previous_writes, size=vi_rows*vi_columns;
    renders++;
    readscreen(VI_SCREEN_NEXT,reference_screen);
    reference(reference_screen,&bottom);
    filetonext();
    readscreen(VI_SCREEN_NEXT,screen);
    check(!memcmp(screen,reference_screen,size),"renderer matches original frame");
    check(vi_bot_char==bottom,"renderer matches original Botchar");
    nexttoscreen();
    check(!memcmp(displayed,screen,size),"terminal matches desired frame");
    readscreen(VI_SCREEN_REAL,reference_screen);
    check(!memcmp(screen,reference_screen,size),"real image tracks terminal");
    previous_writes=writes;
    nexttoscreen();
    check(writes==previous_writes,"unchanged screen emits no characters");
}
'''
for signature in ['static void cursor_position(void)','static char *next_screen_row(char *p)','void cursupdate(void)']:
    source+=function('edit.c',signature)
for signature in ['char *nextline(char *curr)','char *prevline(char *curr)','char *coladvance(char *p, unsigned long col)']:
    source+=function('linefunc.c',signature)
source+=function('edit.c','int oneup(unsigned n)')+function('edit.c','int onedown(unsigned n)')
source+=r'''
static void load(char *text) {
    strcpy(file,text); vi_file_mem=file; vi_file_end=file+strlen(file);
    vi_top_char=vi_curs_char=file;
    reset_display(); renders=0;
    cursupdate(); updatescreen(); guard();
}
int main(void) {
    int i, j;
    char lines[1024];
    unsigned random=17;
    check(vi_yank_init(),"reserve external segment");
    for(i=0;i<256;i++) {
        displays[i][0]=(char)i; displays[i][1]=0;
        chars[i].ch_size=1; chars[i].ch_str=displays[i];
    }
    chars[1].ch_size=2; chars[1].ch_str="^A";
    chars[9].ch_size=8; chars[9].ch_str="        ";
    load("abcdefghij\nklmnopqrst\n");
    check(runs==vi_rows-1,"one output run per changed row");
    runs=writes=0;
    file[4]='X';
    updatescreen();
    check(runs==1 && writes==1,"single-cell edit writes one short run");
    load("a\rb\n");
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
    for(i=0;i<500;i++) {
        int length, top, k;
        random=random*1664525U+1013904223U;
        vi_columns=1+random%80;
        random=random*1664525U+1013904223U;
        vi_rows=3+random%23;
        random=random*1664525U+1013904223U;
        length=random%sizeof(file);
        for(j=0;j<length;j++) {
            random=random*1664525U+1013904223U;
            k=random%20;
            file[j]=k==0?'\n':k==1?'\t':k==2?1:'a'+k;
        }
        top=length?random%length:0;
        vi_file_mem=file; vi_file_end=file+length;
        vi_top_char=vi_curs_char=file+top;
        vi_state=i%2?INSERT:NORMAL;
        vi_curs_row=vi_curs_col=0;
        reset_display();
        updatescreen(); guard();
    }
    check(vi_yank_store("keep",4),"seed yank");
    screenclear();
    readscreen(VI_SCREEN_NEXT,screen);
    readscreen(VI_SCREEN_REAL,reference_screen);
    for(i=0;i<vi_rows*vi_columns;i++)
        check(screen[i]==' ' && reference_screen[i]==' ' && displayed[i]==' ',"clear both screens");
    check(vi_yank_load(0,screen_line,4) && !memcmp(screen_line,"keep",4),"clear preserves yank");
    vi_yank_close();
    puts("PASS: scrolling, paging, 500 renderer parity cases, screen diff/clear and status-row guards");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='vi-scroll-') as folder:
    work=Path(folder); (work/'scroll.c').write_text(source)
    subprocess.run([os.environ.get('CC_HOST','cc'),'-std=gnu89','-Wno-comment','-fsanitize=address,undefined',
                    '-I'+str(root),str(work/'scroll.c'),str(root/'yankmem.c'),
                    str(root/'test/yankmock.c'),'-o',str(work/'scroll')],check=True)
    subprocess.run([str(work/'scroll')],check=True)
