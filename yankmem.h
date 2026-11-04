#ifndef VI_YANKMEM_H
#define VI_YANKMEM_H

#ifdef VI_DOS1_COM
#define VI_YANK_CAPACITY 24000U
#else
#define VI_YANK_CAPACITY 38016U
#endif
#define VI_SCREEN_MAX_ROWS 25
#define VI_SCREEN_MAX_COLUMNS 80
#define VI_SCREEN_IMAGE_SIZE (VI_SCREEN_MAX_ROWS * VI_SCREEN_MAX_COLUMNS)
#define VI_SCREEN_REAL 0
#define VI_SCREEN_NEXT 1

int vi_yank_init(void);
void vi_yank_close(void);
unsigned vi_yank_capacity(void);
int vi_yank_store(const char *source, unsigned length);
int vi_yank_load(unsigned offset, char *destination, unsigned length);
int vi_screen_configure(unsigned rows, unsigned columns);
int vi_screen_store(unsigned image, unsigned row, const char *source);
int vi_screen_load(unsigned image, unsigned row, char *destination);

#endif
