CC     = aztec42_cc
STRIP  = aztec42_sqz
LD     = aztec42_link
CPM86_LDFLAGS = -lc86
DOS11_LDFLAGS = -ld11
DOS20_LDFLAGS = -lc

# Flags common to both CP/M-86 builds
CFLAGS =
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
all: vicp52.cmd vicp100.cmd vicpbios.cmd \
 vid1bios.com vid2bios.com \
 cpmtest.img asmtest.com getch.cmd curstest.cmd curstest.com

# --------------------------------------------------------------------
# Link targets
# --------------------------------------------------------------------
vicp52.cmd: $(SHARED_OBJS) edtcp52.o wincp52.o
	$(LD) -o $@ $^ $(CPM86_LDFLAGS)

vicp100.cmd: $(SHARED_OBJS) edtcp100.o wincp100.o
	$(LD) -o $@ $^ $(CPM86_LDFLAGS)

vid1bios.com: $(SHARED_OBJS) edtd1bio.o wind1bio.o
	$(LD) -o $@ $^ $(DOS11_LDFLAGS)

vid2bios.com: $(SHARED_OBJS) edtd2bio.o wind2bio.o
	$(LD) -o $@ $^ $(DOS20_LDFLAGS)

# CP/M-86 binary using the PC BIOS window/keyboard implementation (no VT
# escape codes, no BDOS console I/O) instead of the DOS API.
vicpbios.cmd: $(SHARED_OBJS) edtcpbio.o wincpbio.o
	$(LD) -o $@ $^ $(CPM86_LDFLAGS)

# --------------------------------------------------------------------
# Scratch program: isolate windgoto/windputc from all of vi's own
# screen/timing logic, to check raw BIOS cursor positioning under CP/M-86.
# --------------------------------------------------------------------

curstest.cmd: curstest.o wincpbio.o
	$(LD) -o $@ $^ $(CPM86_LDFLAGS)

curstest.o: curstest.c
	$(CC) $(CFLAGS) -o $@ curstest.c
	$(STRIP) $@

# Same diagnostic, linked for plain DOS, for direct comparison.
curstest.com: curstestdos.o wind1bio.o
	$(LD) -o $@ $^ $(DOS11_LDFLAGS)

curstestdos.o: curstest.c
	$(CC) $(CFLAGS) -D__PCBIOS__ -D__PCDOS__==11 -o $@ $^
	$(STRIP) $@

# --------------------------------------------------------------------
# Scratch program for working out #asm/#endasm variable access rules.
# --------------------------------------------------------------------

asmtest.com: asmtest.o
	$(LD) -o $@ $^ $(DOS11_LDFLAGS)

asmtest.o: asmtest.c
	$(CC) $(CFLAGS) -o $@ $^

getch.cmd: getch.o
	$(LD) -o $@ $^ $(CPM86_LDFLAGS)

getch.o: getch.c
	$(CC) $(CFLAGS) -o $@ $^
	$(STRIP) $@

# --------------------------------------------------------------------
# edit.c and window.c – two variants each
# --------------------------------------------------------------------

edtcp52.o: edit.c
	$(CC) $(CFLAGS) -D__CPM86__ -D__VTCMD__ -D__VT52__ -o $@ edit.c
	$(STRIP) $@

wincp52.o: window.c gitver.h
	$(CC) $(CFLAGS) -D__CPM86__ -D__VTCMD__ -D__VT52__ -o $@ $<
	$(STRIP) $@

edtcp100.o: edit.c
	$(CC) $(CFLAGS) -D__CPM86__ -D__VTCMD__ -D__VT100__ -o $@ $^
	$(STRIP) $@

wincp100.o: window.c gitver.h
	$(CC) $(CFLAGS) -D__CPM86__ -D__VTCMD__ -D__VT100__ -o $@ $<
	$(STRIP) $@

edtd1bio.o: edit.c
	$(CC) $(DOS_CFLAGS) -D__PCDOS__=11 -D__PCBIOS__ -o $@ $^
	$(STRIP) $@

wind1bio.o: window.c gitver.h
	$(CC) $(CFLAGS) -D__PCDOS__=11 -D__PCBIOS__ -o $@ $<
	$(STRIP) $@

edtd2bio.o: edit.c
	$(CC) $(CFLAGS) -D__PCDOS__=20 -D__PCBIOS__ -o $@ $^
	$(STRIP) $@

wind2bio.o: window.c gitver.h
	$(CC) $(CFLAGS) -D__PCDOS__=20 -D__PCBIOS__ -o $@ $<
	$(STRIP) $@

edtcpbio.o: edit.c
	$(CC) -D__CPM86__ -D__PCBIOS__ -o $@ $^
	$(STRIP) $@

wincpbio.o: window.c gitver.h
	$(CC) -D__CPM86__ -D__PCBIOS__ -o $@ $<
	$(STRIP) $@

# Checked against the current git state on every build, but only actually
# rewritten (touching its mtime) if the version string changed -- otherwise
# `make` would consider every window.c object stale on every invocation.
# PID-tagged tmp file so concurrent/parallel make runs don't clash.
gitver.h: FORCE
	@echo '#define GIT_VERSION "$(GIT_VERSION)"' > gitver.h.$$$$.tmp && \
	(cmp -s gitver.h.$$$$.tmp gitver.h 2>/dev/null && $(RM) gitver.h.$$$$.tmp || mv gitver.h.$$$$.tmp gitver.h)

FORCE:

# --------------------------------------------------------------------
# Shared object rules
# --------------------------------------------------------------------
cmdline.o: cmdline.c
	$(CC) $(CFLAGS) -o $@ cmdline.c
	$(STRIP) $@

help.o: help.c
	$(CC) $(CFLAGS) -o $@ help.c
	$(STRIP) $@

hexchars.o: hexchars.c
	$(CC) $(CFLAGS) -o $@ hexchars.c
	$(STRIP) $@

linefunc.o: linefunc.c
	$(CC) $(CFLAGS) -o $@ linefunc.c
	$(STRIP) $@

main.o: main.c
	$(CC) $(CFLAGS) -o $@ main.c
	$(STRIP) $@

misccmds.o: misccmds.c
	$(CC) $(CFLAGS) -o $@ misccmds.c
	$(STRIP) $@

normal.o: normal.c
	$(CC) $(CFLAGS) -o $@ normal.c
	$(STRIP) $@

cpmtest.img: vicp52.cmd vicp100.cmd vicpbios.cmd curstest.cmd cpmbase.img test.txt \
    getch.cmd vid1bios.com vid2bios.com
	cp cpmbase.img cpmtest.img
	cpmrm -f ibmpc-514ss cpmtest.img 0:*.cmd
	cpmrm -f ibmpc-514ss cpmtest.img 0:test.txt
	cpmcp -f ibmpc-514ss cpmtest.img vicp52.cmd 0:vi.cmd
	cpmcp -f ibmpc-514ss cpmtest.img vicp52.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img vicp100.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img vicpbios.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img vid1bios.com 0:
	cpmcp -f ibmpc-514ss cpmtest.img vid2bios.com 0:
	cpmcp -f ibmpc-514ss cpmtest.img curstest.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img getch.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img test.txt 0:
	cpmls -F -f ibmpc-514ss cpmtest.img 0:*.*

dostest.img: vid1bios.com curstest.com dosbase.img test.txt
	cp dosbase.img dostest.img
	mcopy -i dostest.img vid1bios.com  ::VID1BIOS.COM
	mcopy -i dostest.img vid1bios.com  ::VI.COM
	mcopy -i dostest.img curstest.com  ::CURSTEST.COM
	mcopy -i dostest.img test.txt  ::TEST.TXT
	mdir -i dostest.img ::

# --------------------------------------------------------------------
# Binary zip
# --------------------------------------------------------------------
dist: vi-bin.zip

vi-bin.zip: vicp52.cmd vicp100.cmd vicpbios.cmd vid1bios.com vid2bios.com
	rm -f vi-bin.zip
	zip vi-bin.zip vicp52.cmd vicp100.cmd vicpbios.cmd vid1bios.com vid2bios.com

# --------------------------------------------------------------------
# Utility
# --------------------------------------------------------------------
clean:
	$(RM) cpmtest.img *.o gitver.h \
	vicp52.cmd vicp100.cmd vicpbios.cmd \
	vid1bios.com vid2bios.com \
	curstest.cmd curstest.com asmtest.com getch.cmd \
	vi-bin.zip

test: cpm86test

dos11test: dostest.img
	./dos11

cpm86test: cpmtest.img
	./cpm86

ccpm86test: cpmtest.img
	./ccpm86

cdos41test: cpmtest.img
	./cdos41

dosplustest: cpmtest.img
	./dosplus
