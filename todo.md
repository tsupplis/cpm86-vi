# Small vi improvement backlog

Goal: a small, dependable editor with predictable behavior, good responsiveness,
and economical use of code and memory.

This is a proposed execution backlog, not a record of completed work.

## 1. Quality: concrete correctness work

- [ ] **Q1 - Handle string-allocation failures safely.**
  `strsave()` in [linefunc.c](linefunc.c) currently passes an unchecked allocation
  result to `strcpy`. Update its callers too.
  **Done when:** allocation failure reports an error without crashing, losing the
  previous search, or replacing a valid filename.

- [ ] **Q2 - Fix filename ownership.**
  Repeated `:f` and `:e` allocate replacement names without consistently releasing
  the previous allocation.
  **Done when:** repeated renaming/opening does not consume heap; replacing a name
  is safe even when the argument aliases the current name.

- [ ] **Q3 - Make indent/outdent and undo agree.**
  `tabinout()` in [normal.c](normal.c) constructs undo by applying the opposite
  operation to every requested line, even when some lines were unchanged.
  **Done when:** mixed indentation, no-op outdents and capacity rejection preserve
  text correctly; undo restores exactly the original bytes and modified flag.

- [ ] **Q4 - Fix join-command state accounting.**
  `J` captures undo state after deleting the newline.
  **Done when:** join followed by undo restores both original text and the
  original clean/dirty state; joining at EOF leaves prior undo intact.

- [ ] **Q5 - Build a command-consistency regression corpus.**
  Exercise commands through the real parser, including counts, cancellation,
  undo and repeat.
  **Done when:** empty, one-line, unterminated and full buffers have deterministic
  expected results; rejected commands preserve the documented state.

## 2. Responsiveness: measure, then optimize

- [ ] **P1 - Establish a repeatable performance and memory baseline.**
  Use fixed fixtures and a fixed 8088 emulator configuration.
  **Done when:** we can compare load/save, middle `:r`, typing near the beginning,
  scrolling, long-line movement and search, plus code/data sizes and heap
  headroom.

- [ ] **P2 - Batch middle-of-buffer imports.**
  Replace `readfile()` in [main.c](main.c)'s per-byte tail shifting.
  **Done when:** tail movement is substantially reduced, with byte-exact results
  and unchanged all-or-nothing failure behavior.

- [x] **P3 - Add efficient changed-run screen output.**
  **First implementation priority.** Capture a focused display baseline before
  changing output: full redraw, scrolling, single-character edits and long
  changed runs, using a fixed 8088 configuration.
  The renderer already skips unchanged cells and tracks contiguous output, but
  the BIOS character writer still positions the cursor for each character.
  Make the backend output contiguous runs without redundant cursor positioning;
  preserve the existing single-character path for other callers.
  **Done when:** identical frames and cursor behavior, fewer BIOS/terminal calls,
  a measured display-speed improvement, and preserved attributes,
  status-row/background-clock handling and terminal compatibility.
  **Result:** BIOS bulk diff/output benchmarks are 3.23x-3.83x faster on the
  standard-speed 8088 setup. Seven real-kernel display profiles pass, including
  Concurrent DOS 4.1, with colored attributes, cursor recovery, status-row
  protection and legacy control-character behavior checked. All six full-buffer
  variants and both DOS 1 kernel roundtrips pass.
  **VT follow-up complete:** VT52/VT100 runs and cursor sequences now bypass
  per-character stdio overhead while preserving console bytes and ordering.
  Short DOS Plus/CGA measurements show 1.45x faster bulk output; single-cell
  timings are effectively unchanged. DOS Plus and Concurrent DOS VT52 checks
  pass, including settled hardware cursors. Both VT protocols have host
  byte/error-path tests; native VT100 timing remains unmeasured.

- [ ] **P4 - Investigate long-line cursor and search costs.**
  Measure rescanning before introducing caches or a new search algorithm.
  **Done when:** identify the dominant cost; implement only a demonstrated
  improvement, with bounded memory and unchanged navigation/search semantics.

- [ ] **P5 - Measure disk buffering separately from buffer manipulation.**
  Compare current buffered stdio with modest block sizes.
  **Done when:** establish whether disk calls or CPU processing dominate; change
  buffering only if the measured gain justifies its memory cost.

## 3. Functionality: three restrained additions

- [ ] **F1 - Add character-find motions: `f`, `F`, `t`, `T`, followed by `;` and `,`.**
  **Done when:** line-local searches support counts, handle missing characters
  predictably, and do not disturb edit undo/repeat.

- [ ] **F2 - Add `%` bracket matching.**
  Start with literal nested `()`, `[]`, `{}` matching, not an assembly-language
  parser.
  **Done when:** forward/backward nesting works; unmatched brackets leave the
  cursor unchanged and signal failure.

- [ ] **F3 - Add marks and return-to-mark.**
  Use fixed storage, with explicit insertion/deletion adjustment rules.
  **Done when:** marks remain meaningful after edits, deleted marks are
  invalidated predictably, and file changes clear them.

## 4. Size reduction: one measured candidate

- [ ] **S1 - Evaluate a more compact nonprintable-character representation.**
  Investigate [hexchars.c](hexchars.c).
  **Done when:** compare code/data savings against rendering cost. Keep a
  replacement only if octal/hex/decimal output remains identical and
  responsiveness stays acceptable.

## 5. Maintainability: targeted cleanup

- [ ] **M1 - Refresh the design documentation and invariant list.**
  Remove obsolete descriptions of allocation, bulk operations and platform
  layouts.
  **Done when:** documentation matches current behavior and explains the
  important memory, arithmetic and failure-handling rules.

- [ ] **M2 - Reduce source-extraction fragility in tests.**
  Introduce narrow test entry points where existing tests parse function bodies.
  **Done when:** selected tests exercise production code directly without copying
  its implementation or enlarging production binaries.

## Recommended order

P3 is complete. Next: Q1-Q4, the remainder of P1, Q5 and P2. Choose the remaining
work from measurements. Native VT100/ANSI timing remains optional follow-up.

Every implementation task should preserve the current buffer limits, native
memory-budget checks and supported-platform behavior.

No autoindent, gap-buffer rewrite or feature expansion beyond this list.
