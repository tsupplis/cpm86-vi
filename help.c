/*
 * STevie - ST editor for VI enthusiasts.    ...Tim Thompson...twitch!tjt...
 */

#include "ctype.h"
#include "stevie.h"

static helpstr(s)
char *s;
{
	while (*s)
		windputc(*s++);
}

help()
{
	windclear();

	windgoto( 0, 0); helpstr("  --- Movement --------------------   --- Insert / Replace -----------");
	windgoto( 1, 0); helpstr("  h j k l      left/down/up/right     i        insert before cursor");
	windgoto( 2, 0); helpstr("  b / w        back / forward word    a        append after cursor");
	windgoto( 3, 0); helpstr("  ^ 0 / $      begin / end of line    o        open new line below");
	windgoto( 4, 0); helpstr("  [#]G         goto line (G=last)     r <c>    replace single char");
	windgoto( 5, 0); helpstr("  ^F / ^B      fwd / back screen      R        replace mode  (ESC)");
	windgoto( 6, 0); helpstr("  ^D / ^U      down / up 10 lines");
	windgoto( 7, 0); helpstr("  ^G  file info   ^L  redraw          --- Delete ---------------------");
	windgoto( 8, 0); helpstr("                                       x        delete char");
	windgoto( 9, 0); helpstr("  --- Search ------------------------  [#]dd    delete # lines");
	windgoto(10, 0); helpstr("  /str  ?str   fwd / back search       dw       delete word");
	windgoto(11, 0); helpstr("  n  // ??     repeat search           d$ / D / delete to end of line");
	windgoto(12, 0); helpstr("                                       --- Change --------------------");
	windgoto(13, 0); helpstr("  --- Yank & Put --------------------- cc       change line");
	windgoto(14, 0); helpstr("  [#]yy        yank # lines            cw       change word");
	windgoto(15, 0); helpstr("  p / P        put after / before      c$ / C / change to end of line");
	windgoto(16, 0); helpstr("                                       --- Misc ---------------------");
	windgoto(17, 0); helpstr("  --- : Commands --------------------- u / .    undo / redo");
	windgoto(18, 0); helpstr("  :w [f]  :wq  :x   write / quit       J        join lines");
	windgoto(19, 0); helpstr("  :q  :q!           quit               >> <<    indent");
	windgoto(20, 0); helpstr("  :e[!] [f]  :r f   edit / read file");
	windgoto(21, 0); helpstr("  :f [n]  :.=  :$=  :set oct|hex|dec  :h / H   this help");
	windgoto(Rows-1, 0);
	windcolor(2);
	helpstr("  Press any key ...");
	windcolorreset();

	windrefresh();
	vgetc();
	screenclear();
	/* Reset message cache so the main loop's message("Normal Mode")
	 * repaints the status line after returning from help. */
	message("");
	updatescreen();
}
