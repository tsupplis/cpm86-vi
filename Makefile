CC     = aztec42_cc
STRIP  = aztec42_sqz
LD     = aztec42_link
CPM_LDFLAGS = -lc86
DOS_LDFLAGS = -ld11 -ld11

# Flags common to both CP/M-86 builds
CPM_CFLAGS = -D__CPM86__
DOS_CFLAGS = -D__PCBIOS__
PCBIOS_CFLAGS = -D__PCBIOS__

GIT_VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo unknown)

# Objects shared by both terminal builds (window.o and edit.o excluded)
SHARED_OBJS = \
	cmdline.o  \
	help.o     \
	hexchars.o \
	linefunc.o \
	main.o     \
	misccmds.o \
	normal.o

# --------------------------------------------------------------------
# Top-level targets
# --------------------------------------------------------------------
all: vivt52.cmd vivt100.cmd vidos.com vibios.cmd cpmtest.img asmtest.com getch.cmd curstest.cmd curstest.com

# --------------------------------------------------------------------
# Link targets
# --------------------------------------------------------------------
vivt52.cmd: $(SHARED_OBJS) edtvt52.o winvt52.o
	$(LD) -o $@ $^ $(CPM_LDFLAGS)

vivt100.cmd: $(SHARED_OBJS) edtvt100.o winvt100.o
	$(LD) -o $@ $^ $(CPM_LDFLAGS)

vidos.com: $(SHARED_OBJS) edtdos.o windos.o
	$(LD) -o $@ $^ $(DOS_LDFLAGS)

# CP/M-86 binary using the PC BIOS window/keyboard implementation (no VT
# escape codes, no BDOS console I/O) instead of the DOS API.
vibios.cmd: $(SHARED_OBJS) edtbios.o winbios.o
	$(LD) -o $@ $^ $(CPM_LDFLAGS)

# --------------------------------------------------------------------
# Scratch program: isolate windgoto/windputc from all of vi's own
# screen/timing logic, to check raw BIOS cursor positioning under CP/M-86.
# --------------------------------------------------------------------

curstest.cmd: curstest.o winbios.o
	$(LD) -o $@ $^ $(CPM_LDFLAGS)

curstest.o: curstest.c
	$(CC) $(CPM_CFLAGS) -o $@ curstest.c
	$(STRIP) $@

# Same diagnostic, linked for plain DOS, for direct comparison.
curstest.com: curstestdos.o windos.o
	$(LD) -o $@ $^ $(DOS_LDFLAGS)

curstestdos.o: curstest.c
	$(CC) $(DOS_CFLAGS) -o $@ curstest.c
	$(STRIP) $@

# --------------------------------------------------------------------
# Scratch program for working out #asm/#endasm variable access rules.
# --------------------------------------------------------------------

asmtest.com: asmtest.o
	$(LD) -o $@ $^ $(DOS_LDFLAGS)

asmtest.o: asmtest.c
	$(CC) $(DOS_CFLAGS) -o $@ asmtest.c

getch.cmd: getch.o
	$(LD) -o $@ $^ $(CPM_LDFLAGS)

getch.o: getch.c
	$(CC) $(CPM_CFLAGS) -o $@ getch.c
	$(STRIP) $@

# --------------------------------------------------------------------
# edit.c and window.c – two variants each
# --------------------------------------------------------------------

edtvt52.o: edit.c
	$(CC) $(CPM_CFLAGS) -D__VTCMD__ -D__VT52__ -o $@ edit.c
	$(STRIP) $@

winvt52.o: window.c gitver.h
	$(CC) $(CPM_CFLAGS) -D__VTCMD__ -D__VT52__ -o $@ window.c
	$(STRIP) $@

edtvt100.o: edit.c
	$(CC) $(CPM_CFLAGS) -D__VTCMD__ -D__VT100__ -o $@ edit.c
	$(STRIP) $@

winvt100.o: window.c gitver.h
	$(CC) $(CPM_CFLAGS) -D__VTCMD__ -D__VT100__ -o $@ window.c
	$(STRIP) $@

edtdos.o: edit.c
	$(CC) $(DOS_CFLAGS) -o $@ edit.c
	$(STRIP) $@

windos.o: window.c gitver.h
	$(CC) $(DOS_CFLAGS) -o $@ window.c
	$(STRIP) $@

edtbios.o: edit.c
	$(CC) $(CPM_CFLAGS) $(PCBIOS_CFLAGS) -o $@ edit.c
	$(STRIP) $@

winbios.o: window.c gitver.h
	$(CC) $(CPM_CFLAGS) $(PCBIOS_CFLAGS) -o $@ window.c
	$(STRIP) $@

# Regenerated on every build so it always reflects the current git state.
gitver.h: FORCE
	echo '#define GIT_VERSION "$(GIT_VERSION)"' > gitver.h

FORCE:

# --------------------------------------------------------------------
# Shared object rules
# --------------------------------------------------------------------
cmdline.o: cmdline.c
	$(CC) $(CPM_CFLAGS) -o $@ cmdline.c
	$(STRIP) $@

help.o: help.c
	$(CC) $(CPM_CFLAGS) -o $@ help.c
	$(STRIP) $@

hexchars.o: hexchars.c
	$(CC) $(CPM_CFLAGS) -o $@ hexchars.c
	$(STRIP) $@

linefunc.o: linefunc.c
	$(CC) $(CPM_CFLAGS) -o $@ linefunc.c
	$(STRIP) $@

main.o: main.c
	$(CC) $(CPM_CFLAGS) -o $@ main.c
	$(STRIP) $@

misccmds.o: misccmds.c
	$(CC) $(CPM_CFLAGS) -o $@ misccmds.c
	$(STRIP) $@

normal.o: normal.c
	$(CC) $(CPM_CFLAGS) -o $@ normal.c
	$(STRIP) $@

cpmtest.img: vivt52.cmd vivt100.cmd vibios.cmd curstest.cmd cpmbase.img test.txt
	cp cpmbase.img cpmtest.img
	cpmrm -f ibmpc-514ss cpmtest.img 0:*.cmd
	cpmrm -f ibmpc-514ss cpmtest.img 0:test.txt
	cpmcp -f ibmpc-514ss cpmtest.img vivt52.cmd 0:vi.cmd
	cpmcp -f ibmpc-514ss cpmtest.img vivt52.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img vivt100.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img vibios.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img curstest.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img test.txt 0:
	cpmls -F -f ibmpc-514ss cpmtest.img 0:*.*

dostest.img: vidos.com curstest.com dosbase.img test.txt
	cp dosbase.img dostest.img
	mcopy -i dostest.img vidos.com  ::VIDOS.COM
	mcopy -i dostest.img vidos.com  ::VI.COM
	mcopy -i dostest.img curstest.com  ::CURSTEST.COM
	mcopy -i dostest.img test.txt  ::TEST.TXT
	mdir -i dostest.img ::

# --------------------------------------------------------------------
# Binary zip
# --------------------------------------------------------------------
dist: vi-bin.zip

vi-bin.zip: vivt52.cmd vivt100.cmd vibios.cmd vidos.com
	rm -f vi-bin.zip
	zip vi-bin.zip vivt52.cmd vivt100.cmd vibios.cmd vidos.com

# --------------------------------------------------------------------
# Utility
# --------------------------------------------------------------------
clean:
	$(RM) cpmtest.img *.o gitver.h \
	vivt52.cmd vivt100.cmd vidos.com vibios.cmd curstest.cmd curstest.com asmtest.com getch.cmd \
	vi-bin.zip

cpm86test: cpmtest.img
	./cpm86

test: cpm86test

dostest: dostest.img
	./dos
