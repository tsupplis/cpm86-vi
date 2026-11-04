#!/usr/bin/env python3
"""Compile and execute the real 8086 yank adapters under emu2."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(args, work):
    try:
        return subprocess.run(args, cwd=work, check=True, timeout=60,
                              capture_output=True, text=True)
    except subprocess.TimeoutExpired as error:
        print((error.stdout or b'')[-3000:])
        print((error.stderr or b'')[-3000:])
        raise


def main():
    with tempfile.TemporaryDirectory(prefix='vi-yank-runtime-') as directory:
        work = Path(directory)
        for name in ('yankmem.c', 'yankmem.h', 'yankcopy.asm', 'yankcp.asm',
                     'yankd11.asm', 'yankd20.asm'):
            shutil.copyfile(ROOT / name, work / name)
        shutil.copyfile(ROOT / 'test/yankprobe.c', work / 'yankprobe.c')
        try:
            for source in ('yankcopy', 'yankcp', 'yankd11', 'yankd20'):
                run(['aztec42_as', source + '.asm'], work)
            for source in ('yankmem', 'yankprobe'):
                run(['aztec42_cc', '-I.', '+F', '+0', '-o', source + '.o',
                     source + '.c'], work)
            for library, adapter, extension in (
                    ('c86', 'yankcp', 'cmd'), ('d11', 'yankd11', 'com'),
                    ('c', 'yankd20', 'exe')):
                output = 'yank.' + extension
                run(['aztec42_link', '-o', output, 'yankprobe.o', 'yankmem.o',
                     'yankcopy.o', adapter + '.o', '-l' + library], work)
                if extension == 'cmd':
                    rejected = run(['emu2', output, 'REJECT'], work)
                    assert 'VI YANK INIT REJECTED' in rejected.stdout
                    run(['pcdev_cmdmod', '-t', 'EXTRA', '-n', '4000',
                         '-m', '4000', output, '2'], work)
                    rejected = run(['emu2', output, 'REJECT'], work)
                    assert 'VI YANK INIT REJECTED' in rejected.stdout
                    run(['pcdev_cmdmod', '-t', 'EXTRA', '-n', '8000',
                         '-m', '8000', output, '2'], work)
                result = run(['emu2', output], work)
                assert 'VI YANK PASS: 0 failures' in result.stdout, result.stdout
                print('VI YANK RUNTIME PASS:', library)
                if os.environ.get('YANK_TEST_OUTPUT'):
                    destination = Path(os.environ['YANK_TEST_OUTPUT'])
                    destination.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(work / output, destination / output)
        except subprocess.CalledProcessError as error:
            print(error.stdout)
            print(error.stderr)
            raise


if __name__ == '__main__':
    main()
