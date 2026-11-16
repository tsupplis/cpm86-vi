/* Private CP/M console backend: setup, raw input and Concurrent key codes. */
#include "keycpm.h"
#include "oscpm.h"
#include "sgtty.h"
extern int bdos(int fn, int argument);

static int concurrent_keys, ansi_keys;
static int pending_bracket, pending_key;

#define GETCH_BUFLEN 64
static char getch_buffer[GETCH_BUFLEN];
static int getch_size, getch_offset;

static int legacy_read(int wait) {
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

static int concurrent_read(void) {
    int c;
    int key = 0;
    if (pending_bracket) {
        pending_bracket = 0;
        return '[';
    }
    if (pending_key) {
        c = pending_key;
        pending_key = 0;
        return c;
    }
    c = bdos(6, 253) & 255; /* OS wait: suspend until a character arrives. */
    switch (c) {
    case 0xC8:
        key = 'A';
        break;
    case 0xD0:
        key = 'B';
        break;
    case 0xCD:
        key = 'C';
        break;
    case 0xCB:
        key = 'D';
        break;
    case 0xC7:
        key = 'H';
        break;
    case 0xC9:
        key = 'I';
        break;
    case 0xD2:
        key = 'L';
        break;
    case 0xCF:
        return 26; /* End */
    case 0xD1:
        return 10; /* Page Down */
    case 0xD3:
        return 127; /* Delete */
    }
    if (key) {
        pending_bracket = ansi_keys;
        pending_key = key;
        return 27;
    }
    return c;
}

int vi_cpm_key_init(int ansi) {
    unsigned identity;
    struct sgttyb stty;
    identity = vi_cpm_os_identity();
    concurrent_keys = (identity & 255) >= 0x30 && ((identity >> 8) & 5) != 0;
    /* Classic BDOS 2 buffers typeahead that BDOS 6 cannot retrieve.
     * RAW keeps normal C output on the same direct console interface
     * as our input. CRMOD retains the runtime's LF-to-CRLF mapping. */
    stty.sg_flags = CRMOD | (concurrent_keys ? CBREAK : RAW);
    ioctl(0, TIOCSETP, &stty);
    ansi_keys = ansi;
    pending_bracket = pending_key = getch_size = getch_offset = 0;
    if (concurrent_keys) {
        bdos(2, 27);
        bdos(2, '6');
    }
    return concurrent_keys;
}

void vi_cpm_key_close(void) {
    if (concurrent_keys) {
        bdos(2, 27);
        bdos(2, '7');
    }
    concurrent_keys = 0;
    pending_bracket = pending_key = getch_size = getch_offset = 0;
}

int vi_cpm_key_read(int wait) {
    if (!concurrent_keys)
        return legacy_read(wait);
    if (!wait && !pending_bracket && !pending_key && !(bdos(11, 0) & 255))
        return -1;
    return concurrent_read();
}
