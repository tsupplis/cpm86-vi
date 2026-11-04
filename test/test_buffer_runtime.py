#!/usr/bin/env python3
"""Exercise the larger editor buffer and heap budget in native builds."""
from pathlib import Path
import os
import shutil
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = ('vicp52.cmd', 'vicp100.cmd', 'vicpbios.cmd',
            'vid2bios.exe')

PROBE = r'''
#include "editor.c"

#define REQUIRE(x) if (!(x)) { \
    fprintf(stderr, "VI BUFFER FAIL: line %d\n", __LINE__); return 1; }

static int expected(int i) {
    return i % 64 == 63 ? '\n' : 'a' + i % 23;
}

static int contents(void) {
    int i;
    if (vi_file_end != vi_file_max)
        return 0;
    for (i = 0; i < FILELENG; i++)
        if (vi_file_mem[i] != expected(i))
            return 0;
    return 1;
}

int main(int argc, char **argv) {
    char *spare;
    FILE *report;
    int i, spare_size;

    REQUIRE(argc == 1 || (argc == 2 && !strcmp(argv[1], "MINIMUM")));
    spare_size = argc == 1 ? 8192 : 2048;
    REQUIRE(FILELENG == 32000);
    REQUIRE(vi_yank_init());
    windinit();
    hexchars();
    vi_file_name = strsave("INPUT.TXT");
    screenalloc();
    REQUIRE(vi_real_scr != NULL && vi_next_scr != NULL);
    filealloc();
    spare = malloc((unsigned)spare_size);
    REQUIRE(spare != NULL);
    memset(spare, 'Z', (unsigned)spare_size);
    vi_binary = 1;
    vi_file_end = vi_top_char = vi_curs_char = vi_file_mem;
    screenclear();
    REQUIRE(readfile("INPUT.TXT", vi_file_mem, 1) == 0);
    REQUIRE(contents());

    REQUIRE(yankline(FILELENG));
    vi_renum = FILELENG;
    REQUIRE(stuffin("d"));
    normal('d');
    REQUIRE(vi_file_end == vi_file_mem);
    normal('u');
    while (anyinput())
        normal(vgetc());
    REQUIRE(contents());
    vi_changed = 0;
    vi_curs_char = vi_file_mem;
    inschar('X');
    REQUIRE(contents() && !vi_changed && vi_curs_char == vi_file_mem);
    putline(1);
    REQUIRE(contents() && !vi_changed && vi_curs_char == vi_file_mem);
    REQUIRE(readfile("INPUT.TXT", vi_file_mem, 1) == -1);
    REQUIRE(contents() && !vi_changed);
    REQUIRE(vi_save_file("OUTPUT.TXT", vi_file_mem, vi_file_end, 1) == NULL);
    for (i = 0; i < spare_size; i++)
        REQUIRE(spare[i] == 'Z');
    free(spare);
    clearlastmess();
    vi_key_exit();
    vi_yank_close();
    report = fopen("RESULT.TXT", "w");
    REQUIRE(report != NULL);
    REQUIRE(fprintf(report, "VI BUFFER PASS: %d bytes; %d bytes spare heap\n",
                    FILELENG, spare_size) >= 0);
    REQUIRE(fclose(report) == 0);
    return 0;
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


def main():
    with tempfile.TemporaryDirectory(prefix='vi-buffer-runtime-') as directory:
        work = Path(directory)
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
        (work / 'main.c').write_text(PROBE)
        run(['make', *PROGRAMS], work)
        for program in PROGRAMS:
            allocations = [(None, 8192)]
            if program.endswith('.cmd'):
                data = struct.unpack_from('<BHHHH', (work / program).read_bytes(), 9)
                assert (data[0], data[3] * 16, data[4] * 16) == (2, 61440, 65536), program
                allocations.append((61440, 2048))
            for maximum, spare in allocations:
                args = [os.environ.get('EMU2', 'emu2'), program]
                if maximum is not None:
                    run(['pcdev_cmdmod', '-m', format(maximum, 'x'), program, '1'], work)
                    args.append('MINIMUM')
                capacity = 32000
                original = bytes(10 if i % 64 == 63 else 97 + i % 23
                                 for i in range(capacity))
                (work / 'INPUT.TXT').write_bytes(original)
                result = run(args, work)
                report = work / 'RESULT.TXT'
                assert report.exists(), (program, maximum, result.stdout[-4000:])
                expected = (f'VI BUFFER PASS: {capacity} bytes; '
                            f'{spare} bytes spare heap').encode()
                assert report.read_bytes().split(b'\x1a', 1)[0].strip() == expected, program
                assert (work / 'OUTPUT.TXT').read_bytes() == original, program
                report.unlink()
                (work / 'OUTPUT.TXT').unlink()
                allocation = f', DATA {maximum} bytes' if maximum is not None else ''
                print('VI BUFFER RUNTIME PASS:', program,
                      f'({capacity} bytes, {spare} bytes spare heap{allocation})',
                      flush=True)


if __name__ == '__main__':
    main()
