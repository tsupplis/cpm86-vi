# Vi Editor for CP/M-86

A port of **STevie** (ST Editor for VI Enthusiasts, by Tim Thompson) to
**CP/M-86** on IBM-PC compatible hardware, compiled with **Aztec C v4.2**.

![vi running under CP/M-86](images/vi.png)

---

## Background

STevie was originally written by Tim Thompson for the Atari 520 ST and later
ported to various CP/M-80 machines. This version targets **CP/M-86** on
IBM-PC hardware. The terminal type is selected at compile time via `CFLAGS`.

---

## Features

- Full vi normal-mode command set (movement, insert, append, delete, yank, put, undo, search, `:` command line)
- Keyboard input via **BDOS function 6** — reads raw key codes with a 64-byte
  ring buffer so fast typists don't lose keystrokes
- Composite / extended key support: arrow keys, Home, End, PgUp, PgDn
- Terminal type selected at compile time:

| `CFLAGS` | Terminal |
|----------|----------|
| `-D__CPM86__ -D__VT52__` | VT-52 escape sequences (default) |
| `-D__CPM86__ -D_VT100_`  | ANSI / VT-100 escape sequences |

---

## Building

The build host requires the Aztec C 86 cross-development toolchain
(`aztec42_cc`, `aztec42_link`, `aztec42_sqz`) to be on the PATH.

```sh
make
```

This produces `vi.cmd` and `getch.cmd`, and updates `cpmtest.img`.

To change the terminal type, edit `CFLAGS` in the Makefile before building:

```makefile
CFLAGS=-D__CPM86__ -D__VT52__   # VT-52  (default)
CFLAGS=-D__CPM86__ -D_VT100_    # VT-100 / ANSI
```

To run under the PCE CP/M-86 emulator:

```sh
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

---

## Requirements

- **Aztec C 86 v4.2** cross-compiler (`aztec42_cc`, `aztec42_link`, `aztec42_sqz`)
- **cpmtools** (`cpmcp`, `cpmrm`, `cpmls`) to manage CP/M disk images
- **PCE** CP/M-86 emulator (`cpm86`) for testing — optional

---

## Credits

- **Tim Thompson** — original STevie for the Atari ST
- **Jon Bradbury** — CP/M-80 port for the Philips P2000C
- This CP/M-86 port adds IBM-PC keyboard handling and a cross-compilation Makefile
