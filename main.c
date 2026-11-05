/*
 * STEVIE - ST Editor for VI Enthusiasts   ...Tim Thompson...twitch!tjt...
 */

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stevie.h"
#include "save.h"
#include "keyboard.h"
#include "yankmem.h"

static void filetonext(void);
static void nexttoscreen(void);
static void filealloc(void);
static void screenalloc(void);
static void screenerror(void);

#ifdef VI_DOS1_COM
#define FILELENG 20480U
#else
#define FILELENG 38016U
#endif

int vi_rows;    /* Number of Rows and Columns */
int vi_columns; /* in the current window. */

static char screen_line[VI_SCREEN_MAX_COLUMNS];
static char screen_previous[VI_SCREEN_MAX_COLUMNS];

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

unsigned long vi_curs_row;
int vi_curs_col; /* Current position of cursor */

unsigned long vi_curs_vcol; /* Current virtual column, the column number of */
              /* the file's actual line, as opposed to the */
              /* column number we're at on the screen.  This */
              /* makes a difference on lines that span more */
              /* than one screen line. */

int vi_state = NORMAL; /* This is the current state of the command */
                    /* interpreter. */

unsigned long vi_renum = 0; /* VI_COUNT_MAX + 1 marks an overflowing prefix. */

char *vi_ins_start; /* This is where the latest insert/append */
                /* mode started. */

int vi_changed = 0; /* Set to 1 if something in the file has been */
                 /* changed and not written out. */

int vi_undo_changed = 0; /* Modified state before the current undoable change. */

int vi_debug = 0;

int vi_binary = 0; /* Set to 1 if the file should be read and written */
                /* in binary mode (no cr-lf translation). */

char vi_redo_buff[CMDSIZE]; /* Each command should stuff characters into this */
                     /* buffer that will re-execute itself. */

char vi_undo_buff[CMDSIZE]; /* Each command should stuff characters into this */
                     /* buffer that will undo its effects. */

char vi_ins_buff[CMDSIZE]; /* Each insertion gets stuffed into this buffer. */

char *vi_uncurs_char = NULL; /* Curschar is restored to this before undoing. */

int vi_ninsert = 0;    /* Number of characters in the current insertion. */
int vi_undel_chars = 0; /* Number of characters to delete, when undoing. */
char *vi_ins_ptr = NULL;

char vi_repl_buf[CMDSIZE]; /* Original chars saved during Replace mode. */
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
        vi_key_exit();
        exit(1);
    }

    if (!vi_yank_init()) {
        fputs("Unable to reserve external yank/screen memory!\n", stderr);
        return 1;
    }
    if (atexit(vi_yank_close) != 0) {
        vi_yank_close();
        fputs("Unable to register external memory cleanup!\n", stderr);
        return 1;
    }

#if defined(__CPM86__)
    /* On CP/M-86 the filename may be prefixed with a user-area number,
     * e.g. "4/B:FOO.TXT" or "4/FOO.TXT".  The C runtime's fopen() can
     * handle that prefix for a single open, but it does NOT permanently
     * change the current user area — so a later writeit() call on the
     * same string may land in the wrong area (typically user 0).  Parse
     * and strip the prefix here, issue one bdos(32,n) to set the user
     * area for the entire session, and keep only the bare name in
     * vi_file_name so every subsequent fopen() sees a clean path. */
    {
        char *p = argv[1];
        int  unum = 0;
        int  has_user = 0;
        while (*p >= '0' && *p <= '9') {
            unum = unum * 10 + (*p - '0');
            p++;
            has_user = 1;
        }
        if (has_user && *p == '/') {
            p++;            /* skip the '/' */
            bdos(32, unum); /* Set User Code for the session */
            argv[1] = p;    /* point past the user prefix     */
        }
    }
#endif

    windinit();

    /* Make sure Rows/Columns are big enough */
    if (vi_rows < 3 || vi_columns < 16) {
        fprintf(stderr, "Rows=%d Columns=%d not big enough!\n", vi_rows, vi_columns);
        windexit(0);
    }

    if (!vi_set_filename(argv[1])) {
        fputs("Unable to allocate initial filename!\n", stderr);
        vi_key_exit();
        return 1;
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
    if (readfile(vi_file_name, vi_file_end, 0) == 1)
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
    unsigned position = 0, endscreen;
    char *memp = vi_top_char;
    char *lastmemp = vi_top_char;
    char extra[16];
    int nextra = 0;
    int c;
    int n;

    /* The number of rows shown is Rows-1. */
    /* The last line is the status/command line. */
    endscreen = (vi_rows - 1) * vi_columns;

    row = col = 0;
    while (position < endscreen && (memp < vi_file_end || nextra > 0)) {

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
            if ((n = vi_char_width[c]) > 1) {
                const char *p;
                nextra = 0;
                p = vi_char_text((unsigned char)c);
                /* copy 'ch-str'ing into 'extra' in reverse */
                while (n > 1)
                    extra[nextra++] = p[--n];
                c = p[0];
            }
        }

        if (c == '\n') {
            if (col < vi_columns) {
                memset(screen_line + col, ' ', (unsigned)(vi_columns - col));
                if (!vi_screen_store(VI_SCREEN_NEXT, row, screen_line))
                    screenerror();
            }
            row++;
            position = row * vi_columns;
            col = 0;
            continue;
        }
        /* store the character in Nextscreen */
        if (col >= vi_columns) {
            row++;
            col = 0;
        }
        screen_line[col] = c;
        position++;
        col++;
        if (col == vi_columns &&
            !vi_screen_store(VI_SCREEN_NEXT, row, screen_line))
            screenerror();
    }
    /* If we stopped before finishing the current file character,
     * Botchar is where that character began, else memp. */
    if (position >= endscreen && nextra > 0)
        vi_bot_char = lastmemp;
    else
        vi_bot_char = memp;

    if (col != 0) {
        if (col < vi_columns) {
            memset(screen_line + col, ' ', (unsigned)(vi_columns - col));
            if (!vi_screen_store(VI_SCREEN_NEXT, row, screen_line))
                screenerror();
        }
        row++;
    } else if (vi_file_end == vi_file_mem && vi_state == INSERT) {
        memset(screen_line, ' ', (unsigned)vi_columns);
        if (!vi_screen_store(VI_SCREEN_NEXT, 0, screen_line))
            screenerror();
        row = 1;
    }
    memset(screen_line, ' ', (unsigned)vi_columns);
    screen_line[0] = '~';
    while (row < vi_rows - 1) {
        if (!vi_screen_store(VI_SCREEN_NEXT, row, screen_line))
            screenerror();
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
    char nc;
    int row, col, first, changed;
    int gorow = -1, gocol = -1;

    for (row = 0; row < vi_rows - 1; row++) {
        if (!vi_screen_load(VI_SCREEN_NEXT, row, screen_line) ||
            !vi_screen_load(VI_SCREEN_REAL, row, screen_previous))
            screenerror();
        changed = 0;
        for (col = 0; col < vi_columns; ) {
            if ((nc = screen_line[col]) != screen_previous[col]) {
                changed = 1;
                if (!(gorow == row && gocol == col))
                    windgoto(gorow = row, gocol = col);
                if (nc == '~' && col == 0) {
                    windcolor(2);
                    windputc(nc);
                    windcolorreset();
                    col++;
                } else if ((unsigned char)nc < ' ') {
                    windputc(nc);
                    col++;
                } else {
                    first = col;
                    do {
                        col++;
                    } while (col < vi_columns &&
                             screen_line[col] != screen_previous[col] &&
                             (unsigned char)screen_line[col] >= ' ');
                    windputrun(screen_line + first, (unsigned)(col - first));
                }
                gocol = col;
            } else
                col++;
        }
        if (changed && !vi_screen_store(VI_SCREEN_REAL, row, screen_line))
            screenerror();
    }
    windrefresh();
}

void updatescreen(void) {
    filetonext();
    windcursor(0);
    nexttoscreen();
    windgoto(vi_curs_row, vi_curs_col);
    windcursor(1);
    windrefresh();
}

void screenclear(void) {
    int row;

    windcursor(0);
    windclear();
    memset(screen_line, ' ', (unsigned)vi_columns);
    for (row = 0; row < vi_rows; row++) {
        if (!vi_screen_store(VI_SCREEN_REAL, row, screen_line) ||
            !vi_screen_store(VI_SCREEN_NEXT, row, screen_line))
            screenerror();
    }
    windgoto(vi_curs_row, vi_curs_col);
    windcursor(1);
    windrefresh();
}

static void filealloc(void) {
    if ((vi_file_mem = malloc((unsigned)FILELENG)) == NULL) {
        fprintf(stderr, "Unable to allocate %u bytes for file memory!\n",
                (unsigned)FILELENG);
        vi_key_exit();
        exit(1);
    }
    vi_file_max = vi_file_mem + FILELENG;
}

static void screenalloc(void) {
    if (!vi_screen_configure((unsigned)vi_rows, (unsigned)vi_columns))
        screenerror();
}

static void screenerror(void) {
    fputs("Unable to access external screen memory!\n", stderr);
    vi_key_exit();
    exit(1);
}

/* Return 1 for an open failure, -1 for a rolled-back read, or 0 on success. */
int readfile(char *fname, char *fromp, int nochangename) /* if 1, don't change the Filename */
{
    FILE *f;
    char buff[128];
    char *p, *insertp = fromp;
    const char *error = NULL;
    int c;
    unsigned n, used, space, unprint = 0;
    long remaining;

    snprintf(buff, sizeof buff, "Reading %s...", fname);
    message(buff);

    if (!nochangename) {
        if (!vi_set_filename(fname))
            return -1;
        fname = vi_file_name;
    }

    remaining=vi_binary ? vi_file_length(fname) : -1L;
    if ((f = fopen(fname, "r")) == NULL) {
        if (nochangename)
            message("Unable to open file for reading!");
        return (1);
    }

    /* Read file into buffer until EOF or CP/M SUB char */
    n = 0;
    do {
        used = 0;
        space = vi_byte_span(vi_file_end, vi_file_max);
        while (used < sizeof buff && remaining != 0L &&
               (c = getc(f)) != EOF && (vi_binary || c != 0x1A)) {
            if (remaining > 0L) remaining--;
            /* Skip CR; lines are terminated by LF alone internally. */
            if (!vi_binary && c == '\r')
                continue;
            if (used >= space) {
                error = "File too long; read cancelled!";
                break;
            }
            if (!(isprint(c) || isspace(c)))
                unprint++;
            buff[used++] = c;
        }
        if (error != NULL)
            break;
        if (used != 0) {
            /* Reuse the status buffer; move the tail once per filtered chunk. */
            memmove(fromp + used, fromp, vi_byte_span(fromp, vi_file_end));
            memcpy(fromp, buff, used);
            fromp += used;
            vi_file_end += used;
            n += used;
        }
    } while (used == sizeof buff);
    if (ferror(f))
        error = "Read/close failed; read cancelled!";
    if (fclose(f) == EOF)
        error = "Read/close failed; read cancelled!";
    if (error != NULL) {
        memmove(insertp, fromp, vi_byte_span(fromp, vi_file_end));
        vi_file_end -= n;
        message((char *)error);
        return -1;
    }
    if (!vi_binary && unprint > 0) {
        sprintf(
            buff,
            "%u unprintable chars!  Perhaps binary mode (-b) should be used?",
            unprint);
        message(buff);
        /* sleep(2); */
    }
    if (unprint > 0)
        p = "\"%s\" %u characters (%u un-printable)  (Press 'H' for help)";
    else
        p = "\"%s\" %u characters  (Press 'H' for help)";
    snprintf(buff, sizeof buff, p, fname, n, unprint);
    message(buff);
    return (0);
}

static char getcbuff[CMDSIZE];
static char *getcnext = NULL;
static int getc_stuffed;

int stuffin(char *s)
{
    unsigned pending = getcnext == NULL ? 0 : strlen(getcnext);
    unsigned length = strlen(s);

    if (length == 0)
        return 1;
    if (length > sizeof getcbuff - 1 - pending) {
        message("Replay buffer full; command rejected!");
        return 0;
    }
    if (pending)
        memmove(getcbuff, getcnext, pending);
    memcpy(getcbuff + pending, s, length + 1);
    getcnext = getcbuff;
    return 1;
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
        int nextc = (unsigned char)*getcnext++;
        getc_stuffed = 1;
        if (*getcnext == '\0') {
            *getcbuff = '\0';
            getcnext = NULL;
        }
        return (nextc);
    }
    getc_stuffed = 0;
    return (windgetc());
}

int vstuffed(void) {
    return getc_stuffed;
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
