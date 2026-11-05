#!/usr/bin/env python3
"""Compare frozen/new display paths on real kernels and original PC video BIOS."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile

from test_buffer_runtime import ROOT, build, run


def check(root, name, image, config, exitprog, program, video, ram=None, timing=True):
    work = root / name
    work.mkdir()
    shutil.copyfile(image, work / 'boot.img')
    text = config.read_text()
    text = re.sub(r'^path = .*', f'path = "{config.parent}/rom"', text, count=1)
    text = text.replace('file    = "rom/', f'file    = "{config.parent}/rom/')
    text = re.sub(r'file\s*=\s*"(?:pcdos_full|dosplus|cdos41)\.img"',
                  'file = "boot.img"', text)
    text = re.sub(r'disk \{[^{}]*file\s*=\s*"cpmtest.img"[^{}]*\}', '', text)
    text = text.replace('driver = "sdl"', 'driver = "null"')
    if config.stem == 'cdos41':
        text = text.replace('size    = 384K', 'size    = 640K')
    text = re.sub(r'driver\s*=\s*"sdl:lowpass=\d+"', 'driver = "null"', text)
    if ram is not None:
        text, changes = re.subn(
            r'(size\s*=\s*)128K', rf'\g<1>{ram}K', text, count=1)
        assert changes == 1, 'Expected DOS 1.1 fixture with 128K RAM'
    assert re.search(r'model\s*=\s*"8088"', text), name
    speed = 1 if timing else 24
    text, changes = re.subn(
        r'(speed\s*=\s*)\d+', rf'\g<1>{speed}', text, count=1)
    assert changes == 1, 'Expected a CPU speed in the fixture'
    program_disk = 'boot.img'
    command = b'DISPLAY'
    if ram is None:
        shutil.copyfile(ROOT / 'dosbase.img', work / 'probe.img')
        text += '\ndisk { drive = 1 type = "auto" file = "probe.img" }\n'
        program_disk = 'probe.img'
        command = b'B:DISPLAY'
    (work / 'pce.cfg').write_text(text)
    if not timing:
        command += b' CHECK'
    (work / 'AUTOEXEC.BAT').write_bytes(command + b'\r\nPCEEXIT\r\n')
    run(['mcopy', '-o', '-i', program_disk, str(root / program),
         '::DISPLAY' + Path(program).suffix.upper()], work)
    cpm = config.stem == 'cdos41'
    if cpm:
        twist = str(ROOT.parent / 'ref/scripts/cpm86twist')
        shutil.copyfile(ROOT.parent / 'ref/diskdefs', work / 'diskdefs')
        run([twist, 'untwist', 'boot.img', 'logical.img'], work)
        (work / 'startup.0').write_bytes(b'SUBMIT CHECK\r\n\x1a')
        (work / 'CHECK.SUB').write_bytes(command + b'\r\nPCEEXIT\r\n\x1a')
        shutil.copyfile(work / 'AUTOEXEC.BAT', work / 'startup1.bat')
        run(['cpmcp', '-f', 'cpm86-320', 'logical.img', str(exitprog),
             'startup.0', 'CHECK.SUB', 'startup1.bat', '0:'], work)
        run([twist, 'twist', 'logical.img', 'boot.img'], work)
    else:
        for source, destination in (
                (exitprog, exitprog.name.upper()),
                (work / 'AUTOEXEC.BAT', 'AUTOEXEC.BAT')):
            run(['mcopy', '-o', '-i', 'boot.img', str(source), '::' + destination], work)
    result = subprocess.run(
        [os.environ.get('PCE', 'pce-ibmpc'), '-c', 'pce.cfg', '-t', 'null',
         '-r', '-g', video, '-l', 'pce.log'],
        cwd=work, timeout=180, capture_output=True, text=True)
    assert result.returncode in (0, 1), result.stderr
    if cpm:
        run([twist, 'untwist', 'boot.img', 'logical.img'], work)
        run(['cpmcp', '-f', 'cpm86-320', 'logical.img',
             '0:result.txt', 'result.txt'], work)
        report = (work / 'result.txt').read_text().split('\x1a', 1)[0]
    else:
        report = run(['mtype', '-i', 'boot.img', '::RESULT.TXT'], work).stdout
    print(name + '\n' + report, flush=True)
    assert report.startswith('VI DISPLAY PASS'), report
    cases = re.findall(r'(\d) ticks (\d+) (\d+) cursor (\d+) (\d+) chars (\d+) (\d+)',
                       report)
    assert len(cases) == 4, report
    before = after = 0
    for case, old_ticks, new_ticks, old_cursor, new_cursor, old_chars, new_chars in cases:
        assert old_chars == new_chars, report
        if timing and case == '2':
            assert int(new_ticks) <= int(old_ticks) + 2, (
                name, 'Single-cell regression beyond BIOS-tick quantization', report)
        if case in ('0', '1', '3'):
            assert int(new_cursor) < int(old_cursor), report
            before += int(old_ticks)
            after += int(new_ticks)
    if not timing:
        return name, before, after
    print(f'{name}: bulk display ticks {before} -> {after} '
          f'({100 * (before - after) / before:.1f}% reduction)', flush=True)
    return name, before, after


def main():
    timing = '--compat-only' not in sys.argv[1:]
    dos = Path(os.environ.get(
        'DOS11_SOURCE', Path.home() / 'Projects/DOS/pcdos11-hacking'))
    with tempfile.TemporaryDirectory(prefix='vi-display-') as directory:
        work = Path(directory)
        build(work, ('vid1bios.com', 'vid1bios.exe', 'vicpbios.cmd', 'vid2bios.exe'),
              (ROOT / 'test/displayprobe.c').read_text())
        results = []
        for extension, ram in (('com', 128), ('exe', 256)):
            for video in ('cga', 'mda'):
                results.append(check(
                    work, f'dos11-{extension}-{video}', dos / 'pcdos_base.img',
                    dos / 'pcdos.cfg', dos / 'pce/pceexit.com',
                    'vid1bios.' + extension, video, ram, timing))
        exitcmd = ROOT.parent / 'cpm86-hacking/pce/pceexit.cmd'
        for program in ('vicpbios.cmd', 'vid2bios.exe'):
            results.append(check(
                work, 'dosplus-' + program, ROOT / 'dosplus.img',
                ROOT / 'dosplus.cfg', exitcmd, program, 'cga', timing=timing))
        check(work, 'cdos41', ROOT / 'cdos41.img', ROOT / 'cdos41.cfg',
              exitcmd, 'vicpbios.cmd', 'vga', timing=False)
        if timing:
            assert any(after + 2 < before for _, before, after in results), (
                'No improvement beyond BIOS-tick quantization', results)
            assert all(after <= before + 2 for _, before, after in results), (
                'Display regression beyond BIOS-tick quantization', results)


if __name__ == '__main__':
    main()
