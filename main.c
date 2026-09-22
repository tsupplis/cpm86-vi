/*
 * STEVIE - ST Editor for VI Enthusiasts   ...Tim Thompson...twitch!tjt...
 */

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stevie.h"

static void filetonext(void);
static void nexttoscreen(void);
static void filealloc(void);
static void screenalloc(void);

int vi_rows;    /* Number of Rows and Columns */
int vi_columns; /* in the current window. */

char *vi_real_scr; /* What's currently on the screen, a single */
                  /* array of size Rows*Columns. */
char *vi_next_scr; /* What's to be put on the screen. */

char *vi_file_name = NULL; /* Current file name */

char *vi_file_mem; /* The contents of the file, as a single array. */

char *vi_file_max; /* Pointer to the end of allocated space for */
               /* Filemem. (It points to the first byte AFTER */
               /* the allocated space.) */

char *vi_file_end; /* Pointer to the end of the file in Filemem. */
               /* (It points to the byte AFTER the last byte.) */

char *vi_top_char; /* Pointer to the byte in Filemem which is */
               /* in the upper left corner of the screen. */

char *vi_bot_char; /* Pointer to the byte in Filemem which is */
               /* just off the bottom of the screen. */

char *vi_curs_char; /* Pointer to byte in Filemem at which the */
                /* cursor is currently placed. */

int vi_curs_row, vi_curs_col; /* Current position of cursor */

int vi_curs_vcol; /* Current virtual column, the column number of */
              /* the file's actual line, as opposed to the */
              /* column number we're at on the screen.  This */
              /* makes a difference on lines that span more */
              /* than one screen line. */

int vi_state = NORMAL; /* This is the current state of the command */
                    /* interpreter. */

int vi_renum = 0; /* The (optional) number before a command. */

char *vi_ins_start; /* This is where the latest insert/append */
                /* mode started. */

int vi_changed = 0; /* Set to 1 if something in the file has been */
                 /* changed and not written out. */

int vi_undo_changed = 0; /* Modified state before the current undoable change. */

int vi_debug = 0;

int vi_binary = 0; /* Set to 1 if the file should be read and written */
                /* in binary mode (no cr-lf translation). */

char vi_redo_buff[1024]; /* Each command should stuff characters into this */
                     /* buffer that will re-execute itself. */

char vi_undo_buff[1024]; /* Each command should stuff characters into this */
                     /* buffer that will undo its effects. */

char vi_ins_buff[1024]; /* Each insertion gets stuffed into this buffer. */

char *vi_uncurs_char = NULL; /* Curschar is restored to this before undoing. */

int vi_ninsert = 0;    /* Number of characters in the current insertion. */
int vi_undel_chars = 0; /* Number of characters to delete, when undoing. */
char *vi_ins_ptr = NULL;

char vi_repl_buf[1024]; /* Original chars saved during Replace mode. */
int vi_unrpl_chars = 0; /* Number of chars to restore on undo. */

int main(int argc, char **argv)
{
    int mode = 16;

    while (argc > 1 && argv[1][0] == '-') {
        switch (argv[1][1]) {
        case 'x':
            mode = 16;
            break;
        case 'o':
            mode = 8;
            break;
        case 'd':
            vi_debug = 1;
            break;
        case 'b':
            vi_binary = 1;
            break;
        }
        argc--;
        argv++;
    }

    if (argc <= 1) {
        windusage();
        exit(1);
    }

    vi_file_name = strsave(argv[1]);

    windinit();

    /* Make sure Rows/Columns are big enough */
    if (vi_rows < 3 || vi_columns < 16) {
        fprintf(stderr, "Rows=%d Columns=%d not big enough!\n", vi_rows, vi_columns);
        windexit(0);
    }

    switch (mode) {
    case 8:
        octchars();
        break;
    case 16:
        hexchars();
        break;
    }

    screenalloc();
    filealloc();

    screenclear();

    vi_file_end = vi_file_mem;
    if (readfile(vi_file_name, vi_file_end, 0))
        filemess("[New File]");
    vi_top_char = vi_curs_char = vi_file_mem;

    updatescreen();
    edit();
    windexit(0);
    return 0;
}

/*
 * filetonext()
 *
 * Based on the current value of Topchar, transfer a screenfull of
 * stuff from Filemem to Nextscreen, and update Botchar.
 */

static void filetonext(void) {
    int row, col;
    char *screenp = vi_next_scr;
    char *memp = vi_top_char;
    char *lastmemp = vi_top_char;
    char *endscreen;
    char *nextrow;
    char extra[16];
    int nextra = 0;
    int c;
    int n;

    /* The number of rows shown is Rows-1. */
    /* The last line is the status/command line. */
    endscreen = &screenp[(vi_rows - 1) * vi_columns];

    row = col = 0;
    while (screenp < endscreen && memp < vi_file_end) {

        /* Get the next character to put on the screen. */

        /* The 'extra' array contains the extra stuff that is */
        /* inserted to represent special characters (tabs, and */
        /* other non-printable stuff.  The order in the 'extra' */
        /* array is reversed. */

        if (nextra > 0)
            c = extra[--nextra];
        else {
            lastmemp = memp;
            c = (unsigned)(0xff & (*memp++));
            /* when getting a character from the file, we */
            /* may have to turn it into something else on */
            /* the way to putting it into 'Nextscreen'. */
            if (c == '\t') {
                strcpy(extra, "        ");
                /* tab amount depends on current column */
                nextra = (7 - col % 8);
                c = ' ';
            } else if ((n = chars[c].ch_size) > 1) {
                char *p;
                nextra = 0;
                p = chars[c].ch_str;
                /* copy 'ch-str'ing into 'extra' in reverse */
                while (n > 1)
                    extra[nextra++] = p[--n];
                c = p[0];
            }
        }

        if (c == '\n') {
            row++;
            /* get pointer to start of next row */
            nextrow = &vi_next_scr[row * vi_columns];
            /* blank out the rest of this row */
            while (screenp != nextrow)
                *screenp++ = ' ';
            col = 0;
            continue;
        }
        /* store the character in Nextscreen */
        if (col >= vi_columns) {
            row++;
            col = 0;
        }
        *screenp++ = c;
        col++;
    }
    /* If we stopped before finishing the current file character,
     * Botchar is where that character began, else memp. */
    if (screenp >= endscreen && nextra > 0)
        vi_bot_char = lastmemp;
    else
        vi_bot_char = memp;

    /* make sure the rest of the screen is blank */
    while (screenp < endscreen)
        *screenp++ = ' ';
    /* put '~'s on rows that aren't part of the file. */
    if (col != 0)
        row++;
    else if (vi_file_end == vi_file_mem && vi_state == INSERT)
        row = 1;
    while (row < vi_rows - 1) {
        vi_next_scr[row * vi_columns] = '~';
        row++;
    }
}

/*
 * nexttoscreen
 *
 * Transfer the contents of Nextscreen to the screen, using Realscreen
 * to avoid unnecessary output.
 */

static void nexttoscreen(void) {
    char *np = vi_next_scr;
    char *rp = vi_real_scr;
    char *endscreen;
    char nc;
    int row = 0, col = 0;
    int gorow = -1, gocol = -1;

    endscreen = &np[(vi_rows - 1) * vi_columns];

    for (; np < endscreen; np++, rp++) {
        /* If desired screen (contents of Nextscreen) does not */
        /* match what's really there, put it there. */
        if ((nc = (*np)) != (*rp)) {
            *rp = nc;
            /* if we are positioned at the right place, */
            /* we don't have to use windgoto(). */
            if (!(gorow == row && gocol == col))
                windgoto(gorow = row, gocol = col);
            if (nc == '~' && col == 0) {
                windcolor(2);
                windputc(nc);
                windcolorreset();
            } else {
                windputc(nc);
            }
            gocol++;
        }
        if (++col >= vi_columns) {
            col = 0;
            row++;
        }
    }
    windrefresh();
}

void updatescreen(void) {
    filetonext();
    nexttoscreen();
}

void screenclear(void) {
    int n;

    windclear();
    /* blank out the stored screens */
    for (n = vi_rows * vi_columns - 1; n >= 0; n--) {
        vi_real_scr[n] = ' ';
        vi_next_scr[n] = ' ';
    }
}

static void filealloc(void) {
    if ((vi_file_mem = malloc((unsigned)FILELENG)) == NULL) {
        fprintf(stderr, "Unable to allocate %d bytes for file memory!\n",
                FILELENG);
        exit(1);
    }
    vi_file_max = vi_file_mem + FILELENG;
}

static void screenalloc(void) {
    vi_real_scr = malloc((unsigned)(vi_rows * vi_columns));
    vi_next_scr = malloc((unsigned)(vi_rows * vi_columns));
}

int readfile(char *fname, char *fromp, int nochangename) /* if 1, don't change the Filename */
{
    FILE *f;
    char buff[128];
    char *p;
    int c, n;
    int unprint = 0;

    sprintf(buff, "Reading %s...", fname);
    message(buff);

    if (!nochangename)
        vi_file_name = strsave(fname);

    if ((f = fopen(fname, "r")) == NULL) {
        vi_file_end = vi_file_mem;
        return (1);
    }

    /* Read file into buffer until EOF or CP/M SUB char */
    for (n = 0; (c = getc(f)) != EOF && c != 0x1A; n++) {
        /* Skip CR; lines are terminated by LF alone internally */
        if (!vi_binary && c == '\r') {
            n--;
            continue;
        }
        if (!(isprint(c) || isspace(c)))
            unprint++;
        if (fromp >= vi_file_max) {
            fprintf(stderr, "File too long (limit is %d)!\n", FILELENG);
            exit(1);
        }
        /* Insert the char at the current point by shifting
        /* everything down. */
        for (p = vi_file_end; p > fromp; p--)
            *p = *(p - 1);
        *fromp++ = c;
        if (vi_file_end < fromp)
            vi_file_end = fromp;
    }
    if (!vi_binary && unprint > 0) {
        sprintf(
            buff,
            "%d unprintable chars!  Perhaps binary mode (-b) should be used?",
            unprint);
        message(buff);
        /* sleep(2); */
    }
    if (unprint > 0)
        p = "\"%s\" %d characters (%d un-printable)  (Press 'H' for help)";
    else
        p = "\"%s\" %d characters  (Press 'H' for help)";
    sprintf(buff, p, fname, n, unprint);
    message(buff);
    fclose(f);
    return (0);
}

static char getcbuff[1024];
static char *getcnext = NULL;

void stuffin(char *s)
{
    if (getcnext == NULL) {
        strcpy(getcbuff, s);
        getcnext = getcbuff;
    } else
        strcat(getcbuff, s);
}

void addtobuff(char *s, int c1, int c2, int c3, int c4, int c5, int c6)
{
    char *p = s;
    if ((*p++ = c1) == '\0')
        return;
    if ((*p++ = c2) == '\0')
        return;
    if ((*p++ = c3) == '\0')
        return;
    if ((*p++ = c4) == '\0')
        return;
    if ((*p++ = c5) == '\0')
        return;
    if ((*p++ = c6) == '\0')
        return;
}

int vgetc(void) {
    if (getcnext != NULL) {
        int nextc = *getcnext++;
        if (*getcnext == '\0') {
            *getcbuff = '\0';
            getcnext = NULL;
        }
        return (nextc);
    }
    return (windgetc());
}

int vpeekc(void) {
    if (getcnext != NULL)
        return (*getcnext);
    return (-1);
}

/*
 * anyinput
 *
 * Return non-zero if input is pending.
 */

int anyinput(void) {
    if (getcnext != NULL)
        return (1);
    return (0);
}
