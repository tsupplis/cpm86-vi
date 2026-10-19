#ifndef VI_KEYBOARD_H
#define VI_KEYBOARD_H
void vi_key_init(int ansi);
void vi_key_exit(void);
int vi_key_concurrent(void);
int vi_key_read(void);
#endif
