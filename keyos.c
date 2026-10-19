/* Local OS detection and console restoration for VI. */
#include "keyos.h"

/* Local BDOS function 12 wrappers in os.asm. */
extern int osver(void);
extern int ostype(void);
extern int dosplus_crtreset(void);

int vi_os_concurrent(void)
{
    return osver() >= 0x30 && (ostype() & 5) != 0;
}

void vi_os_close(void)
{
    /* DOS Plus: BDOS 4.1 without the MP/M/Concurrent type bits.
     * Never invoke its BIOS reset on a concurrent system. */
    if (osver() == 0x41 && (ostype() & 5) == 0)
        dosplus_crtreset();
}
