/* Keyboard boundary: platform input, buffering and command-key decoding. */
#include "keyboard.h"
#ifdef __MSDOS__
#define __PCBIOS__
#endif
#ifdef __CPM86__
#include "sgtty.h"
#include "keyos.h"
extern int bdos(int fn, int argument);
#endif

static int concurrent_keys;
static int ansi_keys;
static int pending_bracket, pending_key;
static int peeked = -1;
enum { KEY_COMMAND, KEY_ANSI_PREFIX, KEY_ESCAPE, KEY_CPM_PREFIX };
static int command_state;
static void (*wait_hook)(void);

#if defined(__PCBIOS__)

/* One pending byte, for the second half of a synthesized ESC sequence. */
static int pending = -1;

#include "keybios.h"

static int getch(int wait) {
    static char scans[] = "\110\120\115\113\107\111\122\121\117\123";
    static char translated[] = "ABCDHIL\n\032\177";
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
        while (!vi_bios_key_ready()) {
            if (!wait)
                return -1;
            if (wait_hook) (*wait_hook)();
        }
        c = vi_bios_key_read();
        al = c & 0xff;
        ah = (c >> 8) & 0xff;
        if (al != 0)
            return al;
        /* Extended key: no ASCII, decode the BIOS scan code in AH. */
        for (al = 0; al < 10; al++) {
            if (ah != (unsigned char)scans[al])
                continue;
            c = translated[al];
            if (al >= 7)
                return c;
            pending = c;
            return 27;
        }
    }
}

#elif defined(__VTCMD__)

#define GETCH_BUFLEN 64
static char getch_buffer[GETCH_BUFLEN];
static int getch_size, getch_offset;

static int getch(int wait) {
    int c, d;
    if (getch_size > 0) {
        c = (unsigned char)getch_buffer[getch_offset];
        getch_size--;
        getch_offset = (getch_offset + 1) % GETCH_BUFLEN;
        return c;
    }
    while (!(c = bdos(6, 0xFF)))
        if (!wait)
            return -1;
    while (getch_size < GETCH_BUFLEN && (d = bdos(6, 0xFF))) {
        getch_buffer[(getch_offset + getch_size) % GETCH_BUFLEN] = d;
        getch_size++;
    }
    return c;
}

#endif /* __PCBIOS__ / __VTCMD__ */

static int concurrent_read(void)
{
#ifdef __CPM86__
    int c;
    int key = 0;
    if (pending_bracket) { pending_bracket = 0; return '['; }
    if (pending_key) { c = pending_key; pending_key = 0; return c; }
    c = bdos(6, 253) & 255; /* OS wait: suspend until a character arrives. */
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

void vi_key_init(void (*on_wait)(void))
{
#ifdef __CPM86__
    struct sgttyb stty;
    stty.sg_flags = CRMOD | CBREAK;
    ioctl(0, TIOCSETP, &stty);
    concurrent_keys = vi_os_concurrent();
    if (concurrent_keys) {
        bdos(2, 27); bdos(2, '6');
    }
#endif
#if defined(__VT100__)
    ansi_keys = 1;
#else
    ansi_keys = 0;
#endif
    wait_hook = on_wait;
    peeked = -1;
    pending_bracket = pending_key = command_state = 0;
#if defined(__PCBIOS__)
    pending = -1;
#else
    getch_size = getch_offset = 0;
#endif
}

void vi_key_close(void)
{
#ifdef __CPM86__
    if (concurrent_keys) {
        bdos(2, 27); bdos(2, '7');
    }
#endif
    concurrent_keys = 0;
    pending_bracket = pending_key = command_state = 0;
    peeked = -1;
    wait_hook = 0;
}

int vi_key_read(void)
{
    int c;
    if (peeked >= 0) {
        c = peeked;
        peeked = -1;
        return c;
    }
    if (concurrent_keys) return concurrent_read();
    return getch(1);
}

int vi_key_peek(void)
{
    if (peeked >= 0) return peeked;
#ifdef __CPM86__
    if (concurrent_keys) {
        if (pending_bracket || pending_key || (bdos(11, 0) & 255))
            peeked = concurrent_read();
    } else
#endif
        peeked = getch(0);
    return peeked;
}

/* Normal-mode decoding also sees replayed command bytes. Prefixes are
 * retained here, not in the editor state machine. Insert/literal input
 * continues to receive unmodified bytes through vi_key_read(). */
int vi_key_decode_command(int c, int *reset_count)
{
    int state = command_state;
    command_state = 0;
    *reset_count = 0;
    if (state == KEY_ANSI_PREFIX) { /* ANSI ESC [ */
        if (c == '[') {
            *reset_count = 1;
            command_state = KEY_ESCAPE;
            return -1;
        }
    } else if (state == KEY_ESCAPE) { /* Navigation final byte */
        *reset_count = 1;
        switch (c) {
        case 'A': return 'k';
        case 'B': return 'j';
        case 'C': return 'l';
        case 'D': return 'h';
        case 'H': return '0';
        case 'I': return 02;
        }
        *reset_count = 0;
    } else if (state == KEY_CPM_PREFIX) { /* CP/M Ctrl-Q prefix */
        if (c == 'E') return '0';
        if (c == 'X') return '$';
        return -1;
    }
    if (c == 27) {
        command_state = ansi_keys ? KEY_ANSI_PREFIX : KEY_ESCAPE;
        return -1;
    }
    /* Unknown escape tails remain ordinary commands, as before. */
    if (state) return c;
#ifdef __CPM86__
    if (c == 0x11) { command_state = KEY_CPM_PREFIX; return -1; }
    switch (c) {
    case 0x13: return 'h';
    case 0x04: return 'l';
    case 0x05: return 'k';
    case 0x18: return 'j';
    case 0x03: return 06;
    case 0x12: return 02;
    }
#endif
    if (c == 26 || c == 10) {
        *reset_count = 1;
        return c == 26 ? '$' : 06;
    }
    return c;
}
