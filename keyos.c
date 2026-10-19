/* Only the OS capabilities needed by VI's keyboard adapter. */
#include "keyos.h"

/* Local BDOS function 12 wrappers in os.asm. */
extern int osver(void);
extern int ostype(void);

int vi_os_concurrent(void)
{
    return osver() >= 0x30 && (ostype() & 5) != 0;
}
