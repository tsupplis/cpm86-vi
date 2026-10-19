/* Concurrent keyboard adapter. BIOS input is never used on this path. */
#include <stdio.h>
#include "keyboard.h"
#ifdef __CPM86__
#include "keyos.h"
extern int bdos(int fn, int argument);
static int concurrent_keys;
static int ansi_keys;
static int pending_bracket;
static int pending_key;

static void expansion(int enabled)
{
    bdos(2, 27); bdos(2, enabled ? '7' : '6');
}
#endif

void vi_key_init(int ansi)
{
#ifdef __CPM86__
    concurrent_keys = vi_os_concurrent();
    ansi_keys = ansi;
    pending_key = pending_bracket = 0;
    if (concurrent_keys) expansion(0);
#endif
}

void vi_key_exit(void)
{
#ifdef __CPM86__
    if (concurrent_keys) expansion(1);
    concurrent_keys = 0;
    pending_key = pending_bracket = 0;
#endif
}

int vi_key_concurrent(void)
{
#ifdef __CPM86__
    return concurrent_keys;
#else
    return 0;
#endif
}

int vi_key_read(void)
{
#ifdef __CPM86__
    int c;
    int key = 0;
    if (pending_bracket) { pending_bracket = 0; return '['; }
    if (pending_key) { c = pending_key; pending_key = 0; return c; }
    while (!(c = bdos(6, 255) & 255)) ;
    switch (c) {
    case 0xC8: key = 'A'; break;
    case 0xD0: key = 'B'; break;
    case 0xCD: key = 'C'; break;
    case 0xCB: key = 'D'; break;
    case 0xC7: key = 'H'; break;
    case 0xC9: key = 'I'; break;
    case 0xD2: key = 'L'; break;
    case 0xCF: return 26;    /* End */
    case 0xD1: return 10;    /* Page Down */
    case 0xD3: return 127;   /* Delete */
    }
    if (key) {
        pending_bracket = ansi_keys;
        pending_key = key;
        return 27;
    }
    return c;
#else
    return 0;
#endif
}
