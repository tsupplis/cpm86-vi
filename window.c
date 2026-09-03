/*
 * STevie - ST editor for VI enthusiasts.    ...Tim Thompson...twitch!tjt...
 */

#include "stevie.h"
#include "stdio.h"
#ifdef __CPM86__
#include "sgtty.h"
#endif

#define GETCH_BUFLEN 64
static char getch_buffer[GETCH_BUFLEN];

/* ------------------------------------------------------------------ */
/* CP/M-86 implementation                                              */
/* ------------------------------------------------------------------ */
#if defined(__CPM86__)

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
#if defined(__VT52__)
	printf("\033Y%c%c",r+0x20,c+0x20);
#elif defined(_VT100_)
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
#if defined(__VT52__)
	printf("\033K");
#elif defined(_VT100_)
	printf("\033[K");
#endif
}

windcursor(on)
int on;
{
#if defined(__VT52__)
	/* ESC f = cursor off, ESC e = cursor on (CP/M-86 >= 2.2) */
	printf(on ? "\033e" : "\033f");
#elif defined(_VT100_)
	printf(on ? "\033[?25h" : "\033[?25l");
#endif
}

windcolor(fg)
int fg;
{
#if defined(__VT52__)
	/* ESC b <c> sets foreground colour (CGA: 2=green) */
	printf("\033b%c", (char)fg);
#elif defined(_VT100_)
	/* ANSI SGR: 30+fg for foreground (0=black,1=red,2=green,...) */
	printf("\033[3%dm", fg);
#endif
}

windcolorreset()
{
#if defined(__VT52__)
	/* Restore default foreground colour (white=7) */
	printf("\033b\007");
#elif defined(_VT100_)
	printf("\033[0m");
#endif
}

windclear()
{
#if defined(__VT52__)
	printf("\033E");
#elif defined(_VT100_)
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

#endif /* __CPM86__ */
