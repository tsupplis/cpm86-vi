#!/usr/bin/env python3
"""Exercise external screens, full editor buffers and heap budget in native builds."""
from pathlib import Path
import os
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = ('vicp52.cmd', 'vicp100.cmd', 'vicpbios.cmd',
            'vid1bios.com', 'vid1bios.exe', 'vid2bios.exe')

PROBE = r'''
#include "editor.c"

static int failure_line;
#define REQUIRE(x) if (!(x)) { failure_line = __LINE__; goto failure; }

extern void vi_test_donormal(int c);
static int pattern_mode;

static int expected(unsigned i) {
    if (pattern_mode == 1)
        return '\n';
    if (pattern_mode == 2)
        return i % 251U;
    return i % 64 == 63 ? '\n' : 'a' + i % 23;
}

static int contents(void) {
    unsigned i;
    if (vi_file_end != vi_file_max)
        return 0;
    for (i = 0; i < FILELENG; i++)
        if ((unsigned char)vi_file_mem[i] != expected(i))
            return 0;
    return 1;
}

static int quality_commands(void) {
    static char original[] = "\ta\nb\n\tc";
    memcpy(vi_file_mem, original, sizeof original - 1);
    vi_file_end = vi_file_mem + sizeof original - 1;
    vi_top_char = vi_curs_char = vi_file_mem;
    vi_changed = 0;
    resetundo();
    vi_curs_char += 3;
    normal('m');
    vi_curs_char = vi_file_mem;
    REQUIRE(stuffin("3<<u3>>u"));
    while (anyinput())
        vi_test_donormal(vgetc());
    REQUIRE(vi_file_end == vi_file_mem + sizeof original - 1);
    REQUIRE(!memcmp(vi_file_mem, original, sizeof original - 1) && !vi_changed);
    REQUIRE(vi_mark == vi_file_mem + 3);
    normal('\'');
    REQUIRE(vi_curs_char == vi_file_mem + 3);
    memset(vi_file_mem, 'K', FILELENG - 2U);
    vi_file_end = vi_file_mem + FILELENG - 2U;
    vi_curs_char = vi_file_end - 1;
    normal('m');
    vi_curs_char = vi_file_mem;
    inschar('X');
    REQUIRE(vi_mark == vi_file_mem + FILELENG - 2U);
    delchar();
    REQUIRE(vi_mark == vi_file_mem + FILELENG - 3U);
    normal('\'');
    REQUIRE(vi_curs_char == vi_mark);
    delchar();
    REQUIRE(vi_mark == NULL);
    vi_changed = 0;
    resetundo();
    return 0;
failure:
    return 1;
}

int main(int argc, char **argv) {
    char *spare;
    char expected_undo[16];
    FILE *report;
    unsigned i;
    int spare_size, minimum = 0;

    for (i = 1; i < (unsigned)argc; i++) {
        if (!strcmp(argv[i], "MINIMUM"))
            minimum = 1;
        else if (!strcmp(argv[i], "LINES"))
            pattern_mode = 1;
        else if (!strcmp(argv[i], "BINARY"))
            pattern_mode = 2;
        else
            REQUIRE(0);
    }
#ifdef VI_DOS1_COM
    spare_size = 4096;
    REQUIRE(FILELENG == 18432U);
#else
    spare_size = minimum ? 2048 : 4096;
    REQUIRE(FILELENG == 42112U);
#endif
    REQUIRE(vi_yank_init());
    REQUIRE(vi_yank_capacity() == FILELENG);
    windinit();
    hexchars();
    vi_file_name = strsave("INPUT.TXT");
    screenalloc();
    filealloc();
    spare = malloc((unsigned)spare_size);
    REQUIRE(spare != NULL);
    memset(spare, 'Z', (unsigned)spare_size);
    vi_binary = 1;
    if (quality_commands() != 0)
        goto failure;
    vi_file_end = vi_top_char = vi_curs_char = vi_file_mem;
    screenclear();
    REQUIRE(readfile("INPUT.TXT", vi_file_mem, 1) == 0);
    REQUIRE(contents());
    REQUIRE(stuffin("Ju"));
    while (anyinput())
        vi_test_donormal(vgetc());
    REQUIRE(contents() && !vi_changed);

    REQUIRE(yankline(FILELENG));
    vi_changed = 0;
    strcpy(vi_undo_buff, "rZ");
    strcpy(vi_redo_buff, "rX");
    vi_renum = VI_COUNT_MAX + 1UL;
    REQUIRE(stuffin("d"));
    normal('d');
    REQUIRE(contents() && !vi_changed && !anyinput());
    REQUIRE(!strcmp(vi_undo_buff, "rZ") && !strcmp(vi_redo_buff, "rX"));
    vi_renum = VI_COUNT_MAX;
    REQUIRE(stuffin("d"));
    normal('d');
    REQUIRE(vi_file_end == vi_file_mem);
    REQUIRE(!strcmp(vi_redo_buff, "65535dd"));
    normal('u');
    while (anyinput())
        vi_test_donormal(vgetc());
    REQUIRE(contents());
    if (pattern_mode == 1) {
        sprintf(expected_undo, "%udd", (unsigned)FILELENG);
        REQUIRE(!strcmp(vi_undo_buff, expected_undo));
        normal('u');
        while (anyinput())
            vi_test_donormal(vgetc());
        REQUIRE(vi_file_end == vi_file_mem);
        normal('u');
        while (anyinput())
            vi_test_donormal(vgetc());
        REQUIRE(contents());
    }
    if (pattern_mode == 0) {
        vi_renum = VI_COUNT_MAX;
        vi_curs_char = vi_file_mem;
        normal('~');
        REQUIRE(vi_file_mem[0] == 'A' && !strcmp(vi_redo_buff, "65535~"));
        vi_curs_char = vi_file_mem;
        normal('~');
        REQUIRE(contents());
    }
    vi_changed = 0;
    vi_curs_char = vi_file_mem;
    inschar('X');
    REQUIRE(contents() && !vi_changed && vi_curs_char == vi_file_mem);
    putline(1);
    REQUIRE(contents() && !vi_changed && vi_curs_char == vi_file_mem);
    REQUIRE(readfile("INPUT.TXT", vi_file_mem, 1) == -1);
    REQUIRE(contents() && !vi_changed);
    REQUIRE(vi_save_file("OUTPUT.TXT", vi_file_mem, vi_file_end, 1) == NULL);
    vi_file_end = vi_top_char = vi_curs_char = vi_file_mem;
    REQUIRE(readfile("OVER.TXT", vi_file_mem, 1) == -1);
    REQUIRE(vi_file_end == vi_file_mem && !vi_changed);
    REQUIRE(readfile("OUTPUT.TXT", vi_file_mem, 1) == 0);
    REQUIRE(contents());
    for (i = 0; i < spare_size; i++)
        REQUIRE(spare[i] == 'Z');
    free(spare);
    clearlastmess();
    vi_key_exit();
    vi_yank_close();
    report = fopen("RESULT.TXT", "w");
    REQUIRE(report != NULL);
    REQUIRE(fprintf(report, "VI BUFFER PASS: %u bytes; %d bytes spare heap\n",
                    (unsigned)FILELENG, spare_size) >= 0);
    REQUIRE(fclose(report) == 0);
    return 0;
failure:
    fprintf(stderr, "VI BUFFER FAIL: line %d\n", failure_line);
    return 1;
}
'''


def run(args, work):
    try:
        return subprocess.run(args, cwd=work, check=True, timeout=60,
                              capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        print(error.stdout[-4000:])
        print(error.stderr[-4000:])
        raise
    except subprocess.TimeoutExpired as error:
        print((error.stdout or b'')[-4000:])
        print((error.stderr or b'')[-4000:])
        raise


def build(work, programs=PROGRAMS, probe=PROBE):
    for pattern in ('*.c', '*.h', '*.asm', 'Makefile'):
        for path in ROOT.glob(pattern):
            shutil.copyfile(path, work / path.name)
    source = (work / 'main.c').read_text()
    start = source.index('int main(')
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    (work / 'editor.c').write_text(source[:start] + source[end:])
    (work / 'main.c').write_text(probe)
    edit = work / 'edit.c'
    edit.write_text(edit.read_text() +
                    '\nvoid vi_test_donormal(int c) { donormal(c); }\n')
    run(['make', '-j1', *programs], work)


def main():
    programs = tuple(sys.argv[1:]) or PROGRAMS
    if any(program not in PROGRAMS for program in programs):
        raise SystemExit('Unknown buffer-runtime program')
    with tempfile.TemporaryDirectory(prefix='vi-buffer-runtime-') as directory:
        work = Path(directory)
        build(work, programs)
        for program in programs:
            allocations = [(None, 4096)]
            if program.endswith('.cmd'):
                data = struct.unpack_from('<BHHHH', (work / program).read_bytes(), 9)
                assert (data[0], data[3] * 16, data[4] * 16) == (2, 61440, 65536), program
                extra = struct.unpack_from('<BHHHH', (work / program).read_bytes(), 18)
                assert (extra[0], extra[1], extra[3] * 16, extra[4] * 16) == (
                    3, 0, 65536, 65536), program
                allocations.append((61440, 2048))
            for maximum, spare in allocations:
                args = [os.environ.get('EMU2', 'emu2'), program]
                if maximum is not None:
                    run(['pcdev_cmdmod', '-m', format(maximum, 'x'), program, '1'], work)
                    args.append('MINIMUM')
                capacity = 18432 if program.endswith('.com') else 42112
                fixtures = (
                    ([], bytes(10 if i % 64 == 63 else 97 + i % 23
                               for i in range(capacity))),
                    (['LINES'], b'\n' * capacity),
                    (['BINARY'], bytes(i % 251 for i in range(capacity))),
                )
                (work / 'OVER.TXT').write_bytes(b'x' * (capacity + 1))
                for flags, original in fixtures:
                    (work / 'INPUT.TXT').write_bytes(original)
                    result = run(args + flags, work)
                    report = work / 'RESULT.TXT'
                    assert report.exists(), (program, maximum, flags, result.stdout[-4000:])
                    expected = (f'VI BUFFER PASS: {capacity} bytes; '
                                f'{spare} bytes spare heap').encode()
                    actual = report.read_bytes().split(b'\x1a', 1)[0].strip()
                    assert actual == expected, (program, flags, actual, expected)
                    assert (work / 'OUTPUT.TXT').read_bytes() == original, program
                    report.unlink()
                    (work / 'OUTPUT.TXT').unlink()
                    allocation = f', DATA {maximum} bytes' if maximum is not None else ''
                    print('VI BUFFER RUNTIME PASS:', program,
                          f'({capacity} bytes, {spare} bytes spare heap{allocation}, '
                          f'{flags[0] if flags else "TEXT"})', flush=True)


if __name__ == '__main__':
    main()
