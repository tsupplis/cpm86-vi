/*
 * STevie - ST editor for VI enthusiasts.    ...Tim Thompson...twitch!tjt...
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stevie.h"

static char *alloc(unsigned size);
static char *ssearch(int dir, char *str);
static char *fwdsearch(char *str);
static char *bcksearch(char *str);

/* Ordered endpoints in one near segment; subtract addresses, not signed ptrdiffs. */
unsigned vi_byte_span(const char *first, const char *last)
{
    return (unsigned)((unsigned long)last - (unsigned long)first);
}

unsigned long vi_count_digit(unsigned long count, unsigned digit)
{
    if (count > (VI_COUNT_MAX - digit) / 10U)
        return VI_COUNT_MAX + 1UL;
    return count * 10UL + digit;
}

/*
 * nextline(curr)
 *
 * Return a pointer to the beginning of the next line after the
 * 'curr' char.  Return NULL if there is no next line.
 */

char *nextline(char *curr)
{
    while (curr < vi_file_end) {
        if (*curr++ == '\n')
            break;
    }
    if (curr >= vi_file_end)
        return (NULL);
    return (curr);
}

/*
 * prevline(curr)
 *
 * Return a pointer to the beginning of the previous line before the
 * 'curr' char.  Return NULL if there is no previous line.
 */

char *prevline(char *curr)
{
    int nnl = 0;

    /* If we are currently positioned on a '\n', */
    /* we are on a blank line.  Adjust accordingly. */
    if (*curr == '\n')
        nnl = -1;
    while (curr > vi_file_mem) {
        /* look for the 2nd previous newline */
        if (*curr == '\n') {
            nnl++;
            if (nnl == 2)
                break;
        }
        curr--;
    }
    if (curr <= vi_file_mem) {
        /* If we found 1 newline, we found the first line */
        if (nnl == 1)
            return (vi_file_mem);
        else
            return (NULL);
    }
    /* return the first char of the previous line */
    return (++curr);
}

/*
 * coladvance(p,col)
 *
 * Try to advance to the specified column, starting at p.
 */

char *coladvance(char *p, unsigned long col)
{
    char *start = p;
    unsigned width;

    while (p < vi_file_end && *p != '\n' && col > 0) {
        width = vi_char_width[(unsigned char)*p];
        if (col < width)
            break;
        col -= width;
        p++;
    }
    if (p > start && (p == vi_file_end || *p == '\n'))
        p--;
    return (p);
}

static char *alloc(unsigned size)
{
    char *p; /* pointer to new storage space */

    p = malloc(size);
    if (p == (char *)NULL) { /* if there is no more room... */
        message("alloc() is unable to find memory!");
    }
    return (p);
}

char *strsave(char *string)
{
    char *saved = alloc((unsigned)(strlen(string) + 1));
    return saved == NULL ? NULL : strcpy(saved, string);
}

int vi_set_filename(char *name)
{
    char *saved;

    if (name == vi_file_name)
        return 1;
    saved = strsave(name);
    if (saved == NULL)
        return 0;
    if (vi_file_name != NULL)
        free(vi_file_name);
    vi_file_name = saved;
    return 1;
}

static char *laststr = NULL;
static int lastdir;

static char *ssearch(int dir, char *str) /* dir: FORWARD or BACKWARD */
{
    if (dir == BACKWARD)
        return (bcksearch(str));
    else
        return (fwdsearch(str));
}

void dosearch(int dir, char *str)
{
    char *p;

    if (str != laststr) {
        p = strsave(str);
        if (p == NULL)
            return;
        if (laststr != NULL)
            free(laststr);
        laststr = p;
    }
    lastdir = dir;
    if ((p = ssearch(dir, laststr)) == NULL)
        message("Pattern not found");
    else {
        char *savep;

        cursupdate();
        /* if we're backing up, we make sure the line we're on */
        /* is on the screen. */
        vi_curs_char = savep = p;
        /* get to the beginning of the line */
        beginline();
        if (vi_curs_char < vi_top_char)
            vi_top_char = vi_curs_char;
        vi_curs_char = savep;
        cursupdate();
        updatescreen();
    }
}

void repsearch(void) {
    if (laststr == NULL)
        beep();
    else {
        dosearch(lastdir, laststr);
    }
}

static char *fwdsearch(char *str)
{
    unsigned leng = strlen(str), probe;
    char *p, *last;
    char first, selected;

    if (leng == 0 || leng > vi_byte_span(vi_file_mem, vi_file_end))
        return NULL;
    /* Reject repeated-prefix near misses before calling memcmp(). */
    probe = 1;
    while (probe < leng && str[probe] == *str) probe++;
    if (probe == leng) probe = 0;
    first = *str;
    selected = str[probe];
    last = vi_file_end - leng;
    p = vi_curs_char < vi_file_end ? vi_curs_char + 1 : vi_file_end;
    for (; p <= last; p++)
        if (*p == first && p[probe] == selected &&
            memcmp(p, str, (unsigned)leng) == 0)
            return p;
    for (p = vi_file_mem; p <= last && p <= vi_curs_char; p++)
        if (*p == first && p[probe] == selected &&
            memcmp(p, str, (unsigned)leng) == 0)
            return p;
    return NULL;
}

static char *bcksearch(char *str)
{
    unsigned leng = strlen(str), probe;
    char *p, *last;
    char first, selected;

    if (leng == 0 || leng > vi_byte_span(vi_file_mem, vi_file_end))
        return NULL;
    probe = 1;
    while (probe < leng && str[probe] == *str) probe++;
    if (probe == leng) probe = 0;
    first = *str;
    selected = str[probe];
    last = vi_file_end - leng;
    p = vi_curs_char > last ? last + 1 : vi_curs_char;
    while (p > vi_file_mem) {
        p--;
        if (*p == first && p[probe] == selected &&
            memcmp(p, str, (unsigned)leng) == 0)
            return p;
    }
    p = last + 1;
    while (p > vi_curs_char) {
        p--;
        if (*p == first && p[probe] == selected &&
            memcmp(p, str, (unsigned)leng) == 0)
            return p;
    }
    return NULL;
}
