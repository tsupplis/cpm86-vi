# Vi Editor for CP/M-86

A port of **STevie** (ST Editor for VI Enthusiasts, by Tim Thompson) to
**CP/M-86** on IBM-PC compatible hardware, compiled with **Aztec C v4.2**.

![vi running under CP/M-86](images/vi.png)

---

## Why vi on CP/M-86?

CP/M-86 ships with `ed` — a line-oriented editor inherited from Unix.
While powerful for scripting, `ed` is notoriously difficult to use
interactively: you work blind, with no visible context of the file, no
cursor, and a command syntax that takes time to learn.

There is no lightweight **screen-mode** editor for CP/M-86.
Most available options are either proprietary, CP/M-80 only, or require
a specific hardware terminal or heavier. This port of STevie fills that gap:
a familiar, full-screen vi experience that runs on standard IBM-PC
CP/M-86 hardware with nothing more than a VT-52 or VT-100 compatible
terminal emulator.

---

## Background

STevie was originally written by Tim Thompson for the Atari 520 ST and later
ported to various CP/M-80 machines. This version targets **CP/M-86** on
IBM-PC hardware. The terminal type is selected at compile time — only
`window.c` and `edit.c` differ between builds; all other objects are shared.

---

## Features

- Full vi normal-mode command set (movement, insert, append, delete, yank,
  put, undo, search, `:` command line)
- Keyboard input via **BDOS function 6** — reads raw key codes with a 64-byte
  ring buffer so fast typists don't lose keystrokes
- Composite / extended key support: arrow keys, Home, End, PgUp, PgDn
- Two terminal builds:

| Binary | Terminal | `window.c` flags |
|--------|----------|------------------|
| `vivt52.cmd`  | VT-52 escape sequences      | `-D__CPM86__ -D__VT52__` |
| `vivt100.cmd` | ANSI / VT-100 escape sequences | `-D__CPM86__ -D_VT100_` |

---

## Building

Requires the Aztec C 86 cross-development toolchain
(`aztec42_cc`, `aztec42_link`, `aztec42_sqz`) on the PATH, and
**cpmtools** (`cpmcp`, `cpmrm`, `cpmls`) for disk image management.

```sh
# Build both terminal variants
make

# Build and package as a zip for distribution
make dist          # produces vi-bin.zip

# Copy binaries to CP/M-86 test disk image
make cpmtest.img

# Run under the PCE CP/M-86 emulator
make test
```

---

## Source layout

| File | Purpose |
|------|---------|
| `window.c` | All platform-specific I/O — screen, cursor, keyboard |
| `main.c` | Startup, screen/file allocation, update loop |
| `edit.c` | Insert / append / replace mode |
| `normal.c` | Normal-mode command dispatch |
| `cmdline.c` | `:` command-line parser (`:w`, `:q`, `:e`, …) |
| `linefunc.c` | Line navigation helpers |
| `misccmds.c` | Miscellaneous vi commands |
| `help.c` | Built-in help text |
| `hexchars.c` | Hex / octal character display tables |
| `stevie.h` | Shared externs and defines |

### `window.c` build sections

```
#if defined(__CPM86__)
    #if defined(__VT52__)   ← VT-52 escape sequences
    #elif defined(_VT100_)  ← ANSI / VT-100 escape sequences
```

---

## Key mappings

The arrow keys, Home, PgUp, PgDn and End send different byte sequences
depending on the terminal type. The table below shows what each terminal
sends and how the editor interprets it.

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

---

## Requirements

- **Aztec C 86 v4.2** cross-compiler (`aztec42_cc`, `aztec42_link`, `aztec42_sqz`)
- **cpmtools** (`cpmcp`, `cpmrm`, `cpmls`) to manage CP/M disk images
- **zip** for `make dist`
- **PCE** CP/M-86 emulator (`cpm86`) for `make test` — optional

---

## Credits

- **Tim Thompson** — original STevie for the Atari ST
- **Jon Bradbury** — CP/M-80 port for the Philips P2000C
- This CP/M-86 port adds IBM-PC keyboard handling, dual terminal builds,
  and a cross-compilation Makefile
