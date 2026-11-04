CC     = aztec42_cc
STRIP  = aztec42_sqz
AS     = aztec42_as
LD     = aztec42_link
CMDMOD = pcdev_cmdmod
CPM86_LDFLAGS = -lc86
DOS11_LDFLAGS = -ld11
DOS20_LDFLAGS = -lc
RM=rm -f

# Flags common to both CP/M-86 builds
CFLAGS = -I. +F +0
DOS_CFLAGS = -I. +F +0 -D__PCBIOS__
PCBIOS_CFLAGS = -I. +F +0 -D__PCBIOS__

GIT_VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo unknown)

# Objects shared by both terminal builds (window.o and edit.o excluded)
SHARED_OBJS = \
	help.o     \
	hexchars.o \
	linefunc.o \
	main.o     \
	misccmds.o \
	normal.o   \
	yankmem.o  \
	yankcopy.o

# --------------------------------------------------------------------
# Top-level targets
# --------------------------------------------------------------------
all: vicp52.cmd vicp100.cmd vicpbios.cmd \
 vid1bios.com vid2bios.exe \
 cpmtest.img 

# --------------------------------------------------------------------
# Link targets
# --------------------------------------------------------------------
vicp52.cmd: $(SHARED_OBJS) yankcp.o cmdline.o savecp.o edtcp52.o wincp52.o keycp.o keyos.o os.o
	printf '%s\n' '-o $@ $(filter %.o,$^)' > $(basename $@).lnk
	$(LD) -f $(basename $@).lnk $(CPM86_LDFLAGS)
	$(CMDMOD) -t DATA -n f000 -m 10000 $@ 1
	$(CMDMOD) -t EXTRA -n 10000 -m 10000 $@ 2
	$(RM) $(basename $@).lnk

vicp100.cmd: $(SHARED_OBJS) yankcp.o cmdline.o savecp.o edtcp100.o wincp100.o keycp.o keyos.o os.o
	printf '%s\n' '-o $@ $(filter %.o,$^)' > $(basename $@).lnk
	$(LD) -f $(basename $@).lnk $(CPM86_LDFLAGS)
	$(CMDMOD) -t DATA -n f000 -m 10000 $@ 1
	$(CMDMOD) -t EXTRA -n 10000 -m 10000 $@ 2
	$(RM) $(basename $@).lnk

vid1bios.com: $(filter-out main.o,$(SHARED_OBJS)) maind1.o yankd11.o cmddos.o savedos.o edtd1bio.o wind1bio.o keydos.o
	printf '%s\n' '-o $@ $^' > $(basename $@).lnk
	$(LD) -f $(basename $@).lnk $(DOS11_LDFLAGS)
	$(RM) $(basename $@).lnk

vid2bios.exe: $(SHARED_OBJS) yankd20.o cmddos.o savedos.o edtd2bio.o wind2bio.o keydos.o
	printf '%s\n' '-o $@ $^' > $(basename $@).lnk
	$(LD) -f $(basename $@).lnk $(DOS20_LDFLAGS)
	$(RM) $(basename $@).lnk

# CP/M-86 binary using the PC BIOS window/keyboard implementation (no VT
# escape codes, no BDOS console I/O) instead of the DOS API.
vicpbios.cmd: $(SHARED_OBJS) yankcp.o cmdline.o savecp.o edtcpbio.o wincpbio.o keycp.o keyos.o os.o
	printf '%s\n' '-o $@ $(filter %.o,$^)' > $(basename $@).lnk
	$(LD) -f $(basename $@).lnk $(CPM86_LDFLAGS)
	$(CMDMOD) -t DATA -n f000 -m 10000 $@ 1
	$(CMDMOD) -t EXTRA -n 10000 -m 10000 $@ 2
	$(RM) $(basename $@).lnk

vicp52.cmd vicp100.cmd vicpbios.cmd: Makefile

# --------------------------------------------------------------------
# Scratch program: isolate windgoto/windputc from all of vi's own
# screen/timing logic, to check raw BIOS cursor positioning under CP/M-86.
# --------------------------------------------------------------------

curstest.cmd: curstest.o wincpbio.o keycp.o keyos.o os.o
	printf '%s\n' '-o $@ $(filter %.o,$^)' > $(basename $@).lnk
	$(LD) -f $(basename $@).lnk $(CPM86_LDFLAGS)
	$(RM) $(basename $@).lnk

curstest.o: curstest.c
	$(CC) $(CFLAGS) -o $@ curstest.c
	$(STRIP) $@

# Same diagnostic, linked for plain DOS, for direct comparison.
curstest.com: curstestdos.o wind1bio.o keydos.o
	printf '%s\n' '-o $@ $^' > $(basename $@).lnk
	$(LD) -f $(basename $@).lnk $(DOS11_LDFLAGS)
	$(RM) $(basename $@).lnk

curstestdos.o: curstest.c
	$(CC) $(CFLAGS) -D__PCBIOS__ -D__PCDOS__==11 -o $@ $^
	$(STRIP) $@

# --------------------------------------------------------------------
# edit.c and window.c – two variants each
# --------------------------------------------------------------------

edtcp52.o: edit.c
	$(CC) $(CFLAGS) -D__CPM86__ -D__VTCMD__ -D__VT52__ -c -o $@ $<
	$(STRIP) $@

wincp52.o: window.c gitver.h
	$(CC) $(CFLAGS) -D__CPM86__ -D__VTCMD__ -D__VT52__ -c -o $@ $<
	$(STRIP) $@

edtcp100.o: edit.c
	$(CC) $(CFLAGS) -D__CPM86__ -D__VTCMD__ -D__VT100__ -c -o $@ $<
	$(STRIP) $@

wincp100.o: window.c gitver.h
	$(CC) $(CFLAGS) -D__CPM86__ -D__VTCMD__ -D__VT100__ -c -o $@ $<
	$(STRIP) $@

edtd1bio.o: edit.c
	$(CC) $(DOS_CFLAGS) -D__PCDOS__=11 -D__PCBIOS__ -c -o $@ $<
	$(STRIP) $@

wind1bio.o: window.c gitver.h
	$(CC) $(CFLAGS) -D__PCDOS__=11 -D__PCBIOS__ -c -o $@ $<
	$(STRIP) $@

edtd2bio.o: edit.c
	$(CC) $(CFLAGS) -D__PCDOS__=20 -D__PCBIOS__ -c -o $@ $<
	$(STRIP) $@

wind2bio.o: window.c gitver.h
	$(CC) $(CFLAGS) -D__PCDOS__=20 -D__PCBIOS__ -c -o $@ $<
	$(STRIP) $@

edtcpbio.o: edit.c
	$(CC) $(CFLAGS) -D__CPM86__ -D__PCBIOS__ -c -o $@ $<
	$(STRIP) $@

wincpbio.o: window.c gitver.h
	$(CC) $(CFLAGS) -D__CPM86__ -D__PCBIOS__ -c -o $@ $<
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
	$(CC) $(CFLAGS) -D__CPM86__ -o $@ cmdline.c
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

maind1.o: main.c stevie.h keyboard.h yankmem.h save.h
	$(CC) $(CFLAGS) -D__PCDOS__=11 -o $@ $<
	$(STRIP) $@

misccmds.o: misccmds.c
	$(CC) $(CFLAGS) -o $@ misccmds.c
	$(STRIP) $@

normal.o: normal.c
	$(CC) $(CFLAGS) -o $@ normal.c
	$(STRIP) $@

cpmtest.img: vicp52.cmd vicp100.cmd vicpbios.cmd cpmbase.img test.txt \
    vid2bios.exe
	cp cpmbase.img cpmtest.img
	cpmrm -f ibmpc-514ss cpmtest.img 0:*.cmd
	cpmrm -f ibmpc-514ss cpmtest.img 0:test.txt
	cpmcp -f ibmpc-514ss cpmtest.img vicp52.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img vicp100.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img vicpbios.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img vid2bios.exe 0:
	cpmcp -f ibmpc-514ss cpmtest.img test.txt 0:
	cpmls -F -f ibmpc-514ss cpmtest.img 0:*.*

dostest.img: vid1bios.com vid2bios.exe dosbase.img test.txt
	cp dosbase.img dostest.img
	mcopy -i dostest.img vid1bios.com  ::VID1BIOS.COM
	mcopy -i dostest.img vid1bios.com  ::VI.COM
	mcopy -i dostest.img vid2bios.exe  ::VID2BIOS.EXE
	mcopy -i dostest.img test.txt  ::TEST.TXT
	mdir -i dostest.img ::

# --------------------------------------------------------------------
# Binary zip
# --------------------------------------------------------------------
dist: vi.zip

vi.zip: vicp52.cmd vicp100.cmd vicpbios.cmd vid1bios.com vid2bios.exe
	rm -f vi.zip
	zip vi.zip vicp52.cmd vicp100.cmd vicpbios.cmd vid1bios.com vid2bios.exe

# --------------------------------------------------------------------
# Utility
# --------------------------------------------------------------------
clean:
	$(RM) cpmtest.img *.o gitver.h \
	vicp52.cmd vicp100.cmd vicpbios.cmd \
	vid1bios.com vid2bios.com vid2bios.exe \
	vi.zip

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

main.o edtcp52.o edtcp100.o edtcpbio.o edtd1bio.o edtd2bio.o wincp52.o wincp100.o wincpbio.o wind1bio.o wind2bio.o: keyboard.h
$(SHARED_OBJS) cmdline.o cmddos.o edtcp52.o edtcp100.o edtcpbio.o edtd1bio.o edtd2bio.o wincp52.o wincp100.o wincpbio.o wind1bio.o wind2bio.o: stevie.h
wincp52.o wincp100.o wincpbio.o: keyos.h

keycp.o: keyboard.c keyboard.h keyos.h
	$(CC) $(CFLAGS) -D__CPM86__ -o $@ keyboard.c
	$(STRIP) $@

keydos.o: keyboard.c keyboard.h
	$(CC) $(CFLAGS) -o $@ keyboard.c
	$(STRIP) $@

keyos.o: keyos.c keyos.h
	$(CC) $(CFLAGS) -o $@ keyos.c
	$(STRIP) $@

os.o: os.asm
	$(AS) $<
	$(STRIP) $@

yankmem.o: yankmem.c yankmem.h
	$(CC) $(CFLAGS) -o $@ yankmem.c
	$(STRIP) $@

yankcopy.o yankcp.o yankd11.o yankd20.o: %.o: %.asm
	$(AS) $<
	$(STRIP) $@

main.o misccmds.o: yankmem.h

.PHONY: test-keys
test-keys:
	python3 testkeys.py

.PHONY: test-scroll
test-scroll:
	python3 test/test_scroll.py

# Save policy must match the linked runtime; never share the CP/M command object.
cmddos.o: cmdline.c save.h
	$(CC) $(CFLAGS) -o $@ cmdline.c
	$(STRIP) $@
savecp.o: save.c save.h
	$(CC) $(CFLAGS) -D__CPM86__ -o $@ save.c
	$(STRIP) $@
savedos.o: save.c save.h
	$(CC) $(CFLAGS) -o $@ save.c
	$(STRIP) $@
cmdline.o: save.h

.PHONY: test-save test-save-runtime test-save-pce
test-save:
	python3 test/test_save.py
test-save-runtime:
	sh test/saveruntime
test-save-pce:
	python3 test/test_save_pce.py
main.o: save.h

.PHONY: test-editor-state
test-editor-state:
	python3 test/test_editor_state.py

.PHONY: test-buffer-runtime
test-buffer-runtime:
	python3 test/test_buffer_runtime.py

.PHONY: test-capacity-runtime
test-capacity-runtime:
	python3 -B test/test_capacity_runtime.py

.PHONY: test-yank-runtime test-yank-pce
test-yank-runtime:
	python3 test/test_yank_runtime.py
test-yank-pce:
	python3 test/test_yank_pce.py
