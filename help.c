/*
 * STevie - ST editor for VI enthusiasts.    ...Tim Thompson...twitch!tjt...
 */

#include "ctype.h"
#include "stevie.h"

static int helprow;

help()
{
	windclear();
	windgoto(helprow=0,0);
longline("\n"
"   Cursor movement commands:\n"
"   ^l         Redraw screen\n"
"   ^d         Down 1/2 screen\n"
"   ^u         Up 1/2 screen\n"
"   ^f         Forward 1 screen\n");
longline(""
"   ^b         Back 1 screen\n"
"   ^g         Give info on file\n"
"\n"
"      h              Left 1 char\n"
"      j              Down 1 char\n"
"      k              Up 1 char\n");
longline(""
"      l              Right 1 char\n"
"      $              End of line\n"
"      ^ -or- 0       Beginning of line\n"
"      b              Back 1 word\n");
longline(""
"      w              Forward 1 word\n"
"      [#]G           Goto line # (or last line if no #)\n"
"\n"
"<Press space to continue>\n"
"<Any other key to quit>");
	windrefresh();
	if ( vgetc() != ' ' )
		return;
	windclear();
	windgoto(helprow=0,0);
longline("\n"
"    Modification commands\n"
"    =====================\n"
"    x           Delete 1 char\n"
"    dw          Delete 1 word\n"
"    D           Delete rest of line\n"
"    [#]dd       Delete 1 (or #) lines\n"
"    C           Change rest of line\n");
longline(
"    cw          Change word\n"
"    cc          Change line\n"
"    r           Replace single character\n"
"    [#]yy       Yank 1 (or #) lines\n"
"    p           Insert last yanked/deleted line(s)\n");
longline(""
"    P              below (p)/above (P) current line\n"
"    J           Join current and next line\n"
"    [#]<<          Shift line left 1 (or #) tabs\n"
"    [#]>>          Shift line right 1 (or #) tabs\n"
"    i           Enter Insert mode (<ESC> to exit)\n");
longline(""
"    a           Append (<ESC> to exit) \n"
"    o           Open line (<ESC> to exit)\n"
"\n"
"<Press space to continue>\n"
"<Any other key to quit>");
	windrefresh();
	if ( vgetc() != ' ' )
		return;
	windclear();
	windgoto(helprow=0,0);
longline("\n"
"    Miscellaneous:\n"
"    .           Repeat last insert/delete\n"
"    u           Undo last insert/delete\n"
"    /str/       Search for 'str'\n"
"    ?str?       Search back for 'str'\n");
longline("    n           Repeat previous search\n"
"    :.=         Print current line #\n"
"    :$=         Print # lines in file\n"
"    H		Help\n"
"\n"
"    File manipulation:\n");
longline(""
"    :w          Write file\n"
"    :wq         Write and quit\n"
"    :e {file}   Edit a new file\n"
"    :e!         Re-read current file\n"
"    :f          Print file info\n");
longline(""
"    :f {file}   Change current file name\n"
"    :q          Quit\n"
"    :q!         Quit (no save)\n"
"\n"
"<Press any key>");
	windrefresh();
	vgetc();
}

longline(p)
char *p;
{
	char *s;

	for ( s=p; *s; s++ ) {
		if ( *s == '\n' )
			windgoto(++helprow,0);
		else
			windputc(*s);
	}
}
