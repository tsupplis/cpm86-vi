/*
 * STevie - ST editor for VI enthusiasts.     ...Tim Thompson...twitch!tjt...
 */

#include <ctype.h>
#include <stdio.h>
#include "stevie.h"
#include "keyboard.h"

static void donormal(int c);
static void insertchar(int c);
static int gethexchar(void);

/* ------------------------------------------------------------------ */
/* Raw keyboard input                                                  */
/* ------------------------------------------------------------------ */
#if defined(__PCBIOS__)

/* One pending byte, for the second half of a synthesized ESC sequence. */
static int pending = -1;

/* INT 16h AH=0: wait for a keystroke, return AH=scan code, AL=ASCII in AX. */
static int bioskey(void) {
#include "bioskey.asm"
}

/* INT 16h AH=1: non-zero if a keystroke is waiting (doesn't consume it). */
static int keyready(void) {
#include "keyready.asm"
}

static int getch(void) {
    int c, al, ah;

    if (pending >= 0) {
        c = pending;
        pending = -1;
        return c;
    }
    for (;;) {
        /* Don't block in INT 16h: CP/M-86's background clock/status
         * update can reposition the BIOS cursor while we're blocked,
         * with no chance for us to correct it until a key arrives.
         * Poll instead, re-asserting our cursor position every time
         * around, so any interference is fought at high frequency
         * instead of just once, best-effort, after the fact. */
        while (!keyready())
            windrefreshcursor();
        c = bioskey();
        al = c & 0xff;
        ah = (c >> 8) & 0xff;
        if (al != 0)
            return al;
        /* Extended key: no ASCII, decode the BIOS scan code in AH. */
        switch (ah) {
        case 0x48:
            pending = 'A';
            return 27; /* Up */
        case 0x50:
            pending = 'B';
            return 27; /* Down */
        case 0x4D:
            pending = 'C';
            return 27; /* Right */
        case 0x4B:
            pending = 'D';
            return 27; /* Left */
        case 0x47:
            pending = 'H';
            return 27; /* Home */
        case 0x49:
            pending = 'I';
            return 27; /* Page Up */
        case 0x51:
            return '\n'; /* Page Down */
        case 0x4F:
            return '\032'; /* End */
        case 0x52:
            pending = 'L';
            return 27; /* Insert */
        case 0x53:
            return '\177'; /* Delete */
        }
    }
}

#elif defined(__VTCMD__)

#define GETCH_BUFLEN 64
static char getch_buffer[GETCH_BUFLEN];

static int getch(void) {
    int i, c, d;
    static int s = 0;
    static int o = 0;

    if (s > 0) {
        c = (unsigned char)getch_buffer[o];
        s--;
        o++;
        o = o % GETCH_BUFLEN;
        return c;
    }
    while (!(c = bdos(6, 0xFF)))
        continue;
    while (s < GETCH_BUFLEN && (d = bdos(6, 0xFF))) {
        if (1) {
            getch_buffer[(o + s) % GETCH_BUFLEN] = d;
            s++;
        }
    }
    return c;
}

#endif /* __PCBIOS__ / __VTCMD__ */

/* OS-independent wrapper around whichever getch() is active above. */
int windgetc(void) {
    if (vi_key_concurrent()) return vi_key_read();
    return getch();
}

void edit(void) {
    int c, c1, c2;
    char *p, *q;
    /* Buffer to save original chars overwritten in Replace mode,
     * so backspace can restore them. */
    static char replbuf[1024];
    static char *replptr = NULL;

    vi_renum = 0;

    /* position the display and the cursor at the top of the file. */
    vi_top_char = vi_file_mem;
    vi_curs_char = vi_file_mem;
    vi_curs_row = vi_curs_col = 0;

    if (vi_state == INSERT)
        message("Insert");
    else
        message("");

    {
        int laststate = -1; /* forces the mode message on the first pass */
        for (;;) {
            /* Figure out where the cursor is based on Curschar. */
            cursupdate();
            /* Only (re)announce the mode when it actually changes, so a
             * command's own message (e.g. "File not written out...") isn't
             * immediately clobbered on the very next loop iteration. */
            if (vi_state != laststate) {
                if (vi_state == INSERT)
                    message("Insert Mode");
                else if (vi_state == REPLACE)
                    message("Replace Mode");
                else if (vi_state == NORMAL)
                    message("Normal Mode");
                laststate = vi_state;
            }
            /* printf("Curschar=(%d,%d) row/col=(%d,%d)",
                Curschar,*Curschar,Cursrow,Curscol); */
            windgoto(vi_curs_row, vi_curs_col);
            windrefresh();
            c = vgetc();
            switch (vi_state) {
            case NORMAL:
                /* We're in the normal (non-insert) mode. */
                if (c == 27) {
                    /* VT52 and the DOS BIOS key mapping both send a lone ESC
                     * followed directly by a letter; VT100/ANSI sends ESC '['.
                     */
#if defined(__VT52__) || defined(__PCBIOS__)
                    vi_state = NORMAL_ESCAPE;
#elif defined(__VT100__)
                    vi_state = BRACKET_ESCAPE;
#endif
                    break;
                }
#if defined(__CPM86__)
                if (c == 0x11) {
                    vi_state = NORMAL_11;
                    break;
                }
#endif
                /* End and Page-Down arrive as bare bytes, with no ESC prefix */
                if (c == '\032') { /* End key -> end of line */
                    vi_renum = 0;
                    normal('$');
                    break;
                }
                if (c == '\n') { /* Page-Down key -> forward 1 screen */
                    vi_renum = 0;
                    normal(06);
                    break;
                }
#if defined(__CPM86__)
                switch (c) {
                case 0x13:
                    c = 'h';
                    break;
                case 0x04:
                    c = 'l';
                    break;
                case 0x05:
                    c = 'k';
                    break;
                case 0x18:
                    c = 'j';
                    break;
                case 0x03:
                    c = 06;
                    break;
                case 0x12:
                    c = 02;
                    break;

                default:
                    break;
                }
#endif

                donormal(c);
                break;
#if defined(__CPM86__)
            case NORMAL_11:
                /* Handle the special case for CPM86 when c==0x11 */
                switch (c) {
                case 'E':
                    donormal('0');
                    break;
                case 'X':
                    donormal('$');
                    break;
                default:
                    break;
                }
                vi_state = NORMAL;
                break;
#endif
            case BRACKET_ESCAPE:
                /* A lone ESC (not followed by '[') is just the usual */
                /* harmless "make sure we're in Normal mode" keystroke; */
                /* the character that follows must still be executed. */
                if (c == '[') {
                    vi_state = NORMAL_ESCAPE;
                    vi_renum = 0;
                    break;
                }
                vi_state = NORMAL;
                if (c == 27)
                    vi_state = BRACKET_ESCAPE;
                else
                    donormal(c);
                break;
            case NORMAL_ESCAPE: {
                int d = 0;
                switch (c) {
                case 'A':
                    d = 'k';
                    break;
                case 'B':
                    d = 'j';
                    break;
                case 'C':
                    d = 'l';
                    break;
                case 'D':
                    d = 'h';
                    break;
                case 'H': /* Home key -> beginning of line */
                    d = '0';
                    break;
                case 'I': /* Page Up key -> back 1 screen */
                    d = 02;
                    break;
                }
                vi_state = NORMAL;
                if (d) {
                    vi_renum = 0;
                    normal(d);
                }
                /* Same as above: don't drop a keystroke that turns */
                /* out not to be part of an escape sequence. */
                else if (c == 27) {
#if defined(__VT52__) || defined(__PCBIOS__)
                    vi_state = NORMAL_ESCAPE;
#elif defined(__VT100__)
                    vi_state = BRACKET_ESCAPE;
#endif
                } else
                    donormal(c);
            } break;
            case INSERT:
                /* We're in insert mode. */
                switch (c) {
                case '\033': /* an ESCape ends input mode */

                    /* If we're past the end of the file, (which should */
                    /* only happen when we're editing a new file or a */
                    /* file that doesn't have a newline at the end of */
                    /* the line), add a newline automatically. */
                    if (vi_curs_char >= vi_file_end) {
                        insertchar('\n');
                        vi_curs_char--;
                    }

                    /* Don't end up on a '\n' if you can help it. */
                    if (vi_curs_char > vi_file_mem && *vi_curs_char == '\n' &&
                        *(vi_curs_char - 1) != '\n') {
                        vi_curs_char--;
                    }
                    vi_state = NORMAL;
                    message("");
                    vi_uncurs_char = vi_ins_start;
                    vi_undel_chars = vi_ninsert;
                    /* Undobuff[0] = '\0'; */
                    /* construct the Redo buffer */
                    p = vi_redo_buff;
                    q = vi_ins_buff;
                    while (q < vi_ins_ptr)
                        *p++ = *q++;
                    *p++ = '\033';
                    *p = '\0';
                    updatescreen();
                    break;
                case '\b':
                    if (vi_curs_char <= vi_ins_start)
                        beep();
                    else {
                        char *target;
                        vi_curs_char--;
                        target = vi_curs_char;
                        delchar();
                        /* delchar() may back Curschar up further to avoid */
                        /* landing on a trailing newline (for Normal mode); */
                        /* Insert mode always wants it exactly at 'target'. */
                        vi_curs_char = target;
                        vi_ins_ptr--;
                        vi_ninsert--;
                        cursupdate();
                        updatescreen();
                    }
                    break;
                case '\030': /* control-x */
                {
                    int wasnewline = 0;
                    char *p1;
                    p1 = vi_curs_char;
                    if (*vi_curs_char == '\n')
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
                    vi_curs_char = p1;
                    delchar();
                    delchar();
                    delchar();
                    c = 16 * hextoint(c1) + hextoint(c2);
                    if (vi_debug)
                        printf("(c=%d)", c);
                    if (wasnewline)
                        vi_curs_char++;
                    inschar(c);
                    vi_ninsert++;
                    *vi_ins_ptr++ = c;
                    updatescreen();
                    break;
                }
                case 0x16: /* ^V — insert next character literally */
                    c = vgetc();
                    inschar(c);
                    vi_ninsert++;
                    *vi_ins_ptr++ = c;
                    updatescreen();
                    break;
                case 0x09: /* Tab — expand to spaces unless preceded by ^V */
                    insertchar(' ');
                    insertchar(' ');
                    insertchar(' ');
                    insertchar(' ');
                    break;
                case 0x0F:
                    break;
                case 0x0D: /* <CR> */
                case 0x0A: /* <CR> */
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
                if (replptr == NULL)
                    replptr = replbuf;
                switch (c) {
                case '\033': /* ESC exits replace mode */
                    /* Don't end up on a '\n' */
                    if (vi_curs_char > vi_file_mem && *vi_curs_char == '\n' &&
                        *(vi_curs_char - 1) != '\n')
                        vi_curs_char--;
                    vi_state = NORMAL;
                    /* Save originals for undo */
                    vi_unrpl_chars = (int)(replptr - replbuf);
                    if (vi_unrpl_chars > 0) {
                        char *s = replbuf, *d = vi_repl_buf;
                        int k = vi_unrpl_chars;
                        while (k-- > 0)
                            *d++ = *s++;
                        vi_undo_changed = vi_changed;
                    }
                    replptr = NULL;
                    updatescreen();
                    break;
                case '\b': /* backspace: restore original char */
                    if (replptr > replbuf) {
                        replptr--;
                        vi_curs_char--;
                        *vi_curs_char = *replptr;
                        CHANGED;
                        cursupdate();
                        updatescreen();
                    } else {
                        beep();
                    }
                    break;
                default:
                    if (isprint(c) || c == '\t') {
                        /* Save original char before overwriting */
                        if (replptr < replbuf + sizeof(replbuf) - 1) {
                            /* If at end of file or newline, insert instead */
                            if (vi_curs_char >= vi_file_end || *vi_curs_char == '\n') {
                                inschar(c);
                            } else {
                                *replptr++ = *vi_curs_char;
                                *vi_curs_char = c;
                                CHANGED;
                                if (vi_curs_char + 1 < vi_file_end)
                                    vi_curs_char++;
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
static void donormal(int c)
{
    if ((vi_renum > 0 && isdigit(c)) || (isdigit(c) && c != '0')) {
        vi_renum = vi_renum * 10 + (c - '0');
        return;
    }
    /* Forget the last message: a command that repeats the same warning
     * (e.g. "Pattern not found" on two failed searches in a row) must
     * still show it, not have it silently suppressed as unchanged. */
    clearlastmess();
    normal(c);
    vi_renum = 0;
}

static void insertchar(int c)
{
    char *p;

    if (!anyinput()) {
        inschar(c);
        *vi_ins_ptr++ = c;
        vi_ninsert++;
    } else {
        /* If there's any pending input, grab */
        /* it all at once. */
        p = vi_ins_ptr;
        *vi_ins_ptr++ = c;
        vi_ninsert++;
        while ((c = vpeekc()) != '\033') {
            c = vgetc();
            *vi_ins_ptr++ = c;
            vi_ninsert++;
        }
        *vi_ins_ptr = '\0';
        insstr(p);
    }
    updatescreen();
}

static int gethexchar(void) {
    int c;

    for (;;) {
        windgoto(vi_curs_row, vi_curs_col);
        windrefresh();
        c = vgetc();
        if (hextoint(c) >= 0)
            break;
        clearlastmess();
        message("Expecting a hexidecimal character (0-9 or a-f)");
        beep();
        /* sleep(1); */
    }
    return (c);
}

void getout(void) {
    windgoto(vi_rows - 1, 0);
    windrefresh();
    putchar('\r');
    putchar('\n');
    windexit(0);
}

/* Use the renderer's delayed wrap: a full row does not consume another
 * row until the next display cell, and its newline must not wrap twice. */
static void cursor_position(void)
{
    char *p;
    int c, n;

    vi_curs_row = vi_curs_col = vi_curs_vcol = 0;
    for (p = vi_top_char; p < vi_curs_char; p++) {
        c = (unsigned char)*p;
        if (c == '\n') {
            vi_curs_row++;
            vi_curs_col = 0;
        } else {
            n = chars[c].ch_size;
            while (n-- > 0) {
                if (vi_curs_col == vi_columns) {
                    vi_curs_row++;
                    vi_curs_col = 0;
                }
                vi_curs_col++;
            }
        }
    }
    if (vi_curs_col == vi_columns) {
        if (vi_curs_char < vi_file_end && *vi_curs_char == '\n')
            vi_curs_col--;      /* EOL after an exactly full row */
        else {
            vi_curs_row++;
            vi_curs_col = 0;
        }
    }
    /* The desired column belongs to the logical line, even when its first
     * screen row has scrolled off the top. Match the displayed char widths. */
    p = vi_curs_char;
    while (p > vi_file_mem && p[-1] != '\n') p--;
    while (p < vi_curs_char)
        vi_curs_vcol += chars[(unsigned char)*p++].ch_size;
}

/* Advance one visible text row, keeping expanded characters intact when
 * one straddles the boundary. This also works for lines taller than a screen. */
static char *next_screen_row(char *p)
{
    char *start = p;
    int col = 0;
    int n;

    while (p < vi_file_end) {
        if (*p == '\n') return p + 1;
        n = chars[(unsigned char)*p].ch_size;
        if (col + n > vi_columns && p > start) return p;
        col += n;
        p++;
        if (col >= vi_columns) {
            if (p < vi_file_end && *p == '\n') p++;
            return p;
        }
    }
    return p;
}

void cursupdate(void)
{
    char *p;
    char *oldtop = vi_top_char;

    if (vi_file_end == vi_file_mem)
        vi_top_char = vi_curs_char = vi_file_mem;
    else if (vi_curs_char < vi_top_char) {
        /* Reveal the row containing the cursor at the top, just as moving
         * down reveals it at the bottom. Never recenter by half a screen. */
        p = vi_curs_char;
        while (p > vi_file_mem && p[-1] != '\n') p--;
        vi_top_char = p;
        while ((p = next_screen_row(vi_top_char)) > vi_top_char &&
               p <= vi_curs_char)
            vi_top_char = p;
    }
    cursor_position();
    while (vi_curs_row >= vi_rows - 1) {
        p = next_screen_row(vi_top_char);
        if (p <= vi_top_char || p > vi_curs_char) break;
        vi_top_char = p;
        cursor_position();
    }
    if (vi_top_char != oldtop) updatescreen();
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

int oneright(void) {
    char *p;

    p = vi_curs_char;
    if ((*p++) == '\n' || p >= vi_file_end || *p == '\n')
        return (0);
    vi_curs_char++;
    return (1);
}

int oneleft(void) {
    char *p;

    p = vi_curs_char;
    if (*p == '\n' || p == vi_file_mem || *(p - 1) == '\n')
        return (0);
    vi_curs_char--;
    return (1);
}

void beginline(void) {
    while (oneleft())
        ;
}

int oneup(int n) {
    char *p, *np;
    int savevcol, k;

    savevcol = vi_curs_vcol;
    p = vi_curs_char;
    for (k = 0; k < n; k++) {
        /* Look for the previous line */
        if ((np = prevline(p)) == NULL) {
            /* If we've at least backed up a little .. */
            if (k > 0)
                break; /* to update the cursor, etc. */
            else
                return (0);
        }
        p = np;
    }
    /* Both directions leave viewport adjustment to the common cursupdate
     * call, after the final desired column has been selected. */
    /* try to advance to the same (virtual) column */
    /* that we were at before. */
    vi_curs_char = coladvance(p, savevcol);
    return (1);
}

int onedown(int n) {
    char *p, *np;
    int k;

    p = vi_curs_char;
    for (k = 0; k < n; k++) {
        /* Look for the next line */
        if ((np = nextline(p)) == NULL) {
            if (k > 0)
                break;
            else
                return (0);
        }
        p = np;
    }
    /* try to advance to the same (virtual) column */
    /* that we were at before. */
    vi_curs_char = coladvance(p, vi_curs_vcol);
    return (1);
}
