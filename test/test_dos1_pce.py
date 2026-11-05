#!/usr/bin/env python3
"""Verify both full DOS 1 editor probes on a real DOS 1.1 kernel."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile

from test_buffer_runtime import build, run


def main():
    dos = Path(os.environ.get(
        'DOS11_SOURCE', Path.home() / 'Projects/DOS/pcdos11-hacking'))
    with tempfile.TemporaryDirectory(prefix='vi-dos1-dual-') as directory:
        root = Path(directory)
        build(root, ('vid1bios.com', 'vid1bios.exe'))
        for extension, capacity, spare, ram in (
                ('com', 20480, 4096, 128), ('exe', 42112, 4096, 256)):
            check(root, dos, extension, capacity, spare, ram)


def check(root, dos, extension, capacity, spare, ram):
    work = root / extension
    work.mkdir()
    program = root / ('vid1bios.' + extension)
    assert (program.read_bytes()[:2] == b'MZ') == (extension == 'exe')
    shutil.copyfile(dos / 'pcdos_base.img', work / 'boot.img')
    text = (dos / 'pcdos.cfg').read_text()
    text, changes = re.subn(
        r'(size\s*=\s*)128K', rf'\g<1>{ram}K', text, count=1)
    assert changes == 1, 'Expected the DOS 1.1 fixture to specify 128K RAM'
    text = re.sub(r'^path = .*', f'path = "{dos}/rom"', text, count=1)
    text = text.replace('file    = "rom/', f'file    = "{dos}/rom/')
    text = re.sub(r'file\s*=\s*"pcdos_full.img"', 'file = "boot.img"', text)
    text = text.replace('driver = "sdl"', 'driver = "null"')
    text = re.sub(r'driver\s*=\s*"sdl:lowpass=\d+"', 'driver = "null"', text)
    (work / 'pce.cfg').write_text(text)
    original = bytes(i % 251 for i in range(capacity))
    (work / 'INPUT.TXT').write_bytes(original)
    (work / 'OVER.TXT').write_bytes(b'x' * (capacity + 1))
    (work / 'AUTOEXEC.BAT').write_bytes(b'BUFFER BINARY\r\nPCEEXIT\r\n')
    for source, destination in (
            (program, 'BUFFER.' + extension.upper()),
            (dos / 'pce/pceexit.com', 'PCEEXIT.COM'),
            (work / 'INPUT.TXT', 'INPUT.TXT'),
            (work / 'OVER.TXT', 'OVER.TXT'),
            (work / 'AUTOEXEC.BAT', 'AUTOEXEC.BAT')):
        run(['mcopy', '-o', '-i', 'boot.img', str(source),
             '::' + destination], work)
    result = subprocess.run(
        [os.environ.get('PCE', 'pce-ibmpc'), '-c', 'pce.cfg', '-t', 'null',
         '-r', '-l', 'pce.log'], cwd=work, timeout=60, capture_output=True, text=True)
    # PCEEXIT uses the emulator's abort hook, which can return status 1.
    assert result.returncode in (0, 1), result.stderr
    for source, destination in (('RESULT.TXT', 'result.txt'),
                                ('OUTPUT.TXT', 'output.bin')):
        run(['mcopy', '-i', 'boot.img', '::' + source, destination], work)
    report = (work / 'result.txt').read_bytes().split(b'\x1a', 1)[0].strip()
    expected = f'VI BUFFER PASS: {capacity} bytes; {spare} bytes spare heap'.encode()
    assert report == expected, report
    assert (work / 'output.bin').read_bytes() == original
    print(f'DOS 1.1 {extension.upper()} PASS: {capacity}-byte binary '
          f'read/yank/delete/undo/save/reopen, {spare} bytes spare heap, '
          f'{ram} KiB RAM', flush=True)


if __name__ == '__main__':
    main()
