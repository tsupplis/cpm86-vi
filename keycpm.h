#ifndef VI_KEYCPM_H
#define VI_KEYCPM_H
/* Private console backend. Init returns nonzero for Concurrent BDOS input,
 * which takes precedence over BIOS input. ansi selects the escape format. */
int vi_cpm_key_init(int ansi);
void vi_cpm_key_close(void);
/* wait=0 polls and returns -1 when empty; wait=1 blocks. Consumes a byte. */
int vi_cpm_key_read(int wait);
/* Idle after an empty blocking poll; a no-op outside classic CP/M-86. */
void vi_cpm_key_idle(void);
#endif
