# Small vi improvement backlog

Goal: a small, dependable editor with predictable behavior, good responsiveness,
and economical use of code and memory.

Checked items have completed their documented implementation and validation.

## 1. Quality: concrete correctness work

- [x] **Q1 - Handle string-allocation failures safely.**
  `strsave()` in [linefunc.c](linefunc.c) and its callers check allocation
  failures; repeat search reuses its saved pattern.
  **Done when:** allocation failure reports an error without crashing, losing the
  previous search, or replacing a valid filename.

- [x] **Q2 - Fix filename ownership.**
  All filename replacement uses copy-before-free ownership, including aliased
  names. A failed allocation leaves the old filename and buffer intact.
  **Done when:** repeated renaming/opening does not consume heap; replacing a name
  is safe even when the argument aliases the current name.

- [x] **Q3 - Make indent/outdent and undo agree.**
  `tabinout()` in [normal.c](normal.c) preflights the complete operation and
  records changed lines in the existing undo buffer (up to 8,192 visited lines).
  **Done when:** mixed indentation, no-op outdents and capacity rejection preserve
  text correctly; undo restores exactly the original bytes and modified flag.

- [x] **Q4 - Fix join-command state accounting.**
  `J` captures state before deletion and shares literal-byte undo with indentation.
  **Done when:** join followed by undo restores both original text and the
  original clean/dirty state; joining at EOF leaves prior undo intact.

- [x] **Q5 - Build a command-consistency regression corpus.**
  Exercise commands through the real parser, including counts, cancellation,
  undo and repeat.
  **Done when:** empty, one-line, unterminated and full buffers have deterministic
  expected results; rejected commands preserve the documented state.
  **Result:** sanitizer-backed table-driven parser coverage across both buffer
  capacities, allocation-failure/ownership checks, bitmap-boundary tests and
  native parser checks alongside full-buffer/heap-budget regressions.

## 2. Responsiveness: measure, then optimize

- [x] **P1 - Establish a repeatable performance and memory baseline.**
  Use fixed fixtures and a fixed 8088 emulator configuration.
  **Done when:** we can compare load/save, middle `:r`, typing near the beginning,
  scrolling, long-line movement and search, plus code/data sizes and heap
  headroom.
  **Result:** [short baseline](docs/performance.md), one bounded DOS 1/8088/CGA
  profile with seven checked cases, code/data image sizes and reused verified
  heap budgets/display results. Middle import is the demonstrated next target.

- [x] **P2 - Batch middle-of-buffer imports.**
  Replace `readfile()` in [main.c](main.c)'s per-byte tail shifting.
  **Done when:** tail movement is substantially reduced, with byte-exact results
  and unchanged all-or-nothing failure behavior.
  **Result:** 128-byte filtered chunks reuse the existing status buffer.
  The short middle-import sample falls from 159 to 6 ticks; tail movement is
  128x smaller for that fixture. Chunk-boundary, text/binary, exact-capacity and
  rollback tests pass on host and three native runtimes; all 27 full-buffer
  cases retain their heap budgets. See [measurements](docs/performance.md#p2-batched-imports).

- [x] **P3 - Add efficient changed-run screen output.**
  Row-bounded changed runs avoid redundant BIOS cursor positioning while
  preserving the existing single-character path for other callers.
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

- [x] **P4 - Investigate long-line cursor and search costs.**
  Measure rescanning before introducing caches or a new search algorithm.
  **Done when:** identify the dominant cost; implement only a demonstrated
  improvement, with bounded memory and unchanged navigation/search semantics.
  **Result:** one-pass logical-column accounting and first/distinct-byte search
  rejection, without persistent state or a skip table. The short comparison
  shows about 1.4x faster cursor calculation and 2-2.5x faster measured misses.
  Frozen-reference parity, large native navigation, 87 editor-state and 27
  full-buffer cases pass. See [measurements](docs/performance.md#p4-cursor-and-search-scanning).

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

- [ ] **F3 - Add one mark and return-to-mark.**
  Store a single buffer-local cursor position, not a named-mark table or jump
  history. Set it explicitly; return to its exact position only if defined.
  **Done when:** surviving edits keep the mark attached to its character;
  deleting that character invalidates it, undo does not resurrect it, and
  replacing the file buffer clears it. An undefined mark reports an error
  without moving the cursor. Preserve the existing heap-headroom requirements.
  Backlog only: no marks implementation is currently present.

## 4. Size reduction: one measured candidate

- [x] **S1 - Evaluate a more compact nonprintable-character representation.**
  Investigate [hexchars.c](hexchars.c).
  **Done when:** compare code/data savings against rendering cost. Keep a
  replacement only if octal/hex/decimal output remains identical and
  responsiveness stays acceptable.
  **Result:** compact cached strings and a byte-width array save 498 resident
  DATA bytes, 96 EXE code bytes and about 1.5 KiB per executable. All bases and
  byte values match; short renderer samples differ by at most one tick.
  On-demand formatting was rejected for slower expanded-byte rendering.
  See [comparison and validation](docs/performance.md#s1-compact-cached-display-text).

## 5. Maintainability: targeted cleanup

- [x] **M1 - Refresh the design documentation and invariant list.**
  Remove obsolete descriptions of allocation, bulk operations and platform
  layouts.
  **Done when:** documentation matches current behavior and explains the
  important memory, arithmetic and failure-handling rules.
  **Result:** current module/platform map, ownership/undo/rendering invariants,
  accurate bulk-vs-per-byte costs and validation/heap-budget scope.

- [ ] **M2 - Reduce source-extraction fragility in tests.**
  Introduce narrow test entry points where existing tests parse function bodies.
  **Done when:** selected tests exercise production code directly without copying
  its implementation or enlarging production binaries.
