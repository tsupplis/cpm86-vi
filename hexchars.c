/*
 * STevie - ST editor for VI enthusiasts.    ...Tim Thompson...twitch!tjt...
 */

#include <stdio.h>
#include "stevie.h"

unsigned char vi_char_width[256] = {
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 1, 5, 5, 1, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5
};

/* C0 and DEL/high bytes only; two unused C0 slots keep indexing cheap. */
static char display_text[161][6];

const char *vi_char_text(unsigned char c)
{
    return display_text[c < 32 ? c : c - 95];
}

static void display_mode(char *format)
{
    unsigned c;
    for (c = 0; c < 256; c++)
        if (vi_char_width[c] > 1)
            sprintf(display_text[c < 32 ? c : c - 95], format, c);
}

void octchars(void) { display_mode("[%03o]"); }
void hexchars(void) { display_mode("[x%02x]"); }
void decchars(void) { display_mode("[%3u]"); }

int hextoint(int c)
{
    if (c >= '0' && c <= '9')
        return (c - '0');
    if (c >= 'a' && c <= 'f')
        return (10 + c - 'a');
    if (c >= 'A' && c <= 'F')
        return (10 + c - 'A');
    return (-1);
}
