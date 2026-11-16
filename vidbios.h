#ifndef VI_VIDBIOS_H
#define VI_VIDBIOS_H
/* Private display backend; coordinates and text are supplied by window.c. */
void vi_bios_goto(int row, int column);
void vi_bios_cursor(int visible);
void vi_bios_clear(int bottom_row);
void vi_bios_putc(int row, int column, int byte);
void vi_bios_run(const char *text, unsigned length,
                 int row, int column, int columns);
#endif
