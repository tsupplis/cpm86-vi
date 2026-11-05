# Short performance and memory baseline

The measurements below describe their original buffer sizes. Current editing
and yank limits are 42,112 bytes for CP/M and DOS EXE, and 20,480 bytes for DOS 1
COM; new timing samples should not be compared as identical-capacity runs.

## Reproduce

From the repository root, with the existing Aztec/PCE and DOS 1.1 fixtures:

```
make test-perf-pce
```

To keep a machine-readable result:

```
python3 -B test/test_perf_pce.py --output baseline.json
```

The runner builds only one private probe, isolates Aztec's compiler temporary
directory, and boots one private image. It uses **PC-DOS 1.1, DOS 1 EXE,
8088 speed 1, CGA, 256 KiB RAM**, with a **60-second emulator timeout**.
There are no automatic timing retries, statistical repetitions or platform
sweeps. Fixture preparation and setup are outside each timed interval.
The existing production binaries must be present for size reporting.

The JSON records source commit/dirty state, fixture/probe/config/boot-image
hashes, executable sizes/hashes and seven measured cases. This distinguishes
local builds without pretending a dirty worktree is a clean release.

## Recorded sample

Taken on 2026-11-05, based on `4045e15` plus the documentation/probe changes.
The initial sample used the fixtures below; the reported intervals total
383 BIOS ticks, approximately 21 seconds of emulated time.

| Case | Fixed work | Total ticks |
|---|---|---:|
| Empty-buffer load | One 4,096-byte binary read | 21 |
| Save | One 4,096-byte binary save, including flush/truncate/close | 13 |
| Middle `:r` core | One 128-byte import at offset 2,048 in the 4,096-byte buffer | 159 |
| Beginning edit core | Eight insert/delete primitive pairs at offset zero in 4,096 bytes | 29 |
| Viewport scrolling | Two one-line downward moves past the viewport bottom, including redraw/output | 31 |
| Long-line cursor | Eight column recalculations at offset 4,095 in an 8,192-byte line | 45 |
| Failed search | Four wrapped misses for `aaaaab` in 8,192 `a` bytes | 85 |

BIOS ticks are roughly 1/18.2 second; coarse sampling carries about a tick of
boundary uncertainty. Compare the same cases and repeat counts, not individual
sub-tick operations. This is a reproducible point sample, not a significance
test or a whole-editor/real-hardware speed claim.

Beginning edits deliberately isolate tail movement: they do not include parser
or redraw cost. Cursor recalculation excludes redraw; scroll includes it.
Load/import and failed search include their normal status output. The probe
checks successful return values, expected cursor/viewport/length state, import
bytes and an intact 4 KiB held-spare allocation; the host checks saved bytes.

Fixtures:

- `BASE.TXT`: 4,096 bytes, 64 lines of 63 repeated row-specific printable bytes
  followed by LF. The row character is `a + (row modulo 23)`.
  SHA-256: `e116346efe48861de64d1cfe37dccc6784ad7434f68f5c74f32dde72cd52fc96`.
- `IMPORT.TXT`: 128 `X` bytes.
  SHA-256: `64531077024b8fe57566a3d556ef54fd598bab2e0ca49b43185f765a6a86cb5d`.
- CPU-only long-line fixture: 8,192 `a` bytes, generated before timing.

The middle import takes more time than loading the much larger empty buffer.
It repeatedly moves the existing tail; this motivated the P2 change below.
Long-line cursor and search are measurable P4 candidates, not yet algorithm
recommendations. These tiny file samples do not isolate disk service from CPU
and buffering costs; that remains P5.

## P2: batched imports

The same probe, fixtures, boot/config hashes and profile were run once after
changing `readfile()` to stage 128 filtered bytes in its existing status buffer.
It moves the original tail once per chunk, not once per imported byte.
No extra heap or scratch buffer is needed.

| Case | P1 ticks | P2 ticks |
|---|---:|---:|
| Empty-buffer load | 21 | 20 |
| Save | 13 | 13 |
| Middle import | 159 | 6 |
| Eight beginning edit pairs | 29 | 29 |
| Two viewport scrolls | 31 | 32 |
| Eight long-line cursor recalculations | 45 | 45 |
| Four failed searches | 85 | 86 |

For this middle-import fixture, tail movement falls from 262,144 to 2,048
bytes (128 times less). Elapsed time falls from about 8.7 to 0.33 seconds:
roughly **26x faster for this operation**, not for the whole editor.
One-tick differences elsewhere are within the coarse timer's uncertainty.
There was no additional timing sweep.

The enlarged I/O regressions check exact/overflow capacity and read/close
rollback across 127/128/129 and 255/256/257-byte boundaries; beginning, middle
and EOF imports; CR filtering across chunks; and all 256 binary byte values.
They count tail moves/bytes directly and pass under host sanitizers and all
three native runtimes. Parser/state checks pass in all three buffer profiles.
All 27 full-buffer native cases still pass, including the 4 KiB normal and
2 KiB minimum-CP/M held-spare budgets.

All six production variants were rebuilt. Their code/load images grew only
80-96 bytes compared with the P1 snapshot (paragraph rounding varies):
COM is now 30,428 file bytes; DOS 1 EXE 30,942; DOS 2 EXE 30,214.
CMD file lengths are unchanged. These changes do not reduce buffer capacities.

## S1: compact cached display text

The retained representation uses a 256-byte width array and a 966-byte cache
for C0/DEL/high-byte display strings. LF and CR leave two unused cache slots,
avoiding expensive index calculations. Numbers are formatted only at mode
selection, never during redraw; cursor movement still uses a direct width lookup.

The old pointer/width table plus strings occupied 1,722 bytes on Aztec.
The new arrays occupy 1,222 bytes. Including the two extra format-string bytes,
resident DATA falls **498 bytes**; code falls **96 bytes** in the measured EXEs.
Initialized data shrinks more because cached strings now live in zero-filled
storage rather than the load image. File-size savings must not be confused with
resident-memory savings.

| Binary | P2 file bytes | S1 file bytes | Saved bytes |
|---|---:|---:|---:|
| `vicp52.cmd` | 34,816 | 33,280 | 1,536 |
| `vicp100.cmd` | 34,816 | 33,280 | 1,536 |
| `vicpbios.cmd` | 35,328 | 33,792 | 1,536 |
| `vid1bios.com` | 30,428 | 28,866 | 1,562 |
| `vid1bios.exe` | 30,942 | 29,382 | 1,560 |
| `vid2bios.exe` | 30,214 | 28,654 | 1,560 |

A short same-process A/B probe compares the old layout with the compact cache
using identical renderer control flow, on the standard 8088/DOS 1.1/CGA profile.
Each interval is four `filetonext()` calls, excluding initialization and terminal
output. Printable input is 512 `A` bytes; expanded input cycles byte values with
single-cell bytes replaced by byte 1. A third mixed-byte fixture checks frame
parity without timing. All three bases match every screen cell, status-row guard
and bottom-of-viewport pointer.

| Base | Printable: old / compact ticks | Expanded: old / compact ticks |
|---|---:|---:|
| Octal | 7 / 7 | 26 / 26 |
| Hex | 7 / 6 | 26 / 27 |
| Decimal | 7 / 6 | 26 / 27 |

Differences are at most one coarse timer tick; this sample does not establish
a meaningful rendering regression or speedup. An earlier on-demand formatting
candidate was rejected: expanded rendering took 12-19% longer. The retained
cache trades some potential memory savings for predictable rendering cost.

`make test-characters` checks all 256 widths and every expanded string in
octal/hex/decimal, repeated mode switches and hex-key conversion under host
sanitizers and all three native runtimes. To explicitly repeat the bounded A/B:

```
python3 -B test/test_characters.py --timing --output characters.txt
```

The 500 scrolling/rendering parity cases, 87 editor-state cases, host/native
navigation checks and all 27 full-buffer/heap-budget cases pass. All six
production binaries, ZIP and both disk images were rebuilt. Capacities and
held-spare budgets are unchanged; no heap allocation was added.

## P4: cursor and search scanning

The long-line virtual column previously walked backward to find a newline,
then walked the same prefix forward to sum widths. It now sums widths while
walking backward once. This preserves delayed screen wrapping and unsigned
virtual columns without adding cache state.

Search called `memcmp()` at every candidate start. It now first checks the
initial pattern byte and the first byte different from it, falling back to
byte zero for uniform patterns. This cheaply rejects repeated-prefix misses
whether the distinguishing byte is near the beginning, middle or end.
Full comparisons still determine matches; candidate order and overlap/wrapping
rules are unchanged. Worst-case search complexity is unchanged.

One same-process 8088/DOS 1.1/CGA comparison against the frozen pre-P4 functions:

| Case | Repeats | Old ticks | P4 ticks |
|---|---:|---:|---:|
| Long-line cursor | 8 | 44 | 31 |
| Forward miss: `aaaaab` | 2 | 39 | 16 |
| Forward miss: `abaaa` | 2 | 30 | 15 |
| Forward miss: `baaaaa` | 2 | 29 | 12 |
| Backward miss: `aaaaab` | 2 | 38 | 15 |
| Backward miss: `abaaa` | 2 | 30 | 15 |
| Backward miss: `baaaaa` | 2 | 28 | 11 |

These are approximately **1.4x faster cursor calculation** and **2-2.5x faster
for these misses**, not universal search or whole-editor speedups. The fixture
is 8,192 `a` bytes; cursor offset 4,095 and viewport offset 4,080. Search leaves
the cursor at 4,095. Timed calls exclude status output, redraw and fixture setup,
unlike the earlier P1/P2 failed-search case. Both sides use the same runtime,
width table and fixture; intervals total about 19 seconds of emulated time.
Coarse ticks and a single sample limit precision.

Reproduce the explicitly bounded comparison:

```
make test-navigation-perf-pce
```

Or save its text report:

```
python3 -B test/test_navigation_perf.py --output navigation.txt
```

Expanded `test-navigation-runtime` compares both search directions and cursor
geometry against frozen references on 128 deterministic short binary fixtures,
at every cursor position including EOF. Cases include empty/long/uniform
patterns, overlaps, wrapped hits, embedded NUL/high bytes and widths 1-80.
Instrumented tests prove the three misses above make no full `memcmp()` calls.
Existing large-buffer/count/85,000-column checks remain covered.
Host sanitizers and all three native runtimes pass, as do the 500 renderer
parity cases, 87 editor-state cases and 27 full-buffer/heap-budget cases.

All six binaries and packages were rebuilt. EXE code grows 192 bytes; resident
DATA is unchanged, with only a few extra automatic search bytes and no heap
allocation. DOS COM grows from 28,866 to 29,054 file bytes; DOS 1/2 EXEs from
29,382/28,654 to 29,574/28,846. The two VT CMDs grow one 512-byte file-alignment
unit to 33,792 bytes; BIOS CMD stays 33,792. Buffer capacities and held-spare
budgets remain unchanged.

## Production images and memory

Original P1 snapshot, retained for comparison:

| Binary | File bytes | Code image bytes | Data image bytes |
|---|---:|---:|---:|
| `vicp52.cmd` | 34,816 | 26,752 | 7,728 |
| `vicp100.cmd` | 34,816 | 26,736 | 7,760 |
| `vicpbios.cmd` | 35,328 | 27,152 | 7,696 |
| `vid1bios.com` | 30,342 | Combined code/data: 30,342 | Not separately encoded |
| `vid1bios.exe` | 30,860 | 23,456 | 6,892 |
| `vid2bios.exe` | 30,134 | 22,832 | 6,790 |

CMD image values are paragraph-rounded group lengths, not resident allocation
limits. EXE values exclude the MZ header; the runner verifies the current Aztec
small-model entry stub's data-segment immediate against initial SS before
splitting the code/data load image. COM has no segment headers and is not
artificially split. File size includes headers/alignment, and images do not
describe all runtime heap/stack/BSS requirements.

CP/M DATA reserves 61,440-65,536 bytes; EXTRA reserves 65,536 bytes without
payload. At measurement time DOS 1 COM had a combined 64 KiB near window, a 20,480-byte editing
buffer and 32 KiB external reservation. Other editing buffers hold 38,016 bytes
with a 64 KiB external reservation. Two 2,000-byte external screens follow the
matching yank region. See [design.md](design.md) for reservation mechanisms.

Reuse the existing full-buffer validation budgets rather than rerunning a heap
search: **4 KiB held spare in every normal variant**, **2 KiB with minimum CP/M
DATA**. Real DOS 1 COM/EXE boots passed with 4 KiB held on 128/256 KiB machines.
These are tested lower bounds with the complete editing buffer allocated, not
maximum free-heap estimates.

## Existing display results, not rerun

The [README display results](../README.md#display-output) remain the reference:
BIOS bulk diff/output improved 3.23x-3.83x; a separate DOS Plus VT52 sample
improved 1.45x. Single-cell measurements were essentially unchanged.
They have different fixture sizes/repeat counts from this short baseline and
must not be added to it or compared as if they were the same workload.
Native VT100 timing is still optional follow-up.
