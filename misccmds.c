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
    while (Curschar < Fileend && (*Curschar) != '\n')
        Curschar++;
    /* Try to handle a file that doesn't end with a newline */
    if (Curschar >= Fileend)
        Curschar = Fileend - 1;
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

    sprintf(buff, "\"%s\"%s line %d of %d", Filename,
            Changed ? " [Modified]" : "", cntlines(Filemem, Curschar),
            cntlines(Filemem, Fileend) - 1);
    message(buff);
}

void gotoline(int n)
{
    char *p;

    /* n==0 means "last line": use the same descent logic as the
     * numbered case, with the actual line count as the target. */
    if (n == 0)
        n = cntlines(Filemem, Fileend) - 1;
    /* Start at the top of the file and go down 'n'-1 lines */
    Curschar = Filemem;
    while (--n > 0) {
        if ((p = nextline(Curschar)) == NULL)
            break;
        Curschar = p;
    }
    Topchar = Curschar;
    for (n = 0; n < Rows / 2; n++) {
        if ((p = prevline(Topchar)) == NULL)
            break;
        Topchar = p;
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
    savep = Curschar;
    /* go to the beginning of the current line. */
    beginline();
    /* compute length of line */
    for (p = Curschar, leng = 0;; p++) {
        if (*p == '\n') {
            /* keep going until we've seen 'n' lines */
            if (--n <= 0)
                break;
        }
        leng++;
    }
    /* save a copy of it */
    savedline = malloc((unsigned)(leng + 2));
    for (p = Curschar, q = savedline, k = 0; k < leng; k++)
        *q++ = *p++;
    /* get the final newline */
    *q++ = *p;
    *q = '\0';
    Curschar = savep;
    savednum = leng + 1;
    savedcount = (Prenum == 0 ? 1 : Prenum);
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
        while (Curschar < Fileend && *Curschar != '\n')
            Curschar++;
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
        Curschar--;
    if (k == 1)
        Curschar--;
    beginline();
    /* Set up undo: deleting the pasted line(s) undoes the paste. */
    resetundo();
    Uncurschar = Curschar;
    sprintf(Undobuff, "%ddd", savedcount);
    sprintf(Redobuff, "%s", k == 0 ? "p" : "P");
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

    for (p = Fileend; p > Curschar; p--) {
        *p = *(p - 1);
    }
    *Curschar++ = c;
    Fileend++;
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

    for (p = Fileend - 1 + n; p > Curschar; p--) {
        *p = *(p - n);
    }
    for (k = 0; k < n; k++)
        *Curschar++ = *s++;
    Fileend += n;
    CHANGED;
}

static void appchar(int c)
{
    char *p, *endp;

    /* Move everything in the file over to make */
    /* room for the new char. */
    if (!canincrease(1))
        return;

    endp = Curschar + 1;
    for (p = Fileend; p > endp; p--) {
        *p = *(p - 1);
    }
    *(++Curschar) = c;
    Fileend++;
    CHANGED;
}

static int canincrease(int n)
{
    if ((Fileend + n) >= Filemax) {
        message("Can't add anything, file is too big!");
        State = NORMAL;
        return (0);
    }
    return (1);
}

void delchar(void) {
    char *p;

    /* Check for degenerate case; there's nothing in the file. */
    if (Filemem == Fileend)
        return;
    /* Delete the character at Curschar by shifting everything */
    /* in the file down. */
    for (p = Curschar + 1; p < Fileend; p++)
        *(p - 1) = *p;
    /* If we just took off the last character of a non-blank line, */
    /* we don't want to end up positioned at the newline. */
    if (*Curschar == '\n' && Curschar > Filemem && *(Curschar - 1) != '\n')
        Curschar--;
    Fileend--;
    CHANGED;
}

/*
 * deleol - delete from Curschar to end of line (not including the newline).
 * Sets up Undobuff/Uncurschar so undo works.
 */
void deleol(void) {
    char *scan, *p;
    int n;

    resetundo();
    Uncurschar = Curschar;
    /* Count characters to delete first so delchar() repositioning
     * doesn't confuse the loop. */
    n = 0;
    for (scan = Curschar; *scan != '\n' && scan < Fileend; scan++)
        n++;
    /* Build undo string: i<deleted chars>\033 */
    p = Undobuff;
    *p++ = 'i';
    scan = Curschar;
    while (n-- > 0)
        *p++ = *scan++;
    *p++ = '\033';
    *p = '\0';
    /* Now do the actual deletions */
    n = 0;
    for (scan = Curschar; *scan != '\n' && scan < Fileend; scan++)
        n++;
    while (n-- > 0)
        delchar();
    addtobuff(Redobuff, 'D', 0, 0, 0, 0, 0);
}

void delword(int deltrailing) /* 1 if trailing white space should be removed */
{
    int c = *Curschar;
    char *p = Undobuff;

    /* The Undo string is an 'i'nsert of the word we're deleting. */
    *p++ = 'i';
    /* If we're positioned on a word separator... */
    if (issepchar(c) && !isspace(c)) {
        /* If we're on a non-space separator, remove */
        /* the separators and any following space. */
        while (issepchar(c) && !isspace(c)) {
            /* Add the deleted character to the Undobuff */
            *p++ = *Curschar;
            delchar();
            c = *Curschar;
        }
    } else { /* we're positioned in the middle of a word */
        int endofline = 0;
        while (!issepchar(*Curschar) && *Curschar != '\n') {
            /* If the next char is a newline, we note */
            /* that fact here, because delchar() won't */
            /* position us there afterword. */
            if (*(Curschar + 1) == '\n')
                endofline = 1;
            /* Add the deleted character to the Undobuff */
            *p++ = *Curschar;
            delchar();
            if (endofline)
                break;
        }
    }
    if (deltrailing) {
        /* remove any trailing white space */
        while (isspace(*Curschar) && *Curschar != '\n') {
            /* Add the deleted character to the Undobuff */
            *p++ = *Curschar;
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
    if (*Curschar != '\n') {
        /* back up to the previous newline (or the beginning */
        /* of the file. */
        while (Curschar > Filemem) {
            if (*Curschar == '\n') {
                Curschar++;
                break;
            }
            Curschar--;
        }
    }
    message("Deleting...");
    while (nlines-- > 0) {
        /* Count the characters in the line */
        for (nchars = 1, p = Curschar; p < Fileend && *p != '\n'; p++, nchars++)
            ;
        /* Delete the characters of the line */
        /* by moving everything else in the file down. */
        q = Curschar;
        p = Curschar + nchars;
        while (p < Fileend)
            *q++ = *p++;
        Fileend -= nchars;
        CHANGED;

        /* If we delete the last line in the file, back up */
        if (Curschar >= Fileend) {
            if ((Curschar = prevline(Curschar)) == NULL)
                Curschar = Filemem;
            /* and don't try to delete any more lines */
            break;
        }
    }
    message("");
}
