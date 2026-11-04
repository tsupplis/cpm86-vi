/*
 * STevie - ST editor for VI enthusiasts.    ...Tim Thompson...twitch!tjt...
 */

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stevie.h"
#include "yankmem.h"

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

    snprintf(buff, sizeof buff, "\"%s\"%s line %d of %d", vi_file_name,
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

static int savednum = 0;
static int savedcount = 0;
static int savedlast = 0;

/*
 * yankline
 *
 * Save a copy of the current line(s) for later 'p'lacing.
 */

int yankline(int n) {
    char *savep, *start, *p;
    int leng, count = 0;

    savep = vi_curs_char;
    /* go to the beginning of the current line. */
    beginline();
    start = vi_curs_char;
    /* The last line may end at logical EOF, without a newline. */
    for (p = vi_curs_char; p < vi_file_end; ) {
        if (*p++ == '\n') {
            count++;
            if (--n <= 0)
                break;
        }
    }
    if (p > vi_curs_char && p[-1] != '\n')
        count++;
    leng = p - vi_curs_char;
    vi_curs_char = savep;
    if (!vi_yank_store(start, (unsigned)leng)) {
        message("Unable to store yank buffer; command cancelled!");
        return 0;
    }
    savednum = leng;
    savedcount = count;
    savedlast = leng ? p[-1] : 0;
    return 1;
}

/*
 * putline
 *
 * If there is a currently saved line(s), 'p'ut it.
 * If k==1, 'P'ut the line (i.e. above instead of below.
 */

void putline(int k)
{
    char *insertp, *first;
    int total, prefix, suffix;
    unsigned tail;

    if (savednum == 0)
        return;
    insertp = vi_curs_char;
    prefix = 0;
    if (k == 0) {
        while (insertp < vi_file_end && *insertp != '\n')
            insertp++;
        if (insertp < vi_file_end)
            insertp++;
        else if (insertp > vi_file_mem && insertp[-1] != '\n')
            prefix = 1;
    } else {
        while (insertp > vi_file_mem && insertp[-1] != '\n')
            insertp--;
    }
    /* Separate a nonterminated yank from existing following text. At EOF
     * preserve its missing newline, including when undo restores dd. */
    suffix = insertp < vi_file_end && savedlast != '\n';
    total = savednum + prefix + suffix;
    /* Bulk paste needs no spare byte for subsequent character insertion. */
    if (total > vi_file_max - vi_file_end) {
        message("Can't add anything, file is too big!");
        return;
    }
    message("Inserting saved stuff...");
    tail = (unsigned)(vi_file_end - insertp);
    memmove(insertp + total, insertp, tail);
    first = insertp + prefix;
    if (!vi_yank_load(0, first, (unsigned)savednum)) {
        memmove(insertp, insertp + total, tail);
        message("Unable to read yank buffer; command cancelled!");
        return;
    }
    if (prefix)
        *insertp = '\n';
    if (suffix)
        first[savednum] = '\n';
    vi_file_end += total;
    vi_curs_char = first;
    CHANGED;
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
    int k, n = strlen(s);

    /* Move everything in the file over to make */
    /* room for the new string. */
    if (n == 0 || !canincrease(n))
        return;

    memmove(vi_curs_char + n, vi_curs_char,
            (unsigned)(vi_file_end - vi_curs_char));
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
    if (n >= vi_file_max - vi_file_end) {
        message("Can't add anything, file is too big!");
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
int deleol(void) {
    char *scan, *p;
    int n;

    /* Count characters to delete first so delchar() repositioning
     * doesn't confuse the loop. */
    n = 0;
    for (scan = vi_curs_char; scan < vi_file_end && *scan != '\n'; scan++)
        n++;
    if (n > UNDO_LIMIT) {
        message("Deletion too big for undo; command rejected!");
        return 0;
    }
    resetundo();
    vi_uncurs_char = vi_curs_char;
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
    for (scan = vi_curs_char; scan < vi_file_end && *scan != '\n'; scan++)
        n++;
    while (n-- > 0)
        delchar();
    addtobuff(vi_redo_buff, 'D', 0, 0, 0, 0, 0);
    return 1;
}

int delword(int deltrailing) /* 1 if trailing white space should be removed */
{
    char *scan = vi_curs_char, *start = vi_curs_char;
    char *p = vi_undo_buff;
    int n;

    if (scan >= vi_file_end) {
        resetundo();
        return 1;
    }
    if (issepchar((unsigned char)*scan) && !isspace((unsigned char)*scan)) {
        while (scan < vi_file_end && issepchar((unsigned char)*scan) &&
               !isspace((unsigned char)*scan))
            scan++;
    } else {
        while (scan < vi_file_end && !issepchar((unsigned char)*scan))
            scan++;
    }
    if (deltrailing)
        while (scan < vi_file_end && isspace((unsigned char)*scan) && *scan != '\n')
            scan++;
    n = scan - start;
    if (n > UNDO_LIMIT) {
        message("Deletion too big for undo; command rejected!");
        return 0;
    }
    resetundo();
    *p++ = 'i';
    while (start < scan)
        *p++ = *start++;
    *p++ = '\033';
    *p = '\0';
    if (n == 0)
        return 1;
    memmove(vi_curs_char, scan, (unsigned)(vi_file_end - scan));
    vi_file_end -= n;
    CHANGED;
    return 1;
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
        for (nchars = 0, p = vi_curs_char; p < vi_file_end && *p != '\n'; p++, nchars++)
            ;
        if (p < vi_file_end)
            nchars++; /* Include a newline only when one actually exists. */
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
