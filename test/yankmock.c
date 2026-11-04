#include <assert.h>
#include <string.h>
#include "yankmem.h"

#if defined(__PCDOS__) && __PCDOS__ == 11
unsigned char test_yank_memory[32768UL];
#else
unsigned char test_yank_memory[65536UL];
#endif

unsigned vi_yseg_init(void)
{
    return 1;
}

unsigned vi_yseg_capacity(void)
{
#if defined(__PCDOS__) && __PCDOS__ == 11
    return 24000U;
#else
    return VI_YANK_CAPACITY;
#endif
}

int vi_yseg_free(unsigned segment)
{
    assert(segment == 1);
    return 1;
}

void vi_yseg_write(unsigned segment, unsigned offset,
                   const char *source, unsigned length)
{
    assert(segment == 1 && offset + length <= sizeof test_yank_memory);
    if (length)
        memcpy(test_yank_memory + offset, source, length);
}

void vi_yseg_read(unsigned segment, unsigned offset,
                  char *destination, unsigned length)
{
    assert(segment == 1 && offset + length <= sizeof test_yank_memory);
    if (length)
        memcpy(destination, test_yank_memory + offset, length);
}
