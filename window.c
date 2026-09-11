/*
 * STevie - ST editor for VI enthusiasts.    ...Tim Thompson...twitch!tjt...
 */

#include "stevie.h"
#include "stdio.h"
#ifdef __CPM86__
#include "sgtty.h"
#endif
#include "gitver.h"

/* Build-variant version string for the ":v" command; lives here since
 * window.c is already compiled once per variant with the right macros.
 * Hierarchical: OS first (__CPM86__ / __PCDOS__=11 / __PCDOS__=20), then
 * screen/keyboard technique within it. */
char *viversion()
{
	static char buf[80];

#if defined(__CPM86__)
#if defined(__PCBIOS__)
	sprintf(buf, "VI for CP/M-86 %s (bios mode)", GIT_VERSION);
#elif defined(__VTCMD__) && defined(__VT52__)
	sprintf(buf, "VI for CP/M-86 %s (vt52 mode)", GIT_VERSION);
#elif defined(__VTCMD__) && defined(__VT100__)
	sprintf(buf, "VI for CP/M-86 %s (vt100 mode)", GIT_VERSION);
#else
	sprintf(buf, "VI for CP/M-86 %s (unknown mode)", GIT_VERSION);
#endif
#elif defined(__PCDOS__) && __PCDOS__==11
#if defined(__PCBIOS__)
	sprintf(buf, "VI for PC-DOS 1.1 %s (bios mode)", GIT_VERSION);
#else
	sprintf(buf, "VI for PC-DOS 1.1 %s (unknown mode)", GIT_VERSION);
#endif
#elif defined(__PCDOS__) && __PCDOS__==20
#if defined(__PCBIOS__)
	sprintf(buf, "VI for PC-DOS 2.0 %s (bios mode)", GIT_VERSION);
#else
	sprintf(buf, "VI for PC-DOS 2.0 %s (unknown mode)", GIT_VERSION);
#endif
#else
	sprintf(buf, "VI version %s (unknown mode)", GIT_VERSION);
#endif
	return buf;
}

/* Usage message shown when no filename was given; wording depends on the
 * OS's path/drive syntax. Lives here (not main.c) to keep main.c OS-agnostic. */
windusage()
{
#if defined(__CPM86__)
	fprintf(stderr,"Usage: vi [-xodb] [user/][drive:]file\n");
#else
	fprintf(stderr,"Usage: vi [-xodb] [drive:]file\n");
#endif
}

/* ------------------------------------------------------------------ */
/* VT52/VT100 terminal escape-code implementation                      */
/* ------------------------------------------------------------------ */
#if defined(__VTCMD__ )

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
#elif defined(__VT100__)
	printf("\033[%d;%dH",r+1,c+1);
#endif
}

windexit(r)
int r;
{
    windclear();
    windgoto(0,0);
    windrefresh();
	printf("Bye ...\n");
	exit(r);
}

windclreol()
{
#if defined(__VT52__)
	printf("\033K");
#elif defined(__VT100__)
	printf("\033[K");
#endif
}

windcursor(on)
int on;
{
#if defined(__VT52__)
	/* ESC f = cursor off, ESC e = cursor on (CP/M-86 >= 2.2) */
	printf(on ? "\033e" : "\033f");
#elif defined(__VT100__)
	printf(on ? "\033[?25h" : "\033[?25l");
#endif
}

windcolor(fg)
int fg;
{
#if defined(__VT52__)
	/* ESC b <c> sets foreground colour (CGA: 2=green) */
	printf("\033b%c", (char)fg);
#elif defined(__VT100__)
	/* ANSI SGR: 30+fg for foreground (0=black,1=red,2=green,...) */
	printf("\033[3%dm", fg);
#endif
}

windcolorreset()
{
#if defined(__VT52__)
	/* Restore default foreground colour (white=7) */
	printf("\033b\007");
#elif defined(__VT100__)
	printf("\033[0m");
#endif
}

windclear()
{
#if defined(__VT52__)
	printf("\033E");
#elif defined(__VT100__)
	printf("\033[2J\033[H");
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

#endif /* __VTCMD__ */

/* ------------------------------------------------------------------ */
/* MS-DOS implementation (PC BIOS INT 10h, no ANSI.SYS required)       */
/* ------------------------------------------------------------------ */
#if defined(__PCBIOS__)

static int curattr = 7;	/* current text attribute (white on black) */
static int wp_row, wp_col;	/* scratch cursor position for windclreol */
static int wp_count;
static int clearbottom;		/* Rows-1, for windclear()'s scroll region */
static int cur_row, cur_col;	/* our own idea of where the cursor is */

windinit()
{
#if defined(__CPM86__)
	struct sgttyb stty;

	/* Same raw/no-echo console mode as the VTCMD build: without this,
	 * BDOS's own console driver stays in line-buffered/cooked mode and
	 * fights with our direct BIOS reads and writes over the cursor. */
	stty.sg_flags = CRMOD|CBREAK;
	ioctl(0, TIOCSETP, &stty);
#endif
	/* No video mode or page select here: querying/forcing the mode
	 * (AH=0Fh/AH=0) hung or exited immediately on CGA/MDA adapters.
	 * CP/M-86 and DOS both already leave the display in a valid 80x25
	 * text mode (mono on MDA, colour on CGA/EGA/VGA) before we start. */
	Columns=80;
	/* Match the 24-line convention of the vivt52/vivt100 CP/M-86 builds;
	 * plain DOS gets the full 25-line BIOS text mode. */
#if defined(__CPM86__)
	Rows=24;
#else
	Rows=25;
#endif
	/* Force a known cursor position right away; don't rely on CP/M-86's
	 * console (or the display page it may have left active) to have
	 * left the BIOS cursor anywhere sane for us. */
	windgoto(0,0);
}

windgoto(r,c)
int r,c;
{
	int dummy;	/* forces a bp frame so [bp+N] addresses the args */

	cur_row = r;
	cur_col = c;
	/* AH=2: set cursor position, BH=page, DH=row, DL=column */
#asm
    push ax
    push cx
    push dx
    push bx
    push sp     ; Pushes the original SP value (before AX was pushed)
    push bp
    push si
    push di
	mov dh, byte ptr [bp+4]
	mov dl, byte ptr [bp+6]
	mov bh, 0
	mov ah, 2
	int 10h
	pop di
    pop si
    pop bp
    add sp, 2   ; Discards the saved SP value (replaces POP SP)
    pop bx
    pop dx
    pop cx
    pop ax
#endasm
}

/* Re-issue our last known cursor position, without changing it. Used by
 * getch() to fight the background clock/status update at high frequency
 * while polling for a keystroke, instead of trusting a single BIOS call
 * to survive an arbitrarily long wait. */
windrefreshcursor()
{
	windgoto(cur_row,cur_col);
}

windexit(r)
int r;
{
    windclear();
    windgoto(0,0);
    windrefresh();
	printf("Bye ...\n");
#if defined(__PCBIOS__) && defined(__CPM86__)
	printf("\033E\033Y%c%cBye...\n",0x20,0x20);
#asm
	mov  dl, 0Dh    ; CR
	mov  cl, 2      ; C_WRITE
	int  0E0h
#endasm
#endif
	exit(r);
}

windclreol()
{
	/* Use our own tracked position rather than querying the BIOS: a
	 * background CP/M-86 update could have moved the real cursor. */
	wp_row = cur_row;
	wp_col = cur_col;
	for ( wp_count = Columns - wp_col; wp_count > 0; wp_count-- )
		windputc(' ');
	/* windputc() leaves the cursor after the last blank; restore it to
	 * where clreol was actually called from. */
	windgoto(wp_row,wp_col);
}

windcursor(on)
int on;
{
	int dummy;	/* forces a bp frame so [bp+N] addresses the arg */

	/* AH=1: set cursor shape; a start-scanline past the end hides it */
#asm
    push ax
    push cx
    push dx
    push bx
    push sp     ; Pushes the original SP value (before AX was pushed)
    push bp
    push si
    push di
	mov ax, [bp+4]
	cmp ax, 0
	je windcursor_hide
	mov cx, 0607h
	jmp windcursor_done
windcursor_hide:
	mov cx, 2000h
windcursor_done:
	mov ah, 1
	int 10h
	pop di
    pop si
    pop bp
    add sp, 2   ; Discards the saved SP value (replaces POP SP)
    pop bx
    pop dx
    pop cx
    pop ax
#endasm
}

windcolor(fg)
int fg;
{
	curattr = fg & 0x0f;
}

windcolorreset()
{
	curattr = 7;
}

windclear()
{
	clearbottom = Rows - 1;
	/* AH=6: scroll up window. AL=0 ("clear") is a documented shortcut
	 * that some non-genuine BIOS clones don't implement correctly;
	 * AL=25 (>= window height) forces the real scroll path instead,
	 * which has the same visual effect (nothing left to scroll into
	 * view) but is far more widely compatible. */
#asm
    push ax
    push cx
    push dx
    push bx
    push sp     ; Pushes the original SP value (before AX was pushed)
    push bp
    push si
    push di
	mov ax, 0600h
	mov bh, 7
	mov cx, 0
	mov dh, byte ptr clearbottom_
	mov dl, 79
	int 10h
	mov ax, 0200h
	mov bh, 0
	mov dx, 0
	int 10h
	pop di
    pop si
    pop bp
    add sp, 2   ; Discards the saved SP value (replaces POP SP)
    pop bx
    pop dx
    pop cx
    pop ax
#endasm
}

windputc(c)
int c;
{
	int dummy;	/* forces a bp frame so [bp+N] addresses the arg */

	/* Re-assert our own tracked position before writing: CP/M-86 runs a
	 * background clock/status update on its own that can silently move
	 * the BIOS cursor while we're blocked waiting for a keystroke, so we
	 * can't trust "wherever the cursor already is" to still be ours.
	 * AH=2 sets it, then AH=0eh writes the char and auto-advances. */
#asm
    push ax
    push cx
    push dx
    push bx
    push sp     ; Pushes the original SP value (before AX was pushed)
    push bp
    push si
    push di
	mov dh, byte ptr cur_row_
	mov dl, byte ptr cur_col_
	mov bh, 0
	mov ah, 2
	int 10h

	mov al, byte ptr [bp+4]
	mov bh, 0
	mov ah, 0eh
	int 10h
	pop di
    pop si
    pop bp
    add sp, 2   ; Discards the saved SP value (replaces POP SP)
    pop bx
    pop dx
    pop cx
    pop ax
#endasm
	cur_col++;
	if ( cur_col >= Columns ) {
		cur_col = 0;
		cur_row++;
	}
}

windstr(s)
char *s;
{
	while ( *s )
		windputc(*s++);
}

windrefresh()
{
	/* Need a redraw here? */
}

beep()
{
	putchar('\007');
}

#endif /* __PCBIOS__ */

