CC=aztec_cc
CFLAGS=-D__CPM86__
STRIP=aztec_sqz
LDFLAGS=-lm -lc86
LD=aztec_link
BINEXT=.cmd

TOOLS=vi$(BINEXT)

OBJECTS=cmdline.o edit.o help.o hexchars.o linefunc.o main.o misccmds.o \
 normal.o window.o

all: $(TOOLS) cpm86.img cpmtest.img

vi$(BINEXT): $(OBJECTS)
	$(LD) -o $@ $^ $(LDFLAGS)

.c.o:
	$(CC) $(CFLAGS) $<
	$(STRIP) $@

cpmtest.img: $(TOOLS)
	cpmrm -f ibmpc-514ss cpmtest.img 0:*.cmd
	cpmcp -f ibmpc-514ss cpmtest.img vi.cmd 0:
	cpmls -F -f ibmpc-514ss cpmtest.img 0:*.*


clean:
	$(RM) *.o $(TOOLS)

test: cpmtest.img
	./cpm86
