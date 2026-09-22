/*
 * STevie - ST editor for VI enthusiasts.    ...Tim Thompson...twitch!tjt...
 */

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include "stevie.h"

static void appchar(int c);
static int canincrease(int n);

/*
 * opencmd
 *
 * Add a blank line below the current line.
 */

void opencmd(void) {
    /* get to the end of the current line */
    while (vi_curs_char < vi_file_end && (*vi_curs_char) != '\n')
        vi_curs_char++;
    /* Try to handle a file that doesn't end with a newline */
    if (vi_curs_char >= vi_file_end)
        vi_curs_char = vi_file_end - 1;
    /* Add the blank line */
    appchar('\n');
}

int issepchar(int c)
{
    if (strchr(WORDSEP, c) != NULL)
        return (1);
    return (0);
}

int cntlines(char *pbegin, char *pend)
{
    int lnum = 1;
    char *p;

    for (p = pbegin; p < pend;) {
        if (*p++ == '\n')
            lnum++;
    }
    return (lnum);
}

void fileinfo(void) {
    char buff[128];

    sprintf(buff, "\"%s\"%s line %d of %d", vi_file_name,
            vi_changed ? " [Modified]" : "", cntlines(vi_file_mem, vi_curs_char),
            cntlines(vi_file_mem, vi_file_end) - 1);
    message(buff);
}

void gotoline(int n)
{
    char *p;

    /* n==0 means "last line": use the same descent logic as the
     * numbered case, with the actual line count as the target. */
    if (n == 0)
        n = cntlines(vi_file_mem, vi_file_end) - 1;
    /* Start at the top of the file and go down 'n'-1 lines */
    vi_curs_char = vi_file_mem;
    while (--n > 0) {
        if ((p = nextline(vi_curs_char)) == NULL)
            break;
        vi_curs_char = p;
    }
    vi_top_char = vi_curs_char;
    for (n = 0; n < vi_rows / 2; n++) {
        if ((p = prevline(vi_top_char)) == NULL)
            break;
        vi_top_char = p;
    }
    updatescreen();
}

static char *savedline = NULL;
static int savednum = 0;
static int savedcount = 0;

/*
 * yankline
 *
 * Save a copy of the current line(s) for later 'p'lacing.
 */

void yankline(int n) {
    char *savep, *p, *q;
    int leng, k;

    if (savedline != NULL)
        free(savedline);
    savep = vi_curs_char;
    /* go to the beginning of the current line. */
    beginline();
    /* compute length of line */
    for (p = vi_curs_char, leng = 0;; p++) {
        if (*p == '\n') {
            /* keep going until we've seen 'n' lines */
            if (--n <= 0)
                break;
        }
        leng++;
    }
    /* save a copy of it */
    savedline = malloc((unsigned)(leng + 2));
    for (p = vi_curs_char, q = savedline, k = 0; k < leng; k++)
        *q++ = *p++;
    /* get the final newline */
    *q++ = *p;
    *q = '\0';
    vi_curs_char = savep;
    savednum = leng + 1;
    savedcount = (vi_renum == 0 ? 1 : vi_renum);
}

/*
 * putline
 *
 * If there is a currently saved line(s), 'p'ut it.
 * If k==1, 'P'ut the line (i.e. above instead of below.
 */

void putline(int k)
{
    char *p;
    int n;

    if (savedline == NULL)
        return;
    /* Bail out without disturbing undo state if there is no room */
    if (!canincrease(savednum))
        return;
    message("Inserting saved stuff...");
    if (k == 0) {
        /* get to the end of the current line */
        while (vi_curs_char < vi_file_end && *vi_curs_char != '\n')
            vi_curs_char++;
    } else
        beginline();
    /* append or insert the characters of the saved line */
    for (p = savedline, n = 0; n < savednum; p++, n++) {
        if (k == 0)
            appchar(*p);
        else
            inschar(*p);
    }
    /* We want to end up at the beginning of the line. */
    while (n-- > 1)
        vi_curs_char--;
    if (k == 1)
        vi_curs_char--;
    beginline();
    /* Set up undo: deleting the pasted line(s) undoes the paste. */
    resetundo();
    vi_uncurs_char = vi_curs_char;
    sprintf(vi_undo_buff, "%ddd", savedcount);
    sprintf(vi_redo_buff, "%s", k == 0 ? "p" : "P");
    message("");
    updatescreen();
}

void inschar(int c)
{
    register char *p;

    /* Move everything in the file over to make */
    /* room for the new char. */
    if (!canincrease(1))
        return;

    for (p = vi_file_end; p > vi_curs_char; p--) {
        *p = *(p - 1);
    }
    *vi_curs_char++ = c;
    vi_file_end++;
    CHANGED;
}

void insstr(char *s)
{
    register char *p;
    int k, n = strlen(s);

    /* Move everything in the file over to make */
    /* room for the new string. */
    if (!canincrease(n))
        return;

    for (p = vi_file_end - 1 + n; p > vi_curs_char; p--) {
        *p = *(p - n);
    }
    for (k = 0; k < n; k++)
        *vi_curs_char++ = *s++;
    vi_file_end += n;
    CHANGED;
}

static void appchar(int c)
{
    char *p, *endp;

    /* Move everything in the file over to make */
    /* room for the new char. */
    if (!canincrease(1))
        return;

    endp = vi_curs_char + 1;
    for (p = vi_file_end; p > endp; p--) {
        *p = *(p - 1);
    }
    *(++vi_curs_char) = c;
    vi_file_end++;
    CHANGED;
}

static int canincrease(int n)
{
    if ((vi_file_end + n) >= vi_file_max) {
        message("Can't add anything, file is too big!");
        vi_state = NORMAL;
        return (0);
    }
    return (1);
}

void delchar(void) {
    char *p;

    /* Check for degenerate case; there's nothing in the file. */
    if (vi_file_mem == vi_file_end)
        return;
    /* Delete the character at Curschar by shifting everything */
    /* in the file down. */
    for (p = vi_curs_char + 1; p < vi_file_end; p++)
        *(p - 1) = *p;
    /* If we just took off the last character of a non-blank line, */
    /* we don't want to end up positioned at the newline. */
    if (*vi_curs_char == '\n' && vi_curs_char > vi_file_mem && *(vi_curs_char - 1) != '\n')
        vi_curs_char--;
    vi_file_end--;
    CHANGED;
}

/*
 * deleol - delete from Curschar to end of line (not including the newline).
 * Sets up vi_undo_buff/vi_uncurs_char so undo works.
 */
void deleol(void) {
    char *scan, *p;
    int n;

    resetundo();
    vi_uncurs_char = vi_curs_char;
    /* Count characters to delete first so delchar() repositioning
     * doesn't confuse the loop. */
    n = 0;
    for (scan = vi_curs_char; *scan != '\n' && scan < vi_file_end; scan++)
        n++;
    /* Build undo string: i<deleted chars>\033 */
    p = vi_undo_buff;
    *p++ = 'i';
    scan = vi_curs_char;
    while (n-- > 0)
        *p++ = *scan++;
    *p++ = '\033';
    *p = '\0';
    /* Now do the actual deletions */
    n = 0;
    for (scan = vi_curs_char; *scan != '\n' && scan < vi_file_end; scan++)
        n++;
    while (n-- > 0)
        delchar();
    addtobuff(vi_redo_buff, 'D', 0, 0, 0, 0, 0);
}

void delword(int deltrailing) /* 1 if trailing white space should be removed */
{
    int c = *vi_curs_char;
    char *p = vi_undo_buff;

    /* The Undo string is an 'i'nsert of the word we're deleting. */
    *p++ = 'i';
    /* If we're positioned on a word separator... */
    if (issepchar(c) && !isspace(c)) {
        /* If we're on a non-space separator, remove */
        /* the separators and any following space. */
        while (issepchar(c) && !isspace(c)) {
            /* Add the deleted character to the vi_undo_buff */
            *p++ = *vi_curs_char;
            delchar();
            c = *vi_curs_char;
        }
    } else { /* we're positioned in the middle of a word */
        int endofline = 0;
        while (!issepchar(*vi_curs_char) && *vi_curs_char != '\n') {
            /* If the next char is a newline, we note */
            /* that fact here, because delchar() won't */
            /* position us there afterword. */
            if (*(vi_curs_char + 1) == '\n')
                endofline = 1;
            /* Add the deleted character to the vi_undo_buff */
            *p++ = *vi_curs_char;
            delchar();
            if (endofline)
                break;
        }
    }
    if (deltrailing) {
        /* remove any trailing white space */
        while (isspace(*vi_curs_char) && *vi_curs_char != '\n') {
            /* Add the deleted character to the vi_undo_buff */
            *p++ = *vi_curs_char;
            delchar();
        }
    }
    *p++ = '\033';
    *p = '\0';
}

void delline(int nlines) {
    int nchars;
    char *p, *q;

    /* If we're not at the beginning of the line, get there. */
    if (*vi_curs_char != '\n') {
        /* back up to the previous newline (or the beginning */
        /* of the file. */
        while (vi_curs_char > vi_file_mem) {
            if (*vi_curs_char == '\n') {
                vi_curs_char++;
                break;
            }
            vi_curs_char--;
        }
    }
    message("Deleting...");
    while (nlines-- > 0) {
        /* Count the characters in the line */
        for (nchars = 1, p = vi_curs_char; p < vi_file_end && *p != '\n'; p++, nchars++)
            ;
        /* Delete the characters of the line */
        /* by moving everything else in the file down. */
        q = vi_curs_char;
        p = vi_curs_char + nchars;
        while (p < vi_file_end)
            *q++ = *p++;
        vi_file_end -= nchars;
        CHANGED;

        /* If we delete the last line in the file, back up */
        if (vi_curs_char >= vi_file_end) {
            if ((vi_curs_char = prevline(vi_curs_char)) == NULL)
                vi_curs_char = vi_file_mem;
            /* and don't try to delete any more lines */
            break;
        }
    }
    message("");
}
