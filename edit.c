/*
 * STevie - ST editor for VI enthusiasts.     ...Tim Thompson...twitch!tjt...
 */

#include "stdio.h"
#include "ctype.h"
#include "stevie.h"

/* ------------------------------------------------------------------ */
/* Raw keyboard input                                                  */
/* ------------------------------------------------------------------ */
#if defined(__PCBIOS__)

/* One pending byte, for the second half of a synthesized ESC sequence. */
static int pending = -1;

/* INT 16h AH=0: wait for a keystroke, return AH=scan code, AL=ASCII in AX. */
bioskey()
{
#asm
	mov ah, 0
	int 16h
#endasm
}

/* INT 16h AH=1: non-zero if a keystroke is waiting (doesn't consume it). */
keyready()
{
#asm
	mov ah, 1
	int 16h
	jz keyready_none
	mov ax, 1
	jmp keyready_done
keyready_none:
	mov ax, 0
keyready_done:
#endasm
}

getch()
{
	int c, al, ah;

	if ( pending >= 0 ) {
		c = pending;
		pending = -1;
		return c;
	}
	for ( ;; ) {
		/* Don't block in INT 16h: CP/M-86's background clock/status
		 * update can reposition the BIOS cursor while we're blocked,
		 * with no chance for us to correct it until a key arrives.
		 * Poll instead, re-asserting our cursor position every time
		 * around, so any interference is fought at high frequency
		 * instead of just once, best-effort, after the fact. */
		while ( !keyready() )
			windrefreshcursor();
		c = bioskey();
		al = c & 0xff;
		ah = (c >> 8) & 0xff;
		if ( al != 0 )
			return al;
		/* Extended key: no ASCII, decode the BIOS scan code in AH. */
		switch ( ah ) {
		case 0x48: pending='A'; return 27;	/* Up */
		case 0x50: pending='B'; return 27;	/* Down */
		case 0x4D: pending='C'; return 27;	/* Right */
		case 0x4B: pending='D'; return 27;	/* Left */
		case 0x47: pending='H'; return 27;	/* Home */
		case 0x49: pending='I'; return 27;	/* Page Up */
		case 0x51: return '\n';		/* Page Down */
		case 0x4F: return '\032';		/* End */
		case 0x52: pending='L'; return 27;	/* Insert */
		case 0x53: return '\177';		/* Delete */
		}
	}
}

#elif defined(__CPM86__)

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

#endif /* __PCBIOS__ / __CPM86__ */

/* OS-independent wrapper around whichever getch() is active above. */
windgetc()
{
	return(getch());
}

edit()
{
	int c, c1, c2;
	char *p, *q;
	/* Buffer to save original chars overwritten in Replace mode,
	 * so backspace can restore them. */
	static char replbuf[1024];
	static char *replptr = NULL;

	Prenum = 0;

	/* position the display and the cursor at the top of the file. */
	Topchar = Filemem;
	Curschar = Filemem;
	Cursrow = Curscol = 0;

	if(State == INSERT)
		message ("Insert");
	else
		message("");

	{
	int laststate = -1;	/* forces the mode message on the first pass */
	for ( ;; ) {
        /* Figure out where the cursor is based on Curschar. */
        cursupdate();
        /* Only (re)announce the mode when it actually changes, so a
         * command's own message (e.g. "File not written out...") isn't
         * immediately clobbered on the very next loop iteration. */
        if ( State != laststate ) {
            if ( State == INSERT )
                message("Insert Mode");
            else if ( State == REPLACE )
                message("Replace Mode");
            else if ( State == NORMAL )
                message("Normal Mode");
            laststate = State;
        }
        /* printf("Curschar=(%d,%d) row/col=(%d,%d)",
            Curschar,*Curschar,Cursrow,Curscol); */
        windgoto(Cursrow,Curscol);
        windrefresh();
        c = vgetc();
        switch(State) {
        case NORMAL:
            /* We're in the normal (non-insert) mode. */
            if(c==27) {
                /* VT52 and the DOS BIOS key mapping both send a lone ESC
                 * followed directly by a letter; VT100/ANSI sends ESC '['. */
#if defined(__VT52__) || defined(__PCBIOS__)
                State=NORMAL_ESCAPE;
#elif defined(__VT100__)
                State=BRACKET_ESCAPE;
#endif
                break;
            }
            /* End and Page-Down arrive as bare bytes, with no ESC prefix */
            if ( c=='\032' ) {		/* End key -> end of line */
                Prenum=0;
                normal('$');
                break;
            }
            if ( c=='\n' ) {		/* Page-Down key -> forward 1 screen */
                Prenum=0;
                normal(06);
                break;
            }
            donormal(c);
            break;
        case BRACKET_ESCAPE:
            /* A lone ESC (not followed by '[') is just the usual */
            /* harmless "make sure we're in Normal mode" keystroke; */
            /* the character that follows must still be executed. */
            if(c=='[') {
                State=NORMAL_ESCAPE;
                Prenum=0;
                break;
            }
            State=NORMAL;
            if ( c==27 )
                State=BRACKET_ESCAPE;
            else
                donormal(c);
            break;
        case NORMAL_ESCAPE:
            {
                int d=0;
                switch(c) {
                    case 'A':
                        d='k';   
                        break;
                    case 'B':
                        d='j';   
                        break;
                    case 'C':
                        d='l';   
                        break;
                    case 'D':
                        d='h';   
                        break;
                    case 'H':	/* Home key -> beginning of line */
                        d='0';
                        break;
                    case 'I':	/* Page Up key -> back 1 screen */
                        d=02;
                        break;

                }
                State=NORMAL;
                if(d) {
                    Prenum=0;
                    normal(d);    
                }
                /* Same as above: don't drop a keystroke that turns */
                /* out not to be part of an escape sequence. */
                else if ( c==27 ) {
#if defined(__VT52__) || defined(__PCBIOS__)
                    State=NORMAL_ESCAPE;
#elif defined(__VT100__)
                    State=BRACKET_ESCAPE;
#endif
                }
                else
                    donormal(c);
            }
            break;
        case INSERT:
            /* We're in insert mode. */
            switch(c){
            case '\033':	/* an ESCape ends input mode */

                /* If we're past the end of the file, (which should */
                /* only happen when we're editing a new file or a */
                /* file that doesn't have a newline at the end of */
                /* the line), add a newline automatically. */
                if ( Curschar >= Fileend ) {
                    insertchar('\n');
                    Curschar--;
                }

                /* Don't end up on a '\n' if you can help it. */
                if ( Curschar>Filemem && *Curschar=='\n'
                    && *(Curschar-1)!='\n' ) {
                    Curschar--;
                }
                State = NORMAL;
                message("");
                Uncurschar = Insstart;
                Undelchars = Ninsert;
                /* Undobuff[0] = '\0'; */
                /* construct the Redo buffer */
                p=Redobuff;
                q=Insbuff;
                while ( q<Insptr )
                    *p++ = *q++;
                *p++ = '\033';
                *p = '\0';
                updatescreen();
                break;
            case '\b':
                if ( Curschar <= Insstart )
                    beep();
                else {
                    char *target;
                    Curschar--;
                    target = Curschar;
                    delchar();
                    /* delchar() may back Curschar up further to avoid */
                    /* landing on a trailing newline (for Normal mode); */
                    /* Insert mode always wants it exactly at 'target'. */
                    Curschar = target;
                    Insptr--;
                    Ninsert--;
                    cursupdate();
                    updatescreen();
                }
                break;
            case '\030':	/* control-x */ 
                { int wasnewline = 0; char *p1;
                p1 = Curschar;
                if ( *Curschar == '\n' )
                    wasnewline = 1;
                inschar('[');
                inschar('x');
                cursupdate();
                updatescreen();
                c1 = gethexchar();
                inschar(c1);
                cursupdate();
                updatescreen();
                c2 = gethexchar();
                Curschar = p1;
                delchar();
                delchar();
                delchar();
                c = 16*hextoint(c1)+hextoint(c2);
                if(Debug)printf("(c=%d)",c);
                if ( wasnewline )
                    Curschar++;
                inschar(c);
                Ninsert++;
                *Insptr++ = c;
                updatescreen();
                break;
                }
            case 0x09:
                insertchar(' ');
                insertchar(' ');
                insertchar(' ');
                insertchar(' ');
                break;
            case 0x0F:	
                break;
            case 0x0D:	/* <CR> */
            case 0x0A:	/* <CR> */
                insertchar(0x0A);
                c = 0x0D;
                /* This is SUPPOSED to fall down into 'default' */
                break;
            default:
                insertchar(c);
                break;
            }
            break;
        case REPLACE:
            /* Initialise save buffer on first entry */
            if ( replptr == NULL )
                replptr = replbuf;
            switch(c) {
            case '\033':	/* ESC exits replace mode */
                /* Don't end up on a '\n' */
                if ( Curschar>Filemem && *Curschar=='\n'
                    && *(Curschar-1)!='\n' )
                    Curschar--;
                State = NORMAL;
                /* Save originals for undo */
                Unrplchars = (int)(replptr - replbuf);
                if ( Unrplchars > 0 ) {
                    char *s = replbuf, *d = Replbuf;
                    int k = Unrplchars;
                    while ( k-- > 0 ) *d++ = *s++;
                    UndoChanged = Changed;
                }
                replptr = NULL;
                updatescreen();
                break;
            case '\b':	/* backspace: restore original char */
                if ( replptr > replbuf ) {
                    replptr--;
                    Curschar--;
                    *Curschar = *replptr;
                    CHANGED;
                    cursupdate();
                    updatescreen();
                } else {
                    beep();
                }
                break;
            default:
                if ( isprint(c) || c=='\t' ) {
                    /* Save original char before overwriting */
                    if ( replptr < replbuf + sizeof(replbuf) - 1 ) {
                        /* If at end of file or newline, insert instead */
                        if ( Curschar >= Fileend || *Curschar == '\n' ) {
                            inschar(c);
                        } else {
                            *replptr++ = *Curschar;
                            *Curschar = c;
                            CHANGED;
                            if ( Curschar+1 < Fileend )
                                Curschar++;
                        }
                        cursupdate();
                        updatescreen();
                    }
                }
                break;
            }
            break;
        }
 }
 }
}

/*
 * donormal(c)
 *
 * Feed a character to the Normal-mode command interpreter, first
 * collecting any leading digits into 'Prenum'.
 */
donormal(c)
int c;
{
	if ( (Prenum>0 && isdigit(c)) || (isdigit(c) && c!='0') ) {
		Prenum = Prenum*10 + (c-'0');
		return;
	}
	/* Forget the last message: a command that repeats the same warning
	 * (e.g. "Pattern not found" on two failed searches in a row) must
	 * still show it, not have it silently suppressed as unchanged. */
	clearlastmess();
	normal(c);
	Prenum = 0;
}

insertchar(c)
int c;
{
	char *p;

	if ( ! anyinput() ) {
		inschar(c);
		*Insptr++ = c;
		Ninsert++;
	}
	else {
		/* If there's any pending input, grab */
		/* it all at once. */
		p = Insptr;
		*Insptr++ = c;
		Ninsert++;
		while ( (c=vpeekc()) != '\033' ) {
			c = vgetc();
			*Insptr++ = c;
			Ninsert++;
		}
		*Insptr = '\0';
		insstr(p);
	}
	updatescreen();
}

gethexchar()
{
	int c;

	for ( ;; ) {
		windgoto(Cursrow,Curscol);
		windrefresh();
		c = vgetc();
		if ( hextoint(c) >= 0 )
			break;
		clearlastmess();
		message("Expecting a hexidecimal character (0-9 or a-f)");
		beep();
		/* sleep(1); */
	}
	return(c);
}

getout()
{
	windgoto(Rows-1,0);
	windrefresh();
	putchar('\r');
	putchar('\n');
	windexit(0);
}

cursupdate()
{
	char *p;
	int inc, c, nlines;

	/* special case: file is completely empty */
	if ( Fileend == Filemem ) {
		Topchar = Curschar = Filemem;
	}
	else if ( Curschar < Topchar ) {
		nlines = cntlines(Curschar,Topchar);
		/* if the cursor is above the top of */
		/* the screen, put it at the top of the screen.. */
		Topchar = Curschar;
		/* ... and, if we weren't very close to begin with, */
		/* we scroll so that the line is close to the middle. */
		if ( nlines > Rows/3 )
			scrolldown(Rows/3);
		else {
			/* make sure we have the current line completely */
			/* on the screen, by setting Topchar to the */
			/* beginning of the current line (in a strange way). */
			if ( (p=prevline(Topchar))!=NULL &&
				(p=nextline(p))!=NULL ) {
				Topchar = p;
			}
		}
		updatescreen();
	}
	else if ( Curschar >= Botchar && Curschar < Fileend ) {
		nlines = cntlines(Botchar,Curschar);
		/* If the cursor is off the bottom of the screen, */
		/* put it at the top of the screen.. */
		Topchar = Curschar;
		/* ... and back up */
		if ( nlines > Rows/3 )
			scrolldown((2*Rows)/3);
		else
			scrolldown(Rows-2);
		updatescreen();
	}

	Cursrow = Curscol = Cursvcol = 0;
	{ int wrapped = 0;
	for ( p=Topchar; p<Curschar; p++ ) {
		c = *p;
		if ( c == '\n' ) {
			/* If the previous line filled exactly Columns chars
			 * the wrap already incremented Cursrow — don't do it
			 * again for the \n or the cursor lands one row too low.
			 * Two consecutive \n (blank line) still works because
			 * wrapped is cleared after each \n. */
			if ( !wrapped )
				Cursrow++;
			Curscol = Cursvcol = wrapped = 0;
			continue;
		}
		/* A tab gets expanded, depending on the current column */
		if ( c == '\t' )
			inc = (8 - (Curscol)%8);
		else
			inc = chars[(unsigned)(c & 0xff)].ch_size;
		Curscol += inc;
		Cursvcol += inc;
		if ( Curscol >= Columns ) {
			Curscol -= Columns;
			Cursrow++;
			wrapped = 1;
		} else {
			wrapped = 0;
		}
	}
	}
}

scrolldown(nlines)
int nlines;
{
	int n;
	char *p;

	/* Scroll up 'nlines' lines. */
	for ( n=nlines; n>0; n-- ) {
		if ( (p=prevline(Topchar)) == NULL )
			break;
		Topchar = p;
	}
}

/*
 * oneright
 * oneleft
 * onedown
 * oneup
 *
 * Move one char {right,left,down,up}.  Return 1 when
 * sucessful, 0 when we hit a boundary (of a line, or the file).
 */

oneright()
{
	char *p;

	p = Curschar;
	if ( (*p++)=='\n' || p>=Fileend || *p == '\n' )
		return(0);
	Curschar++;
	return(1);
}

oneleft()
{
	char *p;

	p = Curschar;
	if ( *p=='\n' || p==Filemem || *(p-1) == '\n' )
		return(0);
	Curschar--;
	return(1);
}

beginline()
{
	while ( oneleft() )
		;
}

oneup(n)
{
	char *p, *np;
	int savevcol, k;

	savevcol = Cursvcol;
	p = Curschar;
	for ( k=0; k<n; k++ ) {
		/* Look for the previous line */
		if ( (np=prevline(p)) == NULL ) {
			/* If we've at least backed up a little .. */
			if ( k > 0 )
				break;	/* to update the cursor, etc. */
			else
				return(0);
		}
		p = np;
	}
	Curschar = p;
	/* This makes sure Topchar gets updated so the complete line */
	/* is one the screen. */
	cursupdate();
	/* try to advance to the same (virtual) column */
	/* that we were at before. */
	Curschar = coladvance(p,savevcol);
	return(1);
}

onedown(n)
{
	char *p, *np;
	int k;

	p = Curschar;
	for ( k=0; k<n; k++ ) {
		/* Look for the next line */
		if ( (np=nextline(p)) == NULL ) {
			if ( k > 0 )
				break;
			else
				return(0);
		}
		p = np;
	}
	/* try to advance to the same (virtual) column */
	/* that we were at before. */
	Curschar = coladvance(p,Cursvcol);
	return(1);
}
