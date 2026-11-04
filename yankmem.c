#include <stdio.h>
#include "yankmem.h"

extern unsigned vi_yseg_init(void);
extern int vi_yseg_free(unsigned segment);
extern void vi_yseg_write(unsigned segment, unsigned offset,
                          const char *source, unsigned length);
extern void vi_yseg_read(unsigned segment, unsigned offset,
                         char *destination, unsigned length);

static unsigned yank_segment;
static unsigned yank_length;

int vi_yank_init(void)
{
    if (yank_segment)
        return 1;
    yank_segment = vi_yseg_init();
    return yank_segment != 0;
}

void vi_yank_close(void)
{
    if (!yank_segment)
        return;
    if (!vi_yseg_free(yank_segment)) {
        fputs("Unable to release yank memory!\n", stderr);
        return;
    }
    yank_segment = yank_length = 0;
}

int vi_yank_store(const char *source, unsigned length)
{
    if (!yank_segment || length > VI_YANK_CAPACITY ||
        (length && source == NULL))
        return 0;
    vi_yseg_write(yank_segment, 0, source, length);
    yank_length = length;
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
