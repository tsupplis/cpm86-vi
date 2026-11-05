#include <stdio.h>
#include "yankmem.h"

extern unsigned vi_yseg_init(void);
extern unsigned vi_yseg_capacity(void);
extern int vi_yseg_free(unsigned segment);
extern void vi_yseg_write(unsigned segment, unsigned offset,
                          const char *source, unsigned length);
extern void vi_yseg_read(unsigned segment, unsigned offset,
                         char *destination, unsigned length);

static unsigned yank_segment;
static unsigned yank_length;
static unsigned yank_capacity;
static unsigned screen_rows, screen_columns;

int vi_yank_init(void)
{
    if (yank_segment)
        return 1;
    yank_segment = vi_yseg_init();
    if (yank_segment)
        yank_capacity = vi_yseg_capacity();
    return yank_segment != 0;
}

void vi_yank_close(void)
{
    if (!yank_segment)
        return;
    if (!vi_yseg_free(yank_segment)) {
        fputs("Unable to release external memory!\n", stderr);
        return;
    }
    yank_segment = yank_length = 0;
    yank_capacity = screen_rows = screen_columns = 0;
}

unsigned vi_yank_capacity(void)
{
    return yank_capacity;
}

int vi_yank_store(const char *source, unsigned length)
{
    if (!yank_segment || length > yank_capacity ||
        (length && !source))
        return 0;
    vi_yseg_write(yank_segment, 0, source, length);
    yank_length = length;
    return 1;
}

int vi_screen_configure(unsigned rows, unsigned columns)
{
    if (!yank_segment || rows == 0 || rows > VI_SCREEN_MAX_ROWS ||
        columns == 0 || columns > VI_SCREEN_MAX_COLUMNS)
        return 0;
    screen_rows = rows;
    screen_columns = columns;
    return 1;
}

/* Two fixed screen slots follow the platform-specific yank region. */
int vi_screen_store(unsigned image, unsigned row, const char *source)
{
    if (!yank_segment || !screen_columns || image > VI_SCREEN_NEXT ||
        row >= screen_rows || !source)
        return 0;
    vi_yseg_write(yank_segment, yank_capacity + image * VI_SCREEN_IMAGE_SIZE +
                  row * screen_columns, source, screen_columns);
    return 1;
}

int vi_screen_load(unsigned image, unsigned row, char *destination)
{
    if (!yank_segment || !screen_columns || image > VI_SCREEN_NEXT ||
        row >= screen_rows || destination == NULL)
        return 0;
    vi_yseg_read(yank_segment, yank_capacity + image * VI_SCREEN_IMAGE_SIZE +
                 row * screen_columns, destination, screen_columns);
    return 1;
}

int vi_yank_load(unsigned offset, char *destination, unsigned length)
{
    if (!yank_segment || offset > yank_length ||
        length > yank_length - offset || (length && destination == NULL))
        return 0;
    vi_yseg_read(yank_segment, offset, destination, length);
    return 1;
}
