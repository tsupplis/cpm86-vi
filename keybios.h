#ifndef VI_KEYBIOS_H
#define VI_KEYBIOS_H
/* Private keyboard backend. Read returns BIOS scan code:ASCII in AX. */
int vi_bios_key_read(void);
int vi_bios_key_ready(void);
#endif
