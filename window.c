/*
 * STevie - ST editor for VI enthusiasts.    ...Tim Thompson...twitch!tjt...
 */

#include "stevie.h"
#include "stdio.h"
#include "sgtty.h"

#define GETCH_BUFLEN 64
static char getch_buffer[GETCH_BUFLEN];

getch()
{
    int i,c,d;
    static int s=0;
    static int o=0;

    if(s>0) {
        c=getch_buffer[o];s--;o++;
        o=o%GETCH_BUFLEN;
        return c;
    }
    while(!(c=bdos(6,255))) 
        continue;
    while(s<GETCH_BUFLEN && (d=bdos(6,255))) {
        if(1) { 
            getch_buffer[(o+s)%GETCH_BUFLEN]=d;
            s++;
        }
    }
    return c;
}


windinit()
{
	struct sgttyb stty;
	stty.sg_flags = CRMOD|CBREAK;
	ioctl(0, TIOCSETP, &stty);

	Columns=80;
	Rows=24;
	/* Here we want no echo, disable line buffering / erase kill
	   and no newline - curses noecho(), cbreak(), nonl() */
}

windgoto(r,c)
int r,c;
{
	/* Locate cursor */
	/* CP/M-86 VT-52 */
#ifdef __VT52__
	printf("\033Y%c%c",r+0x20,c+0x20);
#else 
	/* ANSI (1-based row/col, r and c here are 0-based) */
	printf("\033[%d;%dH",r+1,c+1);
#endif
}

windexit(r)
int r;
{
	exit(r);
}

windclreol() 
{
#ifdef __VT52__
	printf("\033I");
#else 
	/* ANSI */
	printf("\033[K");
#endif
}

windclear()
{
#ifdef __VT52__
	/* Clear the screen */
	/* CP/M-86 VT-52 */
	printf("\033E");
#else
	/* ANSI */
	printf("\033[2J\033[H");
#endif
}

windgetc()
{
	return(getch());
}

windstr(s)
char *s;
{
	printf("%s",s);
}

windputc(c)
int c;
{
	putchar(c);
}

windrefresh()
{
	/* Need a redraw here? */
}

beep()
{
	putchar('\007');
}
