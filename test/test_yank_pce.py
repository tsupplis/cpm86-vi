#!/usr/bin/env python3
"""Verify yank segments on real kernels using private copies of boot images."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def main():
    dos = Path(os.environ.get(
        'DOS11_SOURCE', Path.home() / 'Projects/DOS/pcdos11-hacking'))
    exitcmd = ROOT.parent / 'cpm86-hacking/pce/pceexit.cmd'
    with tempfile.TemporaryDirectory(prefix='viyankpce.') as directory:
        work = Path(directory)
        env = os.environ.copy()
        env['YANK_TEST_OUTPUT'] = str(work / 'programs')
        run('python3', str(ROOT / 'test/test_yank_runtime.py'), env=env)
        for target, image, config, program, exitprog in (
            ('dos11', dos / 'pcdos_base.img', dos / 'pcdos.cfg',
             'yank.com', dos / 'pce/pceexit.com'),
            ('dosplus', ROOT / 'dosplus.img', ROOT / 'dosplus.cfg',
             'yank.cmd', exitcmd),
            ('dosplus2', ROOT / 'dosplus.img', ROOT / 'dosplus.cfg',
             'yank.exe', exitcmd),
            ('ccpm31', ROOT / 'ccpm86.img', ROOT / 'ccpm86.cfg',
             'yank.cmd', exitcmd),
            ('cdos41', ROOT / 'cdos41.img', ROOT / 'cdos41.cfg',
             'yank.cmd', exitcmd),
        ):
            dest = work / target
            dest.mkdir()
            shutil.copyfile(image, dest / 'boot.img')
            text = config.read_text()
            if target == 'cdos41':
                text = text.replace('size    = 384K', 'size    = 640K')
            text = re.sub(r'^path = .*', f'path = "{config.parent}/rom"',
                          text, count=1)
            text = re.sub(
                r'file\s*=\s*"(?:pcdos_full|cpm86|dosplus|ccpm86|cdos41)\.img"',
                'file = "boot.img"', text)
            text = text.replace('file    = "rom/',
                                f'file    = "{config.parent}/rom/')
            text = text.replace('driver = "sdl"', 'driver = "null"')
            text = re.sub(r'driver\s*=\s*"sdl:lowpass=\d+"',
                          'driver = "null"', text)
            text = re.sub(r'disk \{[^{}]*file\s*= "cpmtest.img"[^{}]*\}',
                          '', text)
            (dest / 'pce.cfg').write_text(text)
            boot = str(dest / 'boot.img')
            cpm = target in ('ccpm31', 'cdos41')
            if cpm:
                ref = ROOT.parent / 'ref'
                twist = str(ref / 'scripts/cpm86twist')
                shutil.copyfile(ref / 'diskdefs', dest / 'diskdefs')
                run(twist, 'untwist', boot, str(dest / 'logical.img'))
                if target == 'cdos41':
                    run('cpmrm', '-f', 'cpm86-320', 'logical.img',
                        '0:vi.cmd', cwd=dest)
                (dest / 'startup.0').write_bytes(b'SUBMIT CHECK\r\n\x1a')
                (dest / 'check.sub').write_bytes(b'YANK\r\nPCEEXIT\r\n\x1a')
                run('cpmcp', '-f', 'cpm86-320', 'logical.img',
                    str(work / 'programs' / program), str(exitprog),
                    'startup.0', 'check.sub', '0:', cwd=dest)
                if target == 'cdos41':
                    (dest / 'startup1.bat').write_bytes(
                        b'YANK\r\nPCEEXIT\r\n\x1a')
                    run('cpmcp', '-f', 'cpm86-320', 'logical.img',
                        'startup1.bat', '0:', cwd=dest)
                run(twist, 'twist', str(dest / 'logical.img'), boot)
            else:
                (dest / 'autoexec.bat').write_bytes(b'YANK\r\nPCEEXIT\r\n')
                for path in (work / 'programs' / program, exitprog,
                             dest / 'autoexec.bat'):
                    run('mcopy', '-o', '-i', boot, str(path),
                        '::' + path.name.upper())
            video = ['-g', 'vga'] if target == 'cdos41' else []
            subprocess.run(
                [os.environ.get('PCE', 'pce-ibmpc'), '-c', 'pce.cfg',
                 '-t', 'null', '-r', '-l', 'pce.log'] + video,
                cwd=dest, timeout=60)
            if cpm:
                run(twist, 'untwist', boot, str(dest / 'result.img'))
                run('cpmcp', '-f', 'cpm86-320', 'result.img',
                    '0:result.txt', 'result.txt', cwd=dest)
                raw = (dest / 'result.txt').read_bytes()
            else:
                raw = subprocess.check_output(
                    ['mtype', '-i', boot, '::RESULT.TXT'])
            report = raw.replace(b'\x1a', b'').decode().strip()
            print(target, report, flush=True)
            assert report == 'VI YANK PASS: 0 failures', report


if __name__ == '__main__':
    main()
