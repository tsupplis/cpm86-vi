/*
 * Minimal, standalone diagnostic for the __PCBIOS__ window.c routines
 * under CP/M-86 (linked as a .cmd, run under PCE or the cpm86 emulator).
 * Not part of the real vi build -- isolates windgoto/windputc from all
 * of vi's own screen/timing logic, to check whether raw BIOS cursor
 * positioning is reliable by itself.
 */

#include "stevie.h"
#include "stdio.h"

int Rows, Columns;

/* Minimal standalone key-wait, so we don't have to drag in all of
 * edit.c (and its many external globals) just for getch(). Polls
 * instead of blocking in INT 16h, re-asserting the cursor position
 * every time round -- same fix as edit.c's getch(). */
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

waitkey()
{
	while ( !keyready() )
		windrefreshcursor();
#asm
	mov ah, 0
	int 16h
#endasm
}

main()
{
	int i;

	windinit();

	/* 1: corners */
	windgoto(0,0);   windputc('A');
	windgoto(0,79);  windputc('B');
	windgoto(23,0);  windputc('C');
	windgoto(23,79); windputc('D');

	/* 2: a horizontal run, to check auto-advance/re-assert in sequence */
	windgoto(5,10);
	for ( i=0; i<10; i++ )
		windputc('0'+i);

	/* 3: repeated goto+putc to the SAME spot, to catch drift */
	for ( i=0; i<5; i++ ) {
		windgoto(10,20);
		windputc('X');
	}

	/* 4: wait for a keypress so the screen stays up for inspection */
	windgoto(12,0);
	windstr("Press any key...");
	waitkey();

	windexit(0);
}
