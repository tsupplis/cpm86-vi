# STevie/vi for CP/M-86 and PC-DOS — Design Notes

This document describes the internal architecture of this port of STevie
(a small vi clone by Tim Thompson) to CP/M-86 and PC-DOS 1.1/2.0, compiled
with Aztec C86 v4.10d. It also tracks the ANSI-C modernization pass done
on the codebase: what changed, what was deliberately left alone, and what
remains as follow-up work.

## Overview

The editor is a single-buffer, single-file, full-screen vi clone. The
whole file being edited lives in one contiguous heap block (`Filemem` ..
`Filemax`), and the screen is rendered by diffing a "next" frame against
a "real" (currently displayed) frame buffer, only emitting the bytes that
changed. There is no gap buffer, undo tree, or multi-file support — undo
is a single-level "redo the opposite editop" scheme built from small
fixed-size command buffers (`Undobuff`, `Redobuff`, `Insbuff`, `Replbuf`).

Keyboard input and screen output are the only genuinely platform-specific
parts of the program (`edit.c`'s `getch()`/`bioskey()`/`keyready()`, and
all of `window.c`). Everything else (`cmdline.c`, `linefunc.c`,
`misccmds.c`, `normal.c`, `hexchars.c`, `help.c`, `main.c`'s screen-diff
logic) is portable C operating purely on the in-memory file buffer.

## Build Variants & Portability Matrix

One source tree produces 5 binaries, selected entirely by preprocessor
macros passed on the compiler command line (see `Makefile`). `edit.c` and
`window.c` are compiled once per variant; every other `.c` file is
compiled once and shared (`SHARED_OBJS` in the Makefile) across all 5.

| Binary            | OS               | Screen/keyboard technique         | Macros |
|-------------------|------------------|------------------------------------|--------|
| `vicp52.cmd`      | CP/M-86          | VT-52 escape sequences             | `__CPM86__ __VTCMD__ __VT52__` |
| `vicp100.cmd`     | CP/M-86          | VT-100/ANSI escape sequences       | `__CPM86__ __VTCMD__ __VT100__` |
| `vicpbios.cmd`    | CP/M-86          | Direct PC BIOS (INT 10h/16h)       | `__CPM86__ __PCBIOS__` |
| `vid1bios.com`    | PC-DOS 1.1       | Direct PC BIOS (INT 10h/16h)       | `__PCDOS__=11 __PCBIOS__` |
| `vid2bios.com`    | PC-DOS 2.0       | Direct PC BIOS (INT 10h/16h)       | `__PCDOS__=20 __PCBIOS__` |

Macro meanings:
- `__CPM86__` — target OS is CP/M-86 (vs. PC-DOS). Affects console raw
  mode setup (`ioctl(... TIOCSETP ...)`), screen row count (24 vs 25),
  and the `":v"` version string / usage message wording.
- `__PCDOS__` — set to `11` or `20` for PC-DOS 1.1 / 2.0. Only meaningful
  together with `__PCBIOS__` (there's no VTCMD DOS build).
- `__VTCMD__` — screen/keyboard driven by printing terminal escape codes
  and reading via BDOS function 6, instead of touching the BIOS directly.
- `__VT52__` / `__VT100__` — which escape-code dialect `__VTCMD__` emits.
- `__PCBIOS__` — screen/keyboard driven directly via `INT 10h` (video)
  and `INT 16h` (keyboard) through Aztec C86 inline `#asm`/`#endasm`
  blocks (kept in separate `.asm` files, `#include`d into the function
  body: `windgoto.asm`, `windcurs.asm`, `windclr.asm`, `windputc.asm` in
  `window.c`; `bioskey.asm`, `keyready.asm` in `edit.c`).

None of this is portable beyond 8086 real-mode CP/M-86/DOS — the `#asm`
blocks are Aztec C86-specific syntax and assume near/tiny memory model
(a `char *` and an `int` are both 16 bits and freely interchangeable,
which is relied on implicitly in a few places — see Portability Notes).

## Data Model & Global State

All cross-file shared state is declared `extern` in `stevie.h` and
defined (without `extern`) in `main.c`. These use the original
PascalCase naming and were **deliberately left unrenamed** in this pass
(see Deferred/Future Work) — renaming them touches every file.

- **File buffer**: `Filemem`/`Filemax`/`Fileend` — a single fixed-size
  heap block (`FILELENG` = 24000 bytes, hardcoded) holding the whole
  file as raw bytes; `Fileend` is the current logical end, `Filemax` the
  allocated end. `Curschar` points at the cursor's byte. There is no gap
  buffer — insert/delete shift the tail of the buffer up/down a byte at
  a time (see Efficiency Findings Log).
- **Screen buffers**: `Realscreen` (what's on-screen) and `Nextscreen`
  (what should be on-screen), each `Rows*Columns` bytes, diffed by
  `nexttoscreen()` in `main.c` so only changed cells are redrawn.
  `Topchar`/`Botchar` bound the visible slice of the file buffer.
- **Editor state**: `State` (one of `NORMAL`/`INSERT`/`APPEND`/
  `REPLACE`/... from `stevie.h`), `Prenum` (pending numeric count prefix
  for a command), `Cursrow`/`Curscol`/`Cursvcol` (screen vs. virtual
  cursor column, the latter differing on lines that wrap or contain
  tabs).
- **Undo/redo**: single-level, command-replay based. `Undobuff`/
  `Redobuff`/`Insbuff`/`Replbuf` (1024-byte fixed buffers) hold a tiny
  "mini-script" of characters that, if fed back through the normal-mode
  or insert-mode interpreters, reproduce or reverse the last change.
  `Uncurschar` is the cursor position to restore before replaying.
- **`struct charinfo { char ch_size; char *ch_str; }`** (`stevie.h`) —
  one entry per byte value 0-255 (table in `hexchars.c`), giving the
  on-screen width and (for non-printable bytes) the placeholder string
  like `[041]`/`[x29]`/`[ 41]`, switchable at runtime between octal/hex/
  decimal via `:set oct|hex|dec`.

## Module Reference

Each entry: responsibility, ANSI conversion notes, and any file-specific
naming/portability points. All 9 `.c` files + `stevie.h` are fully
converted from K&R to ANSI C prototypes; see Progress details below for
the exact rationale on visibility (`static`) decisions.

### stevie.h
Central shared header: mode/state constants, `struct charinfo`, the
`extern` global declarations (PascalCase, unrenamed — deferred), and now
a full set of ANSI prototypes for every cross-file function, grouped by
the `.c` file that defines them (`/* cmdline.c */`, `/* linefunc.c */`,
etc.). The old blanket K&R forward-declarations
(`char *malloc(), *strchr(), *strsave(), *alloc(), *strcpy();`) were
removed function-by-function as each file was converted; `strchr()`
alone still uses the old empty-parens (unspecified-args) form — see
Deferred/Future Work.

### cmdline.c
Parses and dispatches `:` command-line input, `/`/`?` search prefixes,
and status-line messages. `badcmd()`, `gotocmd()`, `writeit()` are
file-private (`static`); `readcmdline()`, `message()`, `clearlastmess()`,
`filemess()` are the public surface. Efficiency: the `:` command
dispatcher is a long sequential `strcmp()` chain (see Efficiency
Findings Log — rated Low, not yet applied).

### linefunc.c
Line/column navigation (`nextline`, `prevline`, `coladvance`) and
search (`ssearch`/`fwdsearch`/`bcksearch`, file-private; `dosearch`/
`repsearch` public), plus the allocator helpers `alloc()` (private) and
`strsave()` (public). `fwdsearch`/`bcksearch` are a naive O(n·m)
character-by-character scan (Efficiency Findings Log — Medium, deferred).

### misccmds.c
Character/line insert-delete primitives (`inschar`, `insstr`, `appchar`
(private), `delchar`, `deleol`, `delword`, `delline`), yank/put
(`yankline`, `putline`), and small utilities (`issepchar`, `cntlines`,
`fileinfo`, `gotoline`, `opencmd`). Also defines a **hand-rolled
`strchr()`** — see Deferred/Future Work, this shadows (and, per
empirical testing, actually conflicts with) Aztec's real `<string.h>`
`strchr`. The yank buffer's file-scope globals were renamed
`Savedline`/`Savednum`/`Savedcount` → `savedline`/`savednum`/
`savedcount` and made `static` (they were previously accidentally
external-linkage globals never declared in `stevie.h` — a latent
visibility bug, now fixed; confirmed via grep that nothing outside this
file ever referenced them). Efficiency: `inschar`/`appchar`/`delchar`
are O(n) shifts of the whole rest-of-file per call, so multi-character
operations (`insstr`, `putline`, `delline`) are O(n²) (High, deferred —
true fix is a gap buffer, out of scope for this pass).

### normal.c
The normal-mode command interpreter (`normal()`, public) and its two
helpers `tabinout()` (indent/outdent) and `startinsert()`, both
file-private. `resetundo()` is public (called from `misccmds.c` too).
This file already used angle-bracket `<ctype.h>`/`<stdio.h>` before this
pass — the sole exception noted in the initial survey.

### hexchars.c
The 256-entry `chars[]` table (non-printable byte display), and
`octchars()`/`hexchars()`/`decchars()`/`hextoint()`, all public, all
already ANSI-shaped once given real prototypes (pure data + straight
loops, no K&R quirks beyond the missing prototypes themselves).

### help.c
`help()` (public, shows the built-in key reference screen) and
`helpstr()` (private helper that writes a string via `windputc()`).

### main.c
Program entry point (`int main(int argc, char **argv)`), global state
definitions, the screen-diff renderer (`filetonext()`/`nexttoscreen()`,
both private, driven through public `updatescreen()`), and low-level
file I/O (`readfile()`, public) and command-replay plumbing (`stuffin()`,
`addtobuff()`, `vgetc()`/`vpeekc()`/`anyinput()`, all public).
**`addtobuff()` arg-count fix**: originally `char c1..c6` with callers
passing 2-4 real chars plus a `NULL` terminator, relying on K&R's lack
of argument-count checking — this cannot compile under a strict ANSI
prototype. Fixed by widening the params to `int c1..c6` (matching the
`ctype.h`-style convention already used for `issepchar`) and updating
every call site (in `misccmds.c` and `normal.c`) to always pass exactly
6 arguments, padding unused trailing slots with `0` — behaviorally
identical (the function already stops at the first `'\0'`/`0`), now
ANSI-legal. Efficiency: `readfile()` inserts each character by shifting
the rest of the buffer down one byte at a time — O(n²) for loading a
file of length n (High, deferred).

### edit.c
The main keyboard-read/dispatch loop (`edit()`, public) and its
platform-specific input layer: `getch()` has two independent bodies
(`__PCBIOS__`: polls `INT 16h` via `bioskey()`/`keyready()`, both
file-private, plus a 1-byte `pending` lookahead for synthesized escape
sequences; `__VTCMD__`: reads via BDOS function 6 into a 64-byte ring
buffer). `windgetc()` is the OS-independent public wrapper.
`donormal()`, `insertchar()`, `gethexchar()`, `scrolldown()` are
file-private helpers; `getout()`, `cursupdate()`, `oneright()`,
`oneleft()`, `beginline()`, `oneup()`, `onedown()` are public (called
from `normal.c`/`linefunc.c`). The `#if defined(__PCBIOS__)` block's
`bioskey()`/`keyready()` bodies are raw `#include`d `.asm` files with no
parameters, so converting them to `static int name(void)` carries no
`[bp+N]` stack-frame risk. Efficiency: `cursupdate()` re-scans from
`Topchar` to `Curschar` on every keystroke to track the virtual column
(Medium, deferred — see Efficiency Findings Log).

### window.c
All screen/keyboard I/O, in two independent implementations gated by
`#if defined(__VTCMD__)` / `#if defined(__PCBIOS__)` (never both). Both
define the same public surface: `windinit`, `windgoto`, `windexit`,
`windcursor`, `windcolor`, `windcolorreset`, `windclear`, `windstr`,
`windputc`, `windrefresh`, `beep`, plus `viversion()`/`windusage()`
(shared, outside either `#if`) and, PCBIOS-only, `windrefreshcursor()`
(re-asserts the cursor position between polls, fighting CP/M-86's
background clock/status updates — see edit.c's `getch()`).
`windclreol()` is defined in both blocks but has **no external
callers anywhere in the codebase**; made `static` in both. The
`__PCBIOS__` implementation's `windgoto(r,c)`, `windcursor(on)`, and
`windputc(c)` use raw `#asm` blocks (`windgoto.asm`/`windcurs.asm`/
`windputc.asm`) addressing their C parameters via `[bp+4]`/`[bp+6]` —
each already had a defensive `int dummy;` local (pre-existing, not
added by this pass) to force Aztec to establish a stack frame; the
ANSI signature conversion changes only the declaration syntax, not the
calling convention, so these offsets are unaffected (verified by reading
each `.asm` file). `windclr.asm` and `windputc.asm` reference the
file-scope statics `cur_row`/`cur_col`/`clearbottom` by Aztec's
`name_`-suffix convention (e.g. `cur_row_`) — these are already
`lower_snake_case`, so no naming-pass rename was needed (and none of
these statics should ever be renamed without also updating the `.asm`
files that hardcode the `_`-suffixed symbol name).

## Efficiency Findings Log

Per the agreed process, these are **documented, not applied**, except
where noted. Ratings: Low (safe, local, quick win) / Medium (real but
non-trivial, still fairly contained) / High (structural, e.g. would need
a gap buffer or index rebuild — significant redesign risk).

| Location | Issue | Rating | Status |
|---|---|---|---|
| `cmdline.c` `readcmdline()` | Long sequential `strcmp()` chain to dispatch `:` commands | Low | Identified, not applied — awaiting go-ahead |
| `linefunc.c` `fwdsearch()`/`bcksearch()` | Naive O(n·m) character-by-character search, no early-exit optimizations (e.g. Boyer-Moore) | Medium | Documented only |
| `misccmds.c` `inschar`/`appchar`/`delchar` (and everything built on them: `insstr`, `putline`, `delline`) | O(n) shift of the rest of the file buffer per single-character edit; O(n²) for multi-char operations | High | Documented only — true fix is a gap buffer, a significant architecture change |
| `main.c` `readfile()` | O(n²) file load — shifts the whole in-memory buffer down for every character read | High | Documented only |
| `edit.c` `cursupdate()` | Re-scans from `Topchar` to `Curschar` every keystroke to recompute the virtual column | Medium | Documented only |
| `window.c` PCBIOS `windrefreshcursor()`/`windputc()` | Re-issues an `INT 10h` cursor-position call very frequently (by design, to fight a background clock update) | Low (intentional tradeoff) | Not a bug — documented for awareness only |

## Portability Notes

- **Toolchain**: Aztec C86 v4.10d (1988), a pre-ANSI K&R-era compiler.
  It accepts ANSI-style function prototypes (verified empirically across
  this whole pass) but its standard library is much smaller than a
  modern one — notably, no `strchr` conflict was found for `strcmp`/
  `strcpy`/`strlen`/`malloc`/`free`/`atoi`, but `misccmds.c` had to hand-
  roll its own `strchr()` (see Deferred/Future Work); adding
  `<stdlib.h>`'s `malloc` prototype alongside a mismatched old-style
  hand-declaration (`char *malloc()` vs. the real `void *malloc(unsigned)`
  once one existed) produced a hard "multiply defined symbol" error —
  return-type mismatches between two visible declarations of the same
  libc function are not tolerated, even though two *compatible*
  declarations (e.g. two empty-parens ones) are fine.
- **Memory model**: near/tiny (16-bit pointers, `char *` and `int` are
  both 16-bit). The codebase implicitly relies on this in a few spots
  (e.g. historically, functions returning heap pointers with no visible
  declaration would still "work" via implicit-`int` return, a pattern we
  removed as we added real prototypes, but the compatibility exists as
  the reason it never broke before this pass).
  do NOT assume this generalizes to any other platform/compiler.
- **`#asm`/`#endasm` blocks**: Aztec-specific inline assembly syntax, not
  portable to any modern compiler (GCC/Clang/MSVC all use different
  inline-asm dialects). Concentrated in `window.c` (`__PCBIOS__` block)
  and `edit.c` (`__PCBIOS__` `bioskey()`/`keyready()`). Functions with
  `#asm` bodies that read parameters via `[bp+N]` require Aztec to
  establish a stack frame, which requires at least one C local variable
  in the function (a bare `#asm`-only body with no params/locals is
  treated as a leaf function with no frame) — already handled via a
  defensive `int dummy;` local in the 3 affected `window.c` functions.
- **Fixed-size buffers**: `FILELENG` (24000 bytes) for the whole file,
  and 1024-byte `Undobuff`/`Redobuff`/`Insbuff`/`Replbuf` — all
  compile-time constants, not configurable, a direct consequence of the
  target's limited RAM.
- **Row count**: 24 rows under CP/M-86 (`__CPM86__`), 25 under plain
  PC-DOS (`__PCDOS__`) — a real behavioral difference between variants,
  not just cosmetic (`window.c`'s `windinit()`).

## Deferred / Future Work

Explicitly out of scope for this pass, called out here for a follow-up:

1. **Global PascalCase rename** — `State`, `Rows`, `Curschar`,
   `Filemem`, etc. (all `extern` globals declared in `stevie.h`) were
   left unrenamed. Renaming to `lower_snake_case` would touch every one
   of the 9 `.c` files; deferred due to ripple-effect scope, not
   difficulty.
2. **Public (non-`static`) function naming** — left as-is for the same
   reason (e.g. `windgoto`, `readcmdline`); only file-private (`static`)
   functions were renamed/normalized where needed in this pass (most
   were already lower_snake_case, so in practice almost nothing changed
   here — see per-file notes above for the handful of exceptions like
   `Savedline` -> `savedline`).
3. **`misccmds.c`'s hand-rolled `strchr()`** — shadows the real
   `strchr()` that Aztec's own `<string.h>` provides (confirmed by the
   `#include <string.h>` + custom-definition conflict encountered and
   reverted during this pass). Options for a follow-up: (a) delete the
   custom implementation and rely on `<string.h>`'s real one (needs a
   behavioral equivalence check — the custom one returns `NULL` for "not
   found", matches standard semantics as far as tested), or (b) rename
   the custom function (e.g. `vfindchr`) to stop shadowing the standard
   name and make the override explicit. Either way, `stevie.h`'s
   `strchr()` prototype currently has to stay in the old empty-parens
   (unspecified-args) form to avoid a "multiply defined symbol" error;
   giving it a real `(char *, int)` prototype requires resolving this
   first.
4. **Efficiency — structural fixes** — see the High-rated rows in the
   Efficiency Findings Log (`readfile()`, `inschar`/`appchar`/`delchar`
   and everything built on them). A real fix means a gap buffer or
   piece-table representation for the file, which is a significant
   rewrite of `main.c`/`misccmds.c`/`linefunc.c`'s shared assumption
   that the file is one contiguous array — worth a dedicated follow-up
   effort, not a quick patch.
5. **Efficiency — Low-risk items** — the `cmdline.c` sequential
   `strcmp()` dispatch chain was identified but not yet applied; still
   awaiting explicit go-ahead per the agreed process.

## Verification Record

- Baseline (start of this pass): codebase was 100% K&R, zero ANSI
  prototypes, but already built cleanly under `aztec42_cc`.
- After every file's conversion, the affected `.o` target(s) were
  rebuilt in isolation (`make clean && make <file>.o [...]`) and
  checked for zero new warnings/errors.
- Final state: `make clean && make` (full rebuild of all 5 binaries —
  `vicp52.cmd`, `vicp100.cmd`, `vicpbios.cmd`, `vid1bios.com`,
  `vid2bios.com`) succeeds with **zero warnings and zero errors**.
- Functional/manual smoke-testing in the emulator (emu2/PCE) is the
  user's responsibility per the agreed process, not automated here.
