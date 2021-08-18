#include "stevie.h"
#include "stdio.h"
#include "sgtty.h"

static char buffer[64];

getch()
{
    int i,c,d;
    static int s=0;

    if(s>0) {
        c=buffer[s-1];s--;
        return c;
    }
    while(!(c=bdos(6,255))) 
        continue;
    while(s<64 && (d=bdos(6,255)))
        buffer[s++]=d;
    return c;
}

main() {
    int c=0;
    
    while(c!='q' && c!='Q') {
        c=getch();
        printf("0x%02x(%c)\n",c,c>31?c:'.');
    }
    return 0;
}
