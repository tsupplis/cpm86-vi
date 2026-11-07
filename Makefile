# --------------------------------------------------------------------
# Toolchain & Configuration
# --------------------------------------------------------------------
CC            = aztec43_acc
LD            = aztec43_acc
CMDMOD        = pcdev_cmdmod
RM            = rm -f

CFLAGS        = -I. -squeeze
CPM86_LDFLAGS = -target=cpm86
DOS11_LDFLAGS = -target=dos1
DOS20_LDFLAGS = -target=dos2

GIT_VERSION  := $(shell git describe --tags --always --dirty 2>/dev/null || echo unknown)

# --------------------------------------------------------------------
# Object Lists
# --------------------------------------------------------------------
SHARED_OBJS = \
	help.o     \
	hexchars.o \
	linefunc.o \
	main.o     \
	misccmds.o \
	normal.o   \
	yankmem.o  \
	yankcopy.o

TINY_OBJS = \
	helpd1.o   \
	hexd1.o    \
	lined1.o   \
	maind1.o   \
	miscd1.o   \
	normd1.o   \
	yankmd1.o  \
	cmdd1.o    \
	saved1.o   \
	edttiny.o  \
	wintiny.o  \
	keytiny.o

# --------------------------------------------------------------------
# Top-level Targets
# --------------------------------------------------------------------
.PHONY: all dist clean test dos11test cpm86test ccpm86test cdos41test dosplustest FORCE

all: vicp52.cmd vicp100.cmd vicpbios.cmd \
     vid1bios.com vid1bios.exe vid2bios.exe \
     cpmtest.img

# --------------------------------------------------------------------
# Binary Link Targets
# --------------------------------------------------------------------
vicp52.cmd: $(SHARED_OBJS) yankcp.o cmdline.o savecp.o edtcp52.o wincp52.o keycp.o keyos.o os.o
	$(LD) $(CPM86_LDFLAGS) -o $@ $(filter %.o,$^)
	$(CMDMOD) -t DATA -n f000 -m 10000 $@ 1
	$(CMDMOD) -t EXTRA -n 10000 -m 10000 $@ 2

vicp100.cmd: $(SHARED_OBJS) yankcp.o cmdline.o savecp.o edtcp100.o wincp100.o keycp.o keyos.o os.o
	$(LD) $(CPM86_LDFLAGS) -o $@ $(filter %.o,$^)
	$(CMDMOD) -t DATA -n f000 -m 10000 $@ 1
	$(CMDMOD) -t EXTRA -n 10000 -m 10000 $@ 2

# CP/M-86 binary using the PC BIOS window/keyboard implementation
vicpbios.cmd: $(SHARED_OBJS) yankcp.o cmdline.o savecp.o edtcpbio.o wincpbio.o keycp.o keyos.o os.o
	$(LD) $(CPM86_LDFLAGS) -o $@ $(filter %.o,$^)
	$(CMDMOD) -t DATA -n f000 -m 10000 $@ 1
	$(CMDMOD) -t EXTRA -n 10000 -m 10000 $@ 2

vicp52.cmd vicp100.cmd vicpbios.cmd: Makefile

vid1bios.com: $(TINY_OBJS) yankcopy.o yankd1c.o
	$(LD) $(DOS11_LDFLAGS) -o $@ $^

vid1bios.exe: $(SHARED_OBJS) yankd11.o cmddos.o savedos.o edtd1bio.o wind1bio.o keydos.o
	$(LD) $(DOS11_LDFLAGS) -o $@ $^

vid2bios.exe: $(SHARED_OBJS) yankd20.o cmddos.o savedos.o edtd2bio.o wind2bio.o keydos.o
	$(LD) $(DOS20_LDFLAGS) -o $@ $^

# Scratch diagnostics for BIOS cursor positioning
curstest.cmd: curstest.o wincpbio.o keycp.o keyos.o os.o
	$(LD) $(CPM86_LDFLAGS) -o $@ $(filter %.o,$^)

curstest.com: curstestdos.o wind1bio.o keydos.o
	$(LD) $(DOS11_LDFLAGS) -o $@ $^

# --------------------------------------------------------------------
# Disk Images & Distribution
# --------------------------------------------------------------------
cpmtest.img: vicp52.cmd vicp100.cmd vicpbios.cmd cpmbase.img test.txt \
    vid1bios.com vid2bios.exe
	cp cpmbase.img cpmtest.img
	cpmrm -f ibmpc-514ss cpmtest.img 0:*.cmd
	cpmrm -f ibmpc-514ss cpmtest.img 0:test.txt
	cpmcp -f ibmpc-514ss cpmtest.img vicp52.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img vicpbios.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img vid1bios.com 0:
	cpmcp -f ibmpc-514ss cpmtest.img vid2bios.exe 0:
	cpmcp -f ibmpc-514ss cpmtest.img test.txt 0:
	cpmls -F -f ibmpc-514ss cpmtest.img 0:*.*

dostest.img: vid1bios.com vid1bios.exe vid2bios.exe dosbase.img test.txt
	cp dosbase.img dostest.img
	mcopy -i dostest.img vid1bios.com  ::VID1BIOS.COM
	mcopy -i dostest.img vid1bios.com  ::VI.COM
	mcopy -i dostest.img vid1bios.exe  ::VID1BIOS.EXE
	mcopy -i dostest.img vid1bios.exe  ::VI.EXE
	mcopy -i dostest.img vid2bios.exe  ::VID2BIOS.EXE
	mcopy -i dostest.img test.txt  ::TEST.TXT
	mdir -i dostest.img ::

dist: vi.zip

vi.zip: vicp52.cmd vicp100.cmd vicpbios.cmd vid1bios.com vid1bios.exe vid2bios.exe
	rm -f vi.zip
	zip vi.zip vicp52.cmd vicp100.cmd vicpbios.cmd vid1bios.com vid1bios.exe vid2bios.exe

cpmtest.img dostest.img vi.zip: Makefile

# --------------------------------------------------------------------
# Git Version Header
# --------------------------------------------------------------------
gitver.h: FORCE
	@echo '#define GIT_VERSION "$(GIT_VERSION)"' > gitver.h.$$$$.tmp && \
	(cmp -s gitver.h.$$$$.tmp gitver.h 2>/dev/null && $(RM) gitver.h.$$$$.tmp || mv gitver.h.$$$$.tmp gitver.h)

FORCE:

# --------------------------------------------------------------------
# Compilation Rules: Shared C Objects
# --------------------------------------------------------------------
help.o: help.c
	$(CC) $(CFLAGS) -c -o $@ help.c

hexchars.o: hexchars.c
	$(CC) $(CFLAGS) -c -o $@ hexchars.c

linefunc.o: linefunc.c
	$(CC) $(CFLAGS) -c -o $@ linefunc.c

main.o: main.c
	$(CC) $(CFLAGS) -c -o $@ main.c

misccmds.o: misccmds.c
	$(CC) $(CFLAGS) -c -o $@ misccmds.c

normal.o: normal.c
	$(CC) $(CFLAGS) -c -o $@ normal.c

# --------------------------------------------------------------------
# Compilation Rules: Terminal & BIOS edit/window Variants
# --------------------------------------------------------------------
edtcp52.o: edit.c
	$(CC) $(CFLAGS) -target=cpm86 -D__VTCMD__ -D__VT52__ -c -o $@ $<

wincp52.o: window.c gitver.h
	$(CC) $(CFLAGS) -target=cpm86 -D__VTCMD__ -D__VT52__ -c -o $@ $<

edtcp100.o: edit.c
	$(CC) $(CFLAGS) -target=cpm86 -D__VTCMD__ -D__VT100__ -c -o $@ $<

wincp100.o: window.c gitver.h
	$(CC) $(CFLAGS) -target=cpm86 -D__VTCMD__ -D__VT100__ -c -o $@ $<

edtcpbio.o: edit.c
	$(CC) $(CFLAGS) -target=cpm86 -D__PCBIOS__ -c -o $@ $<

wincpbio.o: window.c gitver.h
	$(CC) $(CFLAGS) -target=cpm86 -D__PCBIOS__ -c -o $@ $<

edtd1bio.o: edit.c
	$(CC) $(CFLAGS) -target=dos1 -c -o $@ $<

wind1bio.o: window.c gitver.h
	$(CC) $(CFLAGS) -target=dos1 -c -o $@ $<

edtd2bio.o: edit.c
	$(CC) $(CFLAGS) -target=dos2 -c -o $@ $<

wind2bio.o: window.c gitver.h
	$(CC) $(CFLAGS) -target=dos2 -c -o $@ $<

# --------------------------------------------------------------------
# Compilation Rules: Keyboard, OS & I/O Adapters
# --------------------------------------------------------------------
keycp.o: keyboard.c keyboard.h keyos.h
	$(CC) $(CFLAGS) -target=cpm86 -c -o $@ keyboard.c

keydos.o: keyboard.c keyboard.h
	$(CC) $(CFLAGS) -c -o $@ keyboard.c

keyos.o: keyos.c keyos.h
	$(CC) $(CFLAGS) -c -o $@ keyos.c

os.o: os.asm
	$(CC) $(CFLAGS) -c -o $@ $<

# Save policy must match the linked runtime; never share the CP/M command object.
cmdline.o: cmdline.c save.h
	$(CC) $(CFLAGS) -target=cpm86 -c -o $@ cmdline.c

cmddos.o: cmdline.c save.h
	$(CC) $(CFLAGS) -c -o $@ cmdline.c

savecp.o: save.c save.h
	$(CC) $(CFLAGS) -target=cpm86 -c -o $@ save.c

savedos.o: save.c save.h
	$(CC) $(CFLAGS) -c -o $@ save.c

# --------------------------------------------------------------------
# Compilation Rules: Yank Memory & Buffer Routines
# --------------------------------------------------------------------
yankmem.o: yankmem.c yankmem.h
	$(CC) $(CFLAGS) -c -o $@ yankmem.c

yankcopy.o yankcp.o yankd11.o yankd20.o: %.o: %.asm
	$(CC) $(CFLAGS) -c -o $@ $<

yankd1c.o: yankd1c.asm yankd11.asm
	$(CC) $(CFLAGS) -c -o $@ yankd1c.asm

# --------------------------------------------------------------------
# Compilation Rules: Diagnostic Objects
# --------------------------------------------------------------------
curstest.o: curstest.c
	$(CC) $(CFLAGS) -c -o $@ curstest.c

curstestdos.o: curstest.c
	$(CC) $(CFLAGS) -target=dos1 -c -o $@ $^

# --------------------------------------------------------------------
# Compilation Rules: Tiny DOS 1 COM Objects
# --------------------------------------------------------------------
helpd1.o: help.c
hexd1.o: hexchars.c
lined1.o: linefunc.c
maind1.o: main.c
miscd1.o: misccmds.c
normd1.o: normal.c
yankmd1.o: yankmem.c
cmdd1.o: cmdline.c
saved1.o: save.c
edttiny.o: edit.c
wintiny.o: window.c
keytiny.o: keyboard.c

# Tiny C objects never share compilation with the full-featured formats.
$(TINY_OBJS): stevie.h keyboard.h yankmem.h save.h Makefile
	$(CC) $(CFLAGS) -DVI_TINY -target=dos1 -c -o $@ $(filter %.c,$^)

wintiny.o: gitver.h windrun.asm

# --------------------------------------------------------------------
# Header Dependencies
# --------------------------------------------------------------------
main.o edtcp52.o edtcp100.o edtcpbio.o edtd1bio.o edtd2bio.o \
wincp52.o wincp100.o wincpbio.o wind1bio.o wind2bio.o: keyboard.h

main.o: save.h

$(SHARED_OBJS) cmdline.o cmddos.o edtcp52.o edtcp100.o edtcpbio.o edtd1bio.o edtd2bio.o \
wincp52.o wincp100.o wincpbio.o wind1bio.o wind2bio.o: stevie.h

wincp52.o wincp100.o wincpbio.o: keyos.h
wincpbio.o wind1bio.o wind2bio.o: windrun.asm
main.o misccmds.o: yankmem.h

# --------------------------------------------------------------------
# Utility & Cleaning
# --------------------------------------------------------------------
clean:
	$(RM) cpmtest.img *.o gitver.h \
	vicp52.cmd vicp100.cmd vicpbios.cmd \
	vid1bios.com vid1bios.exe vid2bios.exe \
	curstest.cmd curstest.com \
	vi.zip

# --------------------------------------------------------------------
# Emulator Execution Targets
# --------------------------------------------------------------------
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

# --------------------------------------------------------------------
# Test Suite Targets
# --------------------------------------------------------------------
.PHONY: test-keys test-regression test-scroll test-save test-save-runtime \
        test-save-pce test-editor-state test-buffer-runtime test-dos1-pce \
        test-display-pce test-display-compat test-vt-output test-vt-pce \
        test-perf-pce test-characters test-capacity-runtime test-io-runtime \
        test-yank-lengths test-navigation-runtime test-navigation-perf-pce \
        test-yank-runtime test-yank-pce

test-keys:
	python3 -B test/test_keys.py

test-regression:
	python3 -B test/regression.py

test-scroll:
	python3 test/test_scroll.py

test-save:
	python3 test/test_save.py

test-save-runtime:
	sh test/saveruntime

test-save-pce:
	python3 test/test_save_pce.py

test-editor-state:
	python3 test/test_editor_state.py

test-buffer-runtime:
	python3 test/test_buffer_runtime.py

test-dos1-pce:
	python3 -B test/test_dos1_pce.py

test-display-pce:
	python3 -B test/test_display_pce.py

test-display-compat:
	python3 -B test/test_display_pce.py --compat-only

test-vt-output:
	python3 -B test/test_vt_output.py

test-vt-pce:
	python3 -B test/test_vt_pce.py

test-perf-pce:
	python3 -B test/test_perf_pce.py

test-characters:
	python3 -B test/test_characters.py

test-capacity-runtime:
	python3 -B test/test_capacity_runtime.py

test-io-runtime:
	python3 -B test/test_io_runtime.py

test-yank-lengths:
	python3 -B test/test_yank_lengths.py

test-navigation-runtime:
	python3 -B test/test_navigation_runtime.py

test-navigation-perf-pce:
	python3 -B test/test_navigation_perf.py

test-yank-runtime:
	python3 test/test_yank_runtime.py

test-yank-pce:
	python3 test/test_yank_pce.py
