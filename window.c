/*
 * STevie - ST editor for VI enthusiasts.    ...Tim Thompson...twitch!tjt...
 */

#include "stevie.h"
#include "stdio.h"
#include "sgtty.h"

#ifdef __CPM86__
getch()
{
    int i,c,d;
    static int s=0;

    if(s>0) {
        c=s;s=0;
        return c;
    }
    while(!(c=bdos(6,255)));
    while(d=bdos(6,255));
    return c;
}
#endif

windinit()
{
#ifndef __CPM86__
	/* Initialise tty */
	struct sgttyb stty;
	stty.sg_flags = CBREAK|CRMOD;
	ioctl(0, TIOCSETP, &stty);
#endif

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
	/* ANSI */
	printf("\033[%d;%dH",r,c);
#endif
}

windexit(r)
int r;
{
	exit(r);
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
#ifdef __CPM86__
	return(getch());
#else
	return(getchar());
#endif
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
