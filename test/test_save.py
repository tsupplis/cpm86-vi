#!/usr/bin/env python3
"""Exercise save.c on host files, with injected I/O and CP/M service failures.
Only BDOS pointer-width casts are adapted for the 64-bit host harness.
"""
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
HARNESS = r'''
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <assert.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/stat.h>
static int identity=0x1022, user=3, fail_flush, fail_close, fail_resize;
static int rename_count, fail_rename, deny_open, truncate_calls, attr_calls;
int bdosver(void) { return identity; }
static void filename(unsigned char *f, char *name) {
 int i,n=0;
 for(i=1;i<9 && (f[i]&127)!=' ';i++) name[n++]=f[i]&127;
 if((f[9]&127)!=' ') { name[n++]='.'; for(i=9;i<12 && (f[i]&127)!=' ';i++) name[n++]=f[i]&127; }
 name[n]=0;
}
int fcbinit(char *name,void *buffer) {
 unsigned char *f=buffer; int i=1,u=255; char *dot;
 memset(f,0,36); memset(f+1,' ',11);
 if(strchr(name,'/')) { u=atoi(name); name=strchr(name,'/')+1; }
 if(strchr(name,':')) name=strchr(name,':')+1;
 dot=strchr(name,'.');
 while(*name && name!=dot && i<9) f[i++]=*name++;
 if(dot) {name=dot+1;i=9;while(*name && i<12)f[i++]=*name++;}
 return u;
}
int bdos(int fn,long arg) {
 unsigned char *f=(unsigned char *)arg; char name[16]; struct stat st;long n;
 if(fn==32) { if(arg!=255) user=(int)arg; return user; }
 filename(f,name);
 if(fn==15) { if(f[32]==255) { if(stat(name,&st))return 255; f[32]=st.st_size%128; } return 0; }
 if(fn==16) return 0;
 if(fn==35) {
  if(stat(name,&st))return 255;
  n=(st.st_size+127)/128; f[33]=n;f[34]=n>>8;f[35]=n>>16;return 0;
 }
 if(fn==99) {
  truncate_calls++; if(fail_resize)return 255;
  n=f[33]+((long)f[34]<<8)+((long)f[35]<<16);
  return truncate(name,(n+1)*128)?255:0;
 }
 if(fn==30) {
  attr_calls++;assert(f[6]&128);if(fail_resize)return 255;
  if(stat(name,&st))return 255;
  n=st.st_size;if(n && f[32])n=((n-1)/128)*128+f[32];
  return truncate(name,n)?255:0;
 }
 assert(0);return 255;
}
static int test_open(const char *name,int flags,...) {
 if(deny_open && !strcmp(name,"FILE.TST")) { errno=EACCES;return -1; }
 return open(name,flags,0600);
}
static int test_flush(FILE *f) { int r=fflush(f);return fail_flush?EOF:r; }
static int test_close(FILE *f) { int r=fclose(f);return fail_close?EOF:r; }
static int test_resize(int fd,long size) {return fail_resize?-1:ftruncate(fd,size);}
static int test_rename(const char *a,const char *b) {
 rename_count++;if(fail_rename && rename_count>=fail_rename){errno=EACCES;return -1;}
 return rename(a,b);
}
#define open test_open
#define fflush test_flush
#define fclose test_close
#define ftruncate test_resize
#define rename test_rename
#include "subject.c"
#undef open
#undef fflush
#undef fclose
#undef ftruncate
#undef rename
static char original[513];
static void seed(void) {
 FILE *f=fopen("FILE.TST","wb");assert(f);memset(original,'X',sizeof original);
 assert(fwrite(original,1,sizeof original,f)==sizeof original);assert(!fclose(f));
}
static long size(void) {struct stat st;assert(!stat("FILE.TST",&st));return st.st_size;}
static void expect(const char *data,int n,long total,int pad) {
 FILE *f=fopen("FILE.TST","rb");int i;assert(f);
 for(i=0;i<n;i++)assert(getc(f)==(unsigned char)data[i]);
 for(;i<total;i++)assert(getc(f)==pad);
 assert(getc(f)==EOF);fclose(f);assert(size()==total);
}
int main(void) {
 const char *error; char text[]="a\nb", binary[]={'a',26,0,'b'};
 seed();error=vi_save_file("FILE.TST",text,text+3,0);assert(!error);
#ifdef __CPM86__
 expect("a\r\nb\032",5,128,26);assert(user==3);
#else
 expect("a\r\nb",4,4,0);
#endif
 error=vi_save_file("FILE.TST",binary,binary+4,1);assert(!error);
#ifdef __CPM86__
 expect(binary,4,128,0);
#else
 expect(binary,4,4,0);
#endif
 error=vi_save_file("FILE.TST",text,text,1);assert(!error);assert(size()==0);
 seed();deny_open=1;assert(vi_save_file("FILE.TST",text,text+3,0));deny_open=0;assert(size()==513);
 seed();fail_flush=1;assert(vi_save_file("FILE.TST",text,text+3,0));fail_flush=0;
 seed();fail_close=1;assert(vi_save_file("FILE.TST",text,text+3,0));fail_close=0;
#ifdef __CPM86__
 assert(capabilities(0x1031)==1 && capabilities(0x1431)==1);
 assert(capabilities(0x1041)==3 && capabilities(0x1042)==0);
 assert(capabilities(0x1231)==0 && capabilities(0x1022)==0);
 seed();rename_count=0;fail_rename=2;
 assert(vi_save_file("FILE.TST",text,text+3,0));fail_rename=0;
 /* Both failed install and failed restoration retain the original backup. */
 assert(access("FILE.TST",F_OK)!=0);
 seed();identity=0x1031;truncate_calls=0;
 assert(!vi_save_file("FILE.TST",text,text+3,0));assert(truncate_calls==1);assert(size()==128);
 seed();identity=0x1431;assert(!vi_save_file("FILE.TST",text,text+3,0));assert(size()==128);
 seed();identity=0x1041;attr_calls=0;
 assert(!vi_save_file("FILE.TST",text,text+3,0));assert(attr_calls==1);expect("a\r\nb\032",5,5,0);assert(vi_file_length("FILE.TST")==5);
 seed();fail_resize=1;assert(vi_save_file("FILE.TST",text,text+3,0));fail_resize=0;
 identity=0x1031;seed();assert(!vi_save_file("7/FILE.TST",text,text+3,0));assert(user==3);
 assert(vi_save_file("*.TST",text,text+3,0));assert(user==3);
#else
 seed();fail_resize=1;assert(vi_save_file("FILE.TST",text,text+3,0));fail_resize=0;
#endif
 puts("SAVE HOST PASS");return 0;
}
'''

def main():
    with tempfile.TemporaryDirectory(prefix='vi-save-') as directory:
        work=Path(directory)
        (work/'save.h').write_text((ROOT/'save.h').read_text())
        (work/'subject.c').write_text((ROOT/'save.c').read_text().replace('(int)fcb','(long)fcb'))
        (work/'dos.h').write_text('')
        (work/'cpm.h').write_text('int bdos(int,long); int fcbinit(char *,void *);\n')
        (work/'test.c').write_text(HARNESS)
        for target in ('dos','cpm'):
            run=work/target;run.mkdir()
            flags=['-D__CPM86__'] if target=='cpm' else []
            subprocess.run(['cc','-std=c99','-g','-fsanitize=address,undefined','-I',str(work),*flags,str(work/'test.c'),'-o',str(run/'test')],check=True)
            subprocess.run([str(run/'test')],cwd=run,check=True)
def editor_state():
    source=(ROOT/'cmdline.c').read_text()
    a=source.index('static int writeit(char *fname)\n{')
    b=source.index('\nvoid filemess',a)
    body=source[a:b]
    harness=r'''#include <stdio.h>
#include <assert.h>
static char text[]="test";
static char *vi_file_mem=text,*vi_file_end=text+4;
static int vi_binary,vi_changed=1,reject;
#define UNCHANGED vi_changed=0
void message(char *s) {(void)s;}
const char *vi_save_file(const char *n,const char *a,const char *b,int binary) {
 assert(a==vi_file_mem && b==vi_file_end);return reject?"injected failure":0;
}
''' + body + r'''
int main(void) {
 reject=1;assert(!writeit("test") && vi_changed==1);
 reject=0;assert(writeit("test") && vi_changed==0);
 puts("SAVE EDITOR STATE PASS");return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix='vi-save-state-') as directory:
        work=Path(directory);(work/'test.c').write_text(harness)
        subprocess.run(['cc',str(work/'test.c'),'-o',str(work/'test')],check=True)
        subprocess.run([str(work/'test')],check=True)
if __name__=='__main__':
    main()
    editor_state()

