# Vi Editor for CP/M-86 and DOS 1.1

A port of **STevie** (ST Editor for VI Enthusiasts, by Tim Thompson) to
**CP/M-86** and **MS-DOS 1.1** on IBM-PC compatible hardware, compiled with
**Aztec C v4.2**.

![vi running under CP/M-86](images/vi.png)

---

## Why vi on CP/M-86 (and DOS 1.1)?

CP/M-86 ships with `ed` — a line-oriented editor inherited from DEC OSes.
While powerful for scripting, `ed` is notoriously difficult to use
interactively: you work blind, with no visible context of the file, no
cursor, and a command syntax that takes time to learn. DOS 1.1 doesn't even
have `ed` and predates ANSI.SYS, so it has essentially no interactive
screen editor at all.

There is no lightweight **screen-mode** editor for CP/M-86, and DOS 1.1's
bare BIOS environment makes porting one there even less common.
Most available options are either proprietary, CP/M-80 only, or require
a specific hardware terminal or heavier. This port of STevie fills that gap:
a familiar, full-screen vi experience that runs on standard IBM-PC
hardware, either through a VT-52/VT-100 terminal emulator on CP/M-86, or
directly against the PC BIOS on CP/M-86 or bare DOS 1.1 — no terminal
emulator, no ANSI.SYS required.

---

## Background

STevie was originally written by Tim Thompson for the Atari 520 ST and later
ported to various CP/M-80 machines. This version targets **CP/M-86** and
**MS-DOS 1.1** on IBM-PC hardware. Screen/keyboard I/O is selected at compile
time along two independent axes — only `window.c` and `edit.c` differ
between builds; all other objects are shared:

- **OS** (`__CPM86__`): uses BDOS for console I/O (raw keystrokes via BDOS
  function 6, `sgtty`/`ioctl` for raw mode) — vs. plain DOS 1.1, which has
  none of that and talks to the hardware directly.
- **Screen/keyboard technique** (`__VTCMD__` + `__VT52__`/`__VT100__` vs.
  `__PCBIOS__`): escape-sequence output through a terminal (VT-52 or
  VT-100/ANSI) vs. direct PC BIOS calls (`INT 10h` for the screen, `INT 16h`
  for the keyboard) — no terminal, no ANSI.SYS.

These two axes are independent: `vibios.cmd` combines `__CPM86__` with
`__PCBIOS__` (BIOS I/O, but still a CP/M-86 `.cmd` binary using the BDOS
runtime for file I/O), while `vidos.com` is `__PCBIOS__` alone (a plain DOS
1.1 `.com` binary).

---

## Features

- Full vi normal-mode command set (movement, insert, append, delete, yank,
  put, undo, search, `:` command line)
- Two keyboard input paths, selected at compile time:
  - **BDOS function 6** (`__CPM86__` + `__VTCMD__` builds) — a 64-byte ring
    buffer so fast typists don't lose keystrokes
  - **Direct PC BIOS** `INT 16h` (`__PCBIOS__` builds) — polled rather than
    blocking, so the cursor position can be re-asserted while waiting (see
    below)
- Composite / extended key support: arrow keys, Home, End, PgUp, PgDn
- Four build variants:

| Binary | Screen/keyboard | Build flags |
|--------|-----------------|-------------|
| `vivt52.cmd`  | VT-52 escape sequences (CP/M-86)      | `-D__VTCMD__ -D__VT52__` |
| `vivt100.cmd` | ANSI / VT-100 escape sequences (CP/M-86) | `-D__VTCMD__ -D__VT100__` |
| `vibios.cmd`  | Direct PC BIOS, CP/M-86 `.cmd` binary | `-D__PCBIOS__` |
| `vidos.com`   | Direct PC BIOS, plain DOS 1.1 `.com` binary | `-D__PCBIOS__` |

---

## Building

Requires the Aztec C 86 cross-development toolchain
(`aztec42_cc`, `aztec42_link`, `aztec42_sqz`) on the PATH, available from
[tsupplis/cpm86-crossdev](https://github.com/tsupplis/cpm86-crossdev),
and **cpmtools** (`cpmcp`, `cpmrm`, `cpmls`) for CP/M-86 disk image
management (DOS 1.1 images use `mtools`' `mcopy`/`mdir` instead).

```sh
# Build all four variants
make

# Build and package as a zip for distribution
make dist          # produces vi-bin.zip

# Copy CP/M-86 binaries to a CP/M-86 test disk image
make cpmtest.img

# Copy the DOS binary to a DOS 1.1 test disk image
make dostest.img

# Run under the PCE CP/M-86 emulator (or emu2 from cpm86-crossdev)
make cpm86test
```

Each build embeds the current `git describe` output (or `unknown` outside a
git checkout) as the version shown by the `:v` command; see `gitver.h`
(generated, not checked in) and `viversion()` in `window.c`.

---

## Source layout

| File | Purpose |
|------|---------|
| `window.c` | All platform-specific screen I/O — cursor, clear, colour, and the `:v` version string |
| `edit.c` | Insert / append / replace mode, and all platform-specific raw keyboard input (`getch()`/`windgetc()`) |
| `main.c` | Startup, screen/file allocation, update loop |
| `normal.c` | Normal-mode command dispatch |
| `cmdline.c` | `:` command-line parser (`:w`, `:q`, `:e`, `:v`, …) |
| `linefunc.c` | Line navigation helpers |
| `misccmds.c` | Miscellaneous vi commands |
| `help.c` | Built-in help text |
| `hexchars.c` | Hex / octal character display tables |
| `stevie.h` | Shared externs and defines |

### `edit.c` and `window.c` build sections

```
# edit.c: raw keyboard input
#if defined(__PCBIOS__)      ← INT 16h, polled, re-asserts cursor position
#elif defined(__CPM86__)     ← BDOS function 6, ring buffer

# edit.c: escape-sequence parsing (arrow/Home/PgUp keys)
#if defined(__VT52__) || defined(__PCBIOS__)  ← lone ESC + letter
#elif defined(__VT100__)                      ← ESC '[' + letter

# window.c: screen output
#if defined(__VTCMD__)
    #if defined(__VT52__)    ← VT-52 escape sequences
    #elif defined(__VT100__) ← ANSI / VT-100 escape sequences
#elif defined(__PCBIOS__)    ← PC BIOS INT 10h calls; Rows=24 if __CPM86__
                                is also defined (matches the VTCMD builds),
                                Rows=25 otherwise (plain DOS)
```

---

## Command Reference

### Movement

| Command | Action |
|---------|--------|
| `h` `j` `k` `l` | Left / down / up / right |
| `b` | Back one word |
| `w` | Forward one word |
| `^` or `0` | Beginning of line |
| `$` | End of line |
| `[#]G` | Go to line `#` (no count = last line) |
| `^F` | Forward one screen |
| `^B` | Back one screen |
| `^D` | Down 10 lines |
| `^U` | Up 10 lines |
| `^G` | Show file info |
| `^L` | Redraw screen |

### Insert / Replace

| Command | Action |
|---------|--------|
| `i` | Insert before cursor |
| `a` | Append after cursor |
| `o` | Open new line below, enter insert mode |
| `r <c>` | Replace single character under cursor with `<c>` |
| `R` | Enter replace mode (overwrite); `ESC` to exit |
| `ESC` | Exit insert or replace mode, return to normal |

### Delete

| Command | Action |
|---------|--------|
| `x` | Delete character under cursor |
| `[#]dd` | Delete `#` lines (default 1) |
| `dw` | Delete word |
| `D` or `d$` | Delete to end of line |

### Change

| Command | Action |
|---------|--------|
| `cc` | Change entire line (delete line, enter insert) |
| `cw` | Change word |
| `C` or `c$` | Change to end of line |

### Yank & Put

| Command | Action |
|---------|--------|
| `[#]yy` | Yank `#` lines into buffer (default 1) |
| `p` | Put yanked/deleted lines after current line |
| `P` | Put yanked/deleted lines before current line |

### Miscellaneous

| Command | Action |
|---------|--------|
| `u` | Undo last change |
| `.` | Redo last insert or delete |
| `J` | Join current line with next |
| `[#]>>` | Indent `#` lines right by one tab (default 1) |
| `[#]<<` | Indent `#` lines left by one tab (default 1) |
| `H` | Show built-in help screen |

### Search

| Command | Action |
|---------|--------|
| `/str` | Search forward for `str` |
| `?str` | Search backward for `str` |
| `n` | Repeat last search |
| `//` or `??` | Repeat last search (command-line form) |

### `:` Command line

| Command | Action |
|---------|--------|
| `:w` | Write file |
| `:w <file>` | Write to `<file>` |
| `:wq` or `:x` | Write and quit |
| `:q` | Quit (refuses if unsaved changes) |
| `:q!` | Quit unconditionally |
| `:e <file>` | Edit `<file>` |
| `:e!` | Re-read current file, discarding changes |
| `:r <file>` | Read `<file>` and insert after current line |
| `:f` | Show current filename and size |
| `:f <name>` | Rename current file (in-editor) |
| `:.=` | Show current line number and character offset |
| `:$=` | Show total number of lines |
| `:set oct` | Display non-printable characters in octal |
| `:set hex` | Display non-printable characters in hex |
| `:set dec` | Display non-printable characters in decimal |
| `:v` | Show the build variant and version (git describe) |
| `:h` or `:help` | Show built-in help screen |

---

## Terminal key sequences

The arrow keys, Home, PgUp, PgDn and End send different byte sequences
depending on the terminal type.

### VT-52 (`vivt52.cmd`)

VT-52 cursor keys send a two-byte sequence: `ESC` followed by a single letter.

| Key | Sequence | vi action |
|-----|----------|-----------|
| ↑ Up    | `ESC A` | `k` — move up one line |
| ↓ Down  | `ESC B` | `j` — move down one line |
| → Right | `ESC C` | `l` — move right one char |
| ← Left  | `ESC D` | `h` — move left one char |
| Home    | `ESC H` | `0` — beginning of line |
| PgUp    | `ESC I` | `^B` — back one screen |
| End     | `^Z` (0x1A) | `$` — end of line |
| PgDn    | `^J` (0x0A) | `^F` — forward one screen |

### VT-100 / ANSI (`vivt100.cmd`)

VT-100 cursor keys send a three-byte sequence: `ESC [` followed by a letter.

| Key | Sequence | vi action |
|-----|----------|-----------|
| ↑ Up    | `ESC [ A` | `k` — move up one line |
| ↓ Down  | `ESC [ B` | `j` — move down one line |
| → Right | `ESC [ C` | `l` — move right one char |
| ← Left  | `ESC [ D` | `h` — move left one char |
| Home    | `ESC [ H` | `0` — beginning of line |
| PgUp    | `ESC [ I` | `^B` — back one screen |
| End     | `^Z` (0x1A) | `$` — end of line |
| PgDn    | `^J` (0x0A) | `^F` — forward one screen |

> End and PgDn arrive as bare control codes with no ESC prefix on both
> terminal types, as sent by the IBM-PC CP/M-86 BDOS keyboard handler.

### PC BIOS (`vibios.cmd`, `vidos.com`)

There's no real terminal here — `getch()` reads `INT 16h` scan codes
directly and synthesizes the same lone `ESC` + letter sequences as VT-52,
so the two builds share the same escape-parsing code in `edit.c`.

| Key | BIOS scan code | Synthesized sequence | vi action |
|-----|-----------------|----------------------|-----------|
| ↑ Up    | `0x48` | `ESC A` | `k` — move up one line |
| ↓ Down  | `0x50` | `ESC B` | `j` — move down one line |
| → Right | `0x4D` | `ESC C` | `l` — move right one char |
| ← Left  | `0x4B` | `ESC D` | `h` — move left one char |
| Home    | `0x47` | `ESC H` | `0` — beginning of line |
| PgUp    | `0x49` | `ESC I` | `^B` — back one screen |
| PgDn    | `0x51` | `^J` (0x0A) | `^F` — forward one screen |
| End     | `0x4F` | `^Z` (0x1A) | `$` — end of line |
| Insert  | `0x52` | `ESC L` | (not yet used in vi) |
| Delete  | `0x53` | `\x7F` | (not yet used in vi) |

---

## Requirements

- **Aztec C 86 v4.2** cross-compiler (`aztec42_cc`, `aztec42_link`, `aztec42_sqz`) —
  from [tsupplis/cpm86-crossdev](https://github.com/tsupplis/cpm86-crossdev)
- **cpmtools** (`cpmcp`, `cpmrm`, `cpmls`) to manage CP/M-86 disk images
- **mtools** (`mcopy`, `mdir`) to manage the DOS 1.1 disk image (`dostest.img`)
- **zip** for `make dist`
- **git** (optional) — used to embed a version string via `:v`; falls back
  to `unknown` if not run from a git checkout
- **CP/M-86 1.1**, from [tsupplis/cpm86-kernel](https://github.com/tsupplis/cpm86-kernel),
  for the `vivt52.cmd`/`vivt100.cmd`/`vibios.cmd` binaries
- **PC-DOS 1.1**, from [tsupplis/pcdos11-hacking](https://github.com/tsupplis/pcdos11-hacking),
  for the `vidos.com` binary
- An emulator for testing — optional; two suitable options:
  - **PCE** CP/M-86 emulator (`cpm86`), for the CP/M-86 binaries
  - **emu2** — runs both CP/M-86 `.cmd` and DOS `.com` binaries locally,
    bundled with [tsupplis/cpm86-crossdev](https://github.com/tsupplis/cpm86-crossdev)
    (originally from [johnsonjh/emu2-cpm86](https://github.com/johnsonjh/emu2-cpm86))

---

## Known issues / TODO

See [TODO.md](TODO.md).

---

## Credits

- **Tim Thompson** — original STevie for the Atari ST
- **Jon Bradbury** — CP/M-80 port for the Philips P2000C
- This CP/M-86 port adds IBM-PC keyboard handling, dual terminal builds,
  and a cross-compilation Makefile
