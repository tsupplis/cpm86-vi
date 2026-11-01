/* File saving shared by the editor and its regression harness. */
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include "save.h"
#ifdef __CPM86__
#include <cpm.h>
/* Full AX from BDOS 12; the generic bdos() wrapper returns AL only. */
extern int bdosver(void);
#else
#include <dos.h>
#endif
int open(const char *, int, ...);

#ifdef __CPM86__
/* Exact known identities, not a guessed version threshold. Unknown/remote
 * systems use replacement. LRBC interpretation is enabled only for DOS Plus. */
static int capabilities(int identity)
{
    switch(identity) {
    case 0x1031: case 0x1431: return 1; /* record truncate */
    case 0x1041: return 3;             /* DOS Plus: used-byte LRBC */
    default: return 0;
    }
}

static int newname(const char *name, char *out, const char *ext)
{
    const char *p;
    int prefix, i, fd;
    p=strchr(name, ':');
    prefix=p ? (int)(p-name)+1 : 0;
    if(prefix>2) { errno=EINVAL; return -1; }
    memcpy(out,name,prefix);
    for(i=0;i<100;i++) {
        sprintf(out+prefix,"VI%06d.%s",i,ext);
        fd=open(out,O_RDWR|O_CREAT|O_EXCL,0666);
        if(fd>=0) return fd;
        if(errno!=EEXIST) return -1;
    }
    return -1;
}

static int finish_cpm(const char *name, long bytes, long previous, int caps)
{
    unsigned char fcb[36];
    long records;
    int rc;
    records=(bytes+127L)/128L;
    memset(fcb,0,sizeof fcb);
    if(fcbinit((char *)name,fcb)<0) return -1;
    if((caps&1) && records<(previous+127L)/128L) {
        /* F_TRUNCATE names the last retained record (zero-based). */
        records--;
        fcb[33]=(unsigned char)records;
        fcb[34]=(unsigned char)(records>>8);
        fcb[35]=(unsigned char)(records>>16);
        rc=bdos(99,(int)fcb)&255;
        if(rc>3) return -1;
    }
    if(caps&2) {
        /* Reload attributes before F_ATTRIB; never clear R/O/system/archive. */
        memset(fcb,0,sizeof fcb);
        fcbinit((char *)name,fcb);
        if((bdos(15,(int)fcb)&255)>3) return -1;
        if((bdos(16,(int)fcb)&255)>3) return -1;
        fcb[6]|=0x80;
        fcb[32]=(unsigned char)(bytes%128L);
        if((bdos(30,(int)fcb)&255)>3) return -1;
    }
    return 0;
}
#endif

const char *vi_save_file(const char *name, const char *start,
                         const char *end, int binary)
{
    FILE *f;
    int fd, existing, failed;
    long bytes;
    const char *p, *error;
#ifdef __CPM86__
    char temp[16], backup[16];
    unsigned char fcb[36];
    int caps, olduser, user, reserve, replacement;
    long previous;
    static char recovery[100];
    temp[0]=backup[0]=0;
    memset(fcb,0,sizeof fcb);
    if(strchr(name,'*') || strchr(name,'?')) return "Ambiguous file name!";
    user=fcbinit((char *)name,fcb);
    if(user<0) return "Invalid file name!";
    /* fcbinit handles [user/][drive:] names; keep all operations in that user. */
    olduser=bdos(32,255)&255;
    if(user!=255) bdos(32,user);
    p=strchr(name,'/');
    if(p) name=p+1;
    caps=capabilities(bdosver());
    replacement=0;
#endif
    error=NULL;
    existing=1;
    fd=open(name,O_RDWR);
    if(fd<0) {
        if(errno!=ENOENT) { error="Unable to open file for writing!"; goto done; }
        existing=0;
        /* Never delete an existing file after an ambiguous open failure. */
        fd=open(name,O_RDWR|O_CREAT|O_EXCL,0666);
    }
    if(fd<0) { error="Unable to create file!"; goto done; }
#ifdef __CPM86__
    previous=0L;
    if(existing && (caps&1)) {
        memset(fcb,0,sizeof fcb);
        fcbinit((char *)name,fcb);
        if((bdos(35,(int)fcb)&255)==255) {
            close(fd); error="Unable to query original size!"; goto done;
        }
        previous=((long)fcb[33] | ((long)fcb[34]<<8) |
                  ((long)fcb[35]<<16))*128L;
    }
    if(existing && (!(caps&1) || (binary && start==end))) {
        if(close(fd)<0) { error="Unable to close original!"; goto done; }
        fd=newname(name,temp,"TMP");
        if(fd<0) { error="Unable to create temporary file!"; goto done; }
        replacement=1;
    }
#endif
    f=fdopen(fd,"w");
    if(!f) { close(fd); error="Unable to buffer file!"; goto done; }
    bytes=0L;
    failed=0;
    for(p=start;p<end;p++) {
        if(!binary && *p=='\n') {
            if(putc('\r',f)==EOF) { failed=1; break; }
            bytes++;
        }
        if(putc((unsigned char)*p,f)==EOF) { failed=1; break; }
        bytes++;
    }
#ifdef __CPM86__
    /* CP/M text EOF; DOS text ends at its exact byte length. */
    if(!failed && !binary) {
        if(putc(0x1a,f)==EOF) failed=1;
        else bytes++;
    }
    if(!failed) {
        int padding;
        padding=(int)((128L-bytes%128L)%128L);
        while(padding--) if(putc(binary?0:0x1a,f)==EOF) { failed=1; break; }
    }
#endif
    if(fflush(f)==EOF || ferror(f)) failed=1;
#ifndef __CPM86__
    if(!failed && ftruncate(fd,bytes)<0) failed=1;
#endif
    if(fclose(f)==EOF) failed=1;
    if(failed) { error="Write/resize/close failed; buffer not saved!"; goto done; }
#ifdef __CPM86__
    if(!replacement) {
        if(finish_cpm(name,bytes,previous,caps)<0)
            error="File written but size update failed!";
    } else {
        /* Reserve a unique backup name. CP/M rename cannot replace a file. */
        reserve=newname(name,backup,"BAK");
        if(reserve<0) { backup[0]=0; error="Unable to reserve backup!"; goto done; }
        if(close(reserve)<0 || unlink(backup)<0) {
            error="Unable to prepare backup!"; goto done;
        }
        if(rename(name,backup)<0) { error="Unable to rename original!"; goto done; }
        if(rename(temp,name)<0) {
            /* Keep both recovery files if restoration also fails. */
            if(rename(backup,name)==0) backup[0]=0;
            error="Unable to install saved file!";
            goto done;
        }
        temp[0]=0;
        if(unlink(backup)<0) {
            error="Saved, but backup removal failed!"; goto done;
        }
        backup[0]=0;
    }
#endif
 done:
#ifdef __CPM86__
    if(error && (temp[0] || backup[0])) {
        sprintf(recovery,"Save failed; retain %s%s%s (user %d)",temp,
                temp[0] && backup[0]?" and ":"",backup, user==255?olduser:user);
        error=recovery;
    }
    bdos(32,olduser);
#endif
    return error;
}

/* Query before opening the stream: CP/M I/O itself remains record-oriented.
 * Only DOS Plus has a verified used-byte LRBC convention in this policy. */
long vi_file_length(const char *name)
{
#ifdef __CPM86__
    unsigned char fcb[36];
    int user, olduser, last;
    long records, result;
    if(!(capabilities(bdosver())&2)) return -1L;
    memset(fcb,0,sizeof fcb);
    user=fcbinit((char *)name,fcb);
    if(user<0) return -1L;
    olduser=bdos(32,255)&255;
    if(user!=255) bdos(32,user);
    result=-1L;
    if((bdos(35,(int)fcb)&255)!=255) {
        records=(long)fcb[33]|((long)fcb[34]<<8)|((long)fcb[35]<<16);
        memset(fcb,0,sizeof fcb);
        fcbinit((char *)name,fcb);
        fcb[32]=255;
        if((bdos(15,(int)fcb)&255)<=3) {
            last=fcb[32];
            fcb[32]=0;
            if((bdos(16,(int)fcb)&255)<=3 && last<=128)
                result=records ? (records-1L)*128L+(last?last:128) : 0L;
        }
    }
    bdos(32,olduser);
    return result;
#else
    return -1L;
#endif
}
