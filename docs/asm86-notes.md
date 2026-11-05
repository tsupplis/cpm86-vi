# Aztec C86 v4.10d inline assembly rules (verified empirically via asmtest.c)

Toolchain: aztec42_cc/aztec42_link (cpm86-crossdev), run under emu2.

- Syntax: `#asm` / `#endasm` blocks (not `asm(...)`).
- Function return value: leave result in AX before `#endasm` (or `return var;`
  after the block) — no special syntax needed, works like any K&R function.
- Variable access from within `#asm`: ONLY works for **file-scope `static`**
  (or global) variables, referenced by `name_` (C name + trailing underscore).
  - Plain `name` or `_name` do NOT work (assembler says "undefined").
  - `extrn name:word` does NOT work either (linker says "undefined symbol").
  - Function-local `static` variables do NOT get a stable `name_` label
    (compiler mangles/scopes them per-function) — must be file-scope.
- Function parameters CAN be addressed directly via `[bp+4]`, `[bp+6]`, etc.
  (near/tiny model: +4 = 1st param, +6 = 2nd param, ...) BUT ONLY if the
  compiler actually establishes a bp stack frame for that function. A
  function whose body is *just* an `#asm` block (no C locals) is treated as
  a leaf with no frame — bp still holds the caller's bp, so `[bp+4]` reads
  garbage. Fix: declare at least one (even unused) local variable, e.g.
  `int dummy;`, to force `push bp / mov bp,sp`. Verified by capturing bp
  into a static (`mov bpcap_, bp`) and scanning `[bp-8..bp+16]` from C to
  confirm offset +4 held the passed value.
  Prefer this over the file-scope-static workaround below when the value is
  only needed inside the same function (no C-side copy needed).
- Byte-sized access to a word-sized static works via `byte ptr name_`,
  e.g. `mov al, byte ptr bb_` / `mov byte ptr result_, al`.
- Linking DOS-target binaries: use `-ld11` (not `-lc86`, which is CP/M-86).
  `emu2 <file.com>` runs a DOS `.com` binary directly for quick testing.
- Multi-arg functions: first declared parameter is at `[bp+4]`, second at
  `[bp+6]`, etc. (confirmed with a 2-arg test: `f(a,b)` -> bp+4==a, bp+6==b).

Verified with editors/vi/asmtest.c + a `asmtest.com` Makefile target in that
project (scratch/throwaway, not part of the real vi build).
