# Vi Editor for CP/M-86 and PC-DOS 1.1/MS-DOS 1.25

A port of **STevie** (ST Editor for VI Enthusiasts, by Tim Thompson) to
**CP/M-86** and **MS-DOS 1.1** on IBM-PC compatible hardware, compiled with
**Aztec C v4.2**.

![vi running under CP/M-86](images/vi.png)

---

## Why vi on CP/M-86 (and PC-DOS 1.1/MS-DOS 1.25)?

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
directly against the PC BIOS on CP/M-86 or bare PC-DOS 1.1 — no terminal
emulator, no ANSI.SYS required.

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
- Five build variants:

| Binary | Screen/keyboard | Build flags |
|--------|-----------------|-------------|
| `vicp52.cmd`    | VT-52 escape sequences (CP/M-86)         | `-D__CPM86__ -D__VTCMD__ -D__VT52__` |
| `vicp100.cmd`   | ANSI / VT-100 escape sequences (CP/M-86) | `-D__CPM86__ -D__VTCMD__ -D__VT100__` |
| `vicpbios.cmd`  | Direct PC BIOS, CP/M-86 `.cmd` binary    | `-D__CPM86__ -D__PCBIOS__` |
| `vid1bios.com`  | Direct PC BIOS, PC-DOS 1.1 `.com` binary | `-D__PCDOS__=11 -D__PCBIOS__` |
| `vid2bios.com`  | Direct PC BIOS, PC-DOS 2.0 `.com` binary | `-D__PCDOS__=20 -D__PCBIOS__` |

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

# Copy the DOS binary to a PC-DOS 1.1 test disk image
make dostest.img

# Run under the PCE CP/M-86 emulator (or emu2 from cpm86-crossdev)
make cpm86test
```

Each build embeds the current `git describe` output (or `unknown` outside a
git checkout) as the version shown by the `:v` command; see `gitver.h`
(generated, not checked in) and `viversion()` in `window.c`.


## Command Reference

![vi help running under CP/M-86](images/help.png)

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
| `O` | Open new line above, enter insert mode |
| `r <c>` | Replace single character under cursor with `<c>` |
| `R` | Enter replace mode (overwrite); `ESC` to exit |
| `^V <c>` | Insert next character literally (e.g. `^V Tab` inserts a real tab) |
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
| `[#]~` | Toggle case of `#` characters from cursor (default 1) |
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
| `:<N>` | Go to line `N` (clamps to last line if `N` exceeds the file) |

---

## Terminal key sequences

The arrow keys, Home, PgUp, PgDn and End send different byte sequences
depending on the terminal type.

### VT-52 (`vicp52.cmd`)

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

### VT-100 / ANSI (`vicp100.cmd`)

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

### PC BIOS (`vicpbios.cmd`, `vidosX.com`)

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
    (from [johnsonjh/emu2-cpm86](https://github.com/johnsonjh/emu2-cpm86))

---

## OS compatibility matrix

| Binary | CP/M-86 1.1 |  CCP/M-86 3.1 | CDOS 3.2 | CDOS 4.1 | DOS Plus 1.2 | PC-DOS 1.1 | DOS ≥ 2.0 | Emu2 |
|--------|-------------|-----------|-------------|---------------------|--------------|------------|-----------|------|
| `vicpbios.cmd`             | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | ✅ |
| `vicp52.cmd`               | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | ✅(1) |
| `vicp100.cmd`              | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | ✅(1) |
| `vid1bios.com`             | — | — | ✅ | ✅ | ✅ | ✅ | ✅| ✅(2)|
| `vid2bios.com`             | — | — | — | ✅  | ✅ | — | ✅ | ✅(2) |

1. keyboard navigation keys need to be configured
2. 25 lines terminal needed

## Concurrent CP/M keyboard

On concurrent BDOS >= 3.0, all CP/M builds use BDOS input for navigation keys
and restore normal function-key expansion on exit. Legacy CP/M and DOS input
paths are preserved. VI includes its own small OS helpers and needs no utility
library. The BIOS build still uses BIOS display calls; prefer VT52 for native
Concurrent CP/M consoles.

## Viewport scrolling

Up/Down scroll only as far as needed to keep the cursor visible. Page and
half-page movement use the document area, reserving the last row for status
and commands, including with wrapped lines and at EOF.

Run `make test-keys test-scroll` for keyboard, OS-gating and viewport checks.
On DOS Plus, CP/M builds reset the text mode on close to restore the XIOS
scrolling origin and cursor state.

--

## Companion projects

| Project | Description |
|---------|-------------|
| [cpm86-kernel](https://github.com/tsupplis/cpm86-kernel)     | CP/M-86 1.1 distribution rebuilt from patched and reconstituted sources |
| [ccpm86-kernel](https://github.com/tsupplis/ccpm86-kernel)         | CCP/M-86 3.1 distribution rebuilt from patched and reconstituted sources |
| [cdos41-kernel](https://github.com/tsupplis/cdos41-kernel)         | Concurrent DOS 4.1 distribution rebuilt from patched and reconstituted sources |
| [cpm86-crossdev](https://github.com/tsupplis/cpm86-crossdev) | Unix CP/M-86 cross development project (compilers, emulation and tools) |
| [cpm86-hacking](https://github.com/tsupplis/cpm86-hacking)   | CP/M-86 miscellaneous tools and PCE emulator helpers |
| [cpm86-cmdtools](https://github.com/tsupplis/cpm86-cmdtools) | CP/M-86 `.cmd` file manipulation tools |
| [cpm86-ports](https://github.com/tsupplis/cpm86-ports)       | CP/M-86 application ports in C and assembler |
| [cpm86-vi](https://github.com/tsupplis/cpm86-vi)             | STevie vi port for CP/M-86 and PC-DOS |
| [cpm86-msbasic](https://github.com/tsupplis/cpm86-msbasic)   | A recreaction of msbasic-86 for CP/M-86 and PC-DOS 1.1 from gwbasic sources |
| [cpm86-menu](https://github.com/tsupplis/cpm86-menu)   | A submit replacement and a menu system for submit orchestration for CP/M-86 1.1 |
| [cpm86-make](https://github.com/tsupplis/cpm86-make)   | A simple submit based make tool for CP/M-86 |
| [pcdos11-hacking](https://github.com/tsupplis/pcdos11-hacking) | PC-DOS 1.1 distribution, tools and notes |

--

## License

The whole repository is as public domain. [License](LICENSE.md) unless specified otherwise in a subdirectory.



## Saving files

The command-line and save objects are built separately for DOS and CP/M.
DOS 1.1 and DOS 2 use the Aztec runtime's `ftruncate` after flushing output,
with the number of physical bytes actually written (including inserted CRs).
DOS text does not need a trailing Ctrl-Z. Binary reads preserve embedded 1Ah.
A failed write, flush, size update, or close leaves the editor marked modified.
An in-place save is not crash-atomic and may already have overwritten data
when an error is reported.

CP/M save policy uses the complete AX returned by BDOS function 12:

| Identity | Save policy |
| --- | --- |
| 1031h: CP/M-86 Plus | BDOS 99 record truncation after closing |
| 1431h: Concurrent CP/M 3.1 | BDOS 99 record truncation after closing |
| 1041h: DOS Plus | Record truncation plus used-byte LRBC metadata |
| Classic CP/M-86 and other identities | Temporary-file replacement |

No broad version threshold is assumed. Network variants and unknown releases
use replacement. BDOS 99 identifies the last retained record, not a byte count.
Empty binary saves use replacement even on native-truncate systems.
Text output has a Ctrl-Z terminator and deliberate record padding; binary
padding is zero. DOS Plus binary reads honor its exact byte-count metadata.
Other CP/M binary files remain rounded to 128-byte records.

Replacement files (`VI000000.TMP` onward) and backup names (`VI000000.BAK`
onward) are created exclusively in the target drive/user area. The completed
temporary file is closed before the original is renamed. Failed installation
attempts restore the original name; if restoration also fails, both recovery
files remain and the error reports their names. Original read-only files are
rejected. Replacement does not promise preservation of timestamps or other
extended file metadata. No failed open is followed by a destructive create.
The original user area is restored on every returning path.

Validation:

```
make test-save          # host files, mocked BDOS, injected I/O/rename failures
make test-save-runtime  # actual Aztec DOS 1.1, DOS 2 and classic CP/M libraries
make test-save-pce      # private DOS 1.1 and DOS Plus images under PCE
```

`CROSSDEV` selects the crossdev checkout; `SAVE_EMULATOR` can select a corrected
emu2. Otherwise the runtime test builds the crossdev DOS 1.1 emulator fixture
in a temporary directory. PCE testing needs the DOS 1.1 checkout at
`~/Projects/DOS/pcdos11-hacking` (override `DOS11_SOURCE`) and this checkout's
DOS Plus image/ROM files. Original images are never modified.
The CP/M Plus and Concurrent 3.1 identities are covered by mocked BDOS tests;
real-kernel native truncation is validated on DOS Plus, not those two kernels.

Reference: Digital Research's CP/M-86 Plus Programmer's Guide, functions 12,
30 and 99, and the supplied DOS Plus 1.2 kernel exercised under PCE.
