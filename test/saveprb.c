#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "save.h"
static char large[513];
static int sizes[]={0,1,127,128,129,255,256,257};
static char errors[512];
static char text[]="a\nb", binarytext[]="z\032q", empty[]="";
int main(int argc, char **argv)
{
    const char *error;
    FILE *f;
    int i,c,fail,j,k,expected;
    long exact;
    int require_exact;
    fail=0;
    require_exact=argc>1 && !strcmp(argv[1],"LRBC");
    memset(large,'x',sizeof large);
    for(j=0;j<8;j++) {
        k=sizes[j];
        error=vi_save_file("SAVE.TST",large,large+k,1);
        if(error) fail++;
        exact=vi_file_length("SAVE.TST");
        if(require_exact && exact<0L) fail++;
        if(exact>=0L && exact!=(long)k) fail++;
        f=fopen("SAVE.TST","r");
        if(!f) return 1;
        for(i=0;i<k;i++) if(getc(f)!='x') fail++;
#ifdef __CPM86__
        expected=((k+127)/128)*128;
#else
        expected=k;
#endif
        for(;i<expected;i++) if(getc(f)!=0) fail++;
        if(getc(f)!=EOF) fail++;
        fclose(f);
    }
    error=vi_save_file("SAVE.TST",large,large+sizeof large,1);
    if(error) { strcat(errors,error); strcat(errors,"\n"); puts(error); fail++; }
    error=vi_save_file("SAVE.TST",text,text+3,0);
    if(error) { strcat(errors,error); strcat(errors,"\n"); puts(error); fail++; }
    exact=vi_file_length("SAVE.TST");
    if(require_exact && exact<0L) fail++;
    if(exact>=0L && exact!=5L) fail++;
    f=fopen("SAVE.TST","r");
    if(!f) return 1;
    if(getc(f)!='a'||getc(f)!='\r'||getc(f)!='\n'||getc(f)!='b') fail++;
#ifdef __CPM86__
    if(getc(f)!=0x1a) fail++;
    /* FAT-backed DOS Plus may zero-pad bytes beyond its exact EOF. */
    for(i=5;i<128;i++) { c=getc(f); if(c!=0x1a && c!=0) fail++; }
#else
    i=4;
#endif
    if(getc(f)!=EOF) fail++;
    fclose(f);
    error=vi_save_file("SAVE.TST",binarytext,binarytext+3,1);
    if(error) { strcat(errors,error); strcat(errors,"\n"); puts(error); fail++; }
    exact=vi_file_length("SAVE.TST");
    if(require_exact && exact<0L) fail++;
    if(exact>=0L && exact!=3L) fail++;
    f=fopen("SAVE.TST","r");
    if(!f) return 1;
    if(getc(f)!='z'||getc(f)!=0x1a||getc(f)!='q') fail++;
#ifdef __CPM86__
    for(i=3;i<128;i++) if(getc(f)!=0) fail++;
#endif
    if(getc(f)!=EOF) fail++;
    fclose(f);
    error=vi_save_file("SAVE.TST",empty,empty,1);
    if(error) { strcat(errors,error); strcat(errors,"\n"); puts(error); fail++; }
    exact=vi_file_length("SAVE.TST");
    if(require_exact && exact<0L) fail++;
    if(exact>=0L && exact!=0L) fail++;
    f=fopen("SAVE.TST","r");
    if(!f) return 1;
    if(getc(f)!=EOF) fail++;
    fclose(f);
    unlink("SAVE.TST");
    f=fopen("RESULT.TXT","w");
    if(!f) return 1;
    fprintf(f,"VI SAVE %s: %d failures\n",fail?"FAIL":"PASS",fail);
    fputs(errors,f);
    fclose(f);
    printf("VI SAVE %s: %d failures\n",fail?"FAIL":"PASS",fail);
    return fail!=0;
}
