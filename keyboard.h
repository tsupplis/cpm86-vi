#ifndef VI_KEYBOARD_H
#define VI_KEYBOARD_H
/* Application owns init/close. on_wait is an optional display-maintenance
 * callback used only while BIOS input waits; it must not consume input. */
void vi_key_init(void (*on_wait)(void));
void vi_key_close(void);
int vi_key_read(void); /* Blocking byte read. */
int vi_key_peek(void); /* Nonblocking, non-consuming; -1 when empty. */
/* Decode a normal-mode command byte; -1 means an incomplete/ignored key.
 * reset_count clears the numeric prefix (including on an incomplete ANSI prefix)
 * and, for a returned command, bypasses numeric accumulation. */
int vi_key_decode_command(int c, int *reset_count);
#endif
