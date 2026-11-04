#include <assert.h>
#include <string.h>
#include "yankmem.h"

unsigned char test_yank_memory[VI_YANK_CAPACITY];

unsigned vi_yseg_init(void)
{
    return 1;
}

int vi_yseg_free(unsigned segment)
{
    assert(segment == 1);
    return 1;
}

void vi_yseg_write(unsigned segment, unsigned offset,
                   const char *source, unsigned length)
{
    assert(segment == 1 && offset + length <= VI_YANK_CAPACITY);
    if (length)
        memcpy(test_yank_memory + offset, source, length);
}

void vi_yseg_read(unsigned segment, unsigned offset,
                  char *destination, unsigned length)
{
    assert(segment == 1 && offset + length <= VI_YANK_CAPACITY);
    if (length)
        memcpy(destination, test_yank_memory + offset, length);
}
