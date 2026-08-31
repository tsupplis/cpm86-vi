CC     = aztec42_cc
STRIP  = aztec42_sqz
LD     = aztec42_link
LDFLAGS = -lc86

# Flags common to both CP/M-86 builds
CPM_CFLAGS = -D__CPM86__

# Objects shared by both terminal builds (window.o excluded)
SHARED_OBJS = \
	cmdline.o \
	edit.o    \
	help.o    \
	hexchars.o \
	linefunc.o \
	main.o    \
	misccmds.o \
	normal.o

# --------------------------------------------------------------------
# Top-level targets
# --------------------------------------------------------------------
all: vivt52.cmd vivt100.cmd cpmtest.img

# --------------------------------------------------------------------
# Link targets
# --------------------------------------------------------------------
vivt52.cmd: $(SHARED_OBJS) winvt52.o
	$(LD) -o $@ $^ $(LDFLAGS)

vivt100.cmd: $(SHARED_OBJS) winvt100.o
	$(LD) -o $@ $^ $(LDFLAGS)

# --------------------------------------------------------------------
# window.c – two variants
# --------------------------------------------------------------------
winvt52.o: window.c
	$(CC) $(CPM_CFLAGS) -D__VT52__ -o $@ window.c
	$(STRIP) $@

winvt100.o: window.c
	$(CC) $(CPM_CFLAGS) -D_VT100_ -o $@ window.c
	$(STRIP) $@

# --------------------------------------------------------------------
# Shared object rules
# --------------------------------------------------------------------
cmdline.o: cmdline.c
	$(CC) $(CPM_CFLAGS) -o $@ cmdline.c
	$(STRIP) $@

edit.o: edit.c
	$(CC) $(CPM_CFLAGS) -o $@ edit.c
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

cpmtest.img: vivt52.cmd vivt100.cmd
	cpmrm -f ibmpc-514ss cpmtest.img 0:*.cmd
	cpmrm -f ibmpc-514ss cpmtest.img 0:test.txt
	cpmcp -f ibmpc-514ss cpmtest.img vivt52.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img vivt100.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img test.txt 0:
	cpmls -F -f ibmpc-514ss cpmtest.img 0:*.*

# --------------------------------------------------------------------
# Binary zip
# --------------------------------------------------------------------
dist: vi-bin.zip

vi-bin.zip: vivt52.cmd vivt100.cmd
	rm -f vi-bin.zip
	zip vi-bin.zip vivt52.cmd vivt100.cmd

# --------------------------------------------------------------------
# Utility
# --------------------------------------------------------------------
clean:
	$(RM) *.o vivt52.cmd vivt100.cmd vi-bin.zip

test: cpmtest.img
	./cpm86
