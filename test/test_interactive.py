#!/usr/bin/env python3
"""Launch shipped editor binaries; verify input, navigation, save, reopen and exit.

One regression step per binary. PCE boots real kernels. ANSI display layout
is not asserted on the supplied VT52 consoles, but input/save/exit are.
No test build or editor internals are substituted.
"""
import argparse
import hashlib
import os
from pathlib import Path
import pty
import re
import select
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
BIN_DIR = Path(os.environ.get('VI_INTERACTIVE_BIN_DIR', ROOT))
PROGRAMS = ('vicp52.cmd','vicp100.cmd','vicpbios.cmd',
            'vid1bios.com','vid1bios.exe','vid2bios.exe')

class Machine:
    def __init__(self, directory):
        self.directory = directory
        self.log = (directory / 'monitor.log').open('wb')
        self.fd, slave = pty.openpty()
        self.process = subprocess.Popen(
            ['pce-ibmpc', '-c', str(directory / 'pce.cfg'), '-t', 'null', '-g', 'vga'],
            cwd=directory, stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)
        try:
            self.wait()
        except Exception:
            self.close()
            raise

    def send(self, command):
        os.write(self.fd, command.encode() + b'\n')

    def wait(self):
        result = bytearray()
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            ready, _, _ = select.select([self.fd], [], [], 0.02)
            if ready:
                block = os.read(self.fd, 65536)
                if not block:
                    raise RuntimeError('PCE closed its monitor')
                self.log.write(block)
                self.log.flush()
                result.extend(block)
            elif result.endswith(b'\n-'):
                return bytes(result)
            if self.process.poll() is not None:
                raise RuntimeError('PCE exited unexpectedly')
        raise TimeoutError('PCE monitor timeout: ' + str(self.directory))

    def command(self, command):
        self.send(command)
        return self.wait()

    def type(self, text):
        for char in text:
            key = {':': '+shift semicolon -shift', '\n': 'return',
                   ' ': 'space', '.': 'period'}.get(char, char)
            self.command('key ' + key)
            self.command('c 80000')

    def memory(self, name, address, size):
        path = self.directory / name
        self.command(f'save {path} bin {address} {size:x}')
        return path.read_bytes()

    def screen(self):
        data = self.memory('screen.bin', 'b800:0', 4000)[::2]
        text = '\n'.join(data[i:i + 80].decode('cp437') for i in range(0, 2000, 80))
        (self.directory / 'screen.txt').write_text(text)
        return text

    def until_screen(self, pattern):
        for _ in range(80):
            self.command('c 100000')
            screen = self.screen()
            if re.search(pattern, screen, re.M):
                return screen
        raise TimeoutError('Expected screen prompt: ' + pattern)

    def close(self):
        try:
            if self.process.poll() is None:
                self.send('q')
                deadline = time.monotonic() + 5
                while self.process.poll() is None and time.monotonic() < deadline:
                    ready, _, _ = select.select([self.fd], [], [], 0.05)
                    if ready:
                        try:
                            self.log.write(os.read(self.fd, 65536))
                        except OSError:
                            break
                if self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                self.process.wait(timeout=5)
        finally:
            os.close(self.fd)
            self.log.close()


def run(*args):
    subprocess.run([str(a) for a in args], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL)

def contents(raw):
    return raw.rstrip(b'\x1a\x00').replace(b'\r\n',b'\n')

def pce_case(base, program, system):
    work=base/system;work.mkdir()
    dos1=system=='dos11'
    fat=dos1 or system=='dosplus'
    shutil.copyfile(ROOT/('pcdos_base.img' if dos1 else system+'.img'),work/'boot.img')
    shutil.copyfile(ROOT/('dosbase.img' if fat else 'cpmbase.img'),work/'disk.img')
    if fat:run('mcopy','-o','-i',work/'disk.img',BIN_DIR/program,'::')
    else:run('cpmcp','-f','ibmpc-514ss',work/'disk.img',BIN_DIR/program,'0:')
    text=(ROOT/(system+'.cfg')).read_text()
    text=re.sub(r'^path = .*',f'path = "{ROOT}/rom"',text,count=1)
    text=re.sub(r'file\s*=\s*"(?:'+system+r'|pcdos)\.img"','file="boot.img"',text)
    text=text.replace('"cpmtest.img"','"disk.img"').replace('"dostest.img"','"disk.img"')
    text=re.sub(r'speed\s*=\s*\d+','speed=24',text,count=1)
    text=re.sub(r'driver\s*=\s*"sdl[^\"]*"','driver="null"',text)
    if system=='cdos41':text=text.replace('size    = 384K','size    = 640K')
    (work/'pce.cfg').write_text(text)
    machine=Machine(work)
    try:
        machine.command('c 3000000');machine.type('b:\n')
        stem=Path(program).stem
        machine.type(stem+' check.txt\n');machine.command('c 1000000')
        screen=machine.screen()
        assert 'Normal Mode' in screen.replace('\n',''), ('startup',system,program,screen)
        machine.type('i');machine.command('c 100000')
        machine.type('hello');machine.command('key esc');machine.command('c 100000')
        screen=machine.screen()
        if program != 'vicp100.cmd':
            assert 'hello' in screen, ('typing',system,program,screen)
        if program == 'vicp100.cmd':
            machine.type('0') # Native fixture sends VT52 Home, not ANSI Home.
        else:
            machine.command('key home')
        machine.command('c 100000')
        machine.type('xi');machine.command('c 100000');machine.type('j')
        machine.command('key esc');machine.command('c 100000')
        if program != 'vicp100.cmd':
            assert 'jello' in machine.screen(), ('navigation',system,program,machine.screen())
        machine.type(':wq\n');machine.command('c 1000000')
        assert re.search(r'^B>\s*$',machine.screen(),re.M), ('exit',system,program,machine.screen())
        machine.type(stem+' check.txt\n');machine.command('c 1000000')
        screen=machine.screen().replace('\n','')
        assert 'Normal Mode' in screen and 'jello' in screen, ('reopen',system,program,screen)
        machine.type(':q\n');machine.command('c 1000000')
        assert re.search(r'^B>\s*$',machine.screen(),re.M), ('second exit',system,program,machine.screen())
    finally:machine.close()
    if fat:run('mcopy','-o','-i',work/'disk.img','::CHECK.TXT',work/'saved.txt')
    else:run('cpmcp','-f','ibmpc-514ss',work/'disk.img','0:check.txt',work/'saved.txt')
    assert contents((work/'saved.txt').read_bytes()) == b'jello\n'
    print(program,system,'PASS: startup, typing, navigation, edit, save, reopen, exit',flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('program',choices=PROGRAMS)
    parser.add_argument('--system',help='Run one native OS fixture for diagnosis')
    args=parser.parse_args()
    artifacts=os.environ.get('VI_INTERACTIVE_ARTIFACTS')
    if artifacts:Path(artifacts).mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='vi-interactive-',dir=artifacts))
    print('Artifacts:',work,flush=True)
    print('Binary SHA256:',hashlib.sha256((BIN_DIR/args.program).read_bytes()).hexdigest(),flush=True)
    systems=(('cpm86','ccpm86','dosplus','cdos41') if args.program.endswith('.cmd') else
             ('dos11',) if args.program.startswith('vid1') else ('dosplus','cdos41'))
    for system in ([args.system] if args.system else systems):pce_case(work,args.program,system)
    shutil.rmtree(work)

if __name__=='__main__':main()
