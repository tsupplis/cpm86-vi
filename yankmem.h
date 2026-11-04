#ifndef VI_YANKMEM_H
#define VI_YANKMEM_H

#define VI_YANK_CAPACITY 32768U

int vi_yank_init(void);
void vi_yank_close(void);
int vi_yank_store(const char *source, unsigned length);
int vi_yank_load(unsigned offset, char *destination, unsigned length);

#endif
