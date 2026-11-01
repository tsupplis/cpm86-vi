#!/usr/bin/env python3
"""Run saveprobe against real DOS 1.1 and DOS Plus kernels, on private images."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
def run(*args, **kwargs):
    return subprocess.run(args,check=True,**kwargs)
def main():
    dos=Path(os.environ.get('DOS11_SOURCE',Path.home()/'Projects/DOS/pcdos11-hacking'))
    with tempfile.TemporaryDirectory(prefix='visavepce.') as directory:
        work=Path(directory); env=os.environ.copy();env['SAVE_TEST_OUTPUT']=str(work/'programs')
        run('sh',str(ROOT/'test/saveruntime'),env=env)
        for target,source,cfg,program,exitprog in (
            ('dos11',dos/'pcdos_base.img',dos/'pcdos.cfg','save.com',dos/'pce/pceexit.com'),
            ('dosplus',ROOT/'dosplus.img',ROOT/'dosplus.cfg','save.cmd',ROOT.parent/'cpm86-hacking/pce/pceexit.cmd')):
            dest=work/target;dest.mkdir();shutil.copyfile(source,dest/'boot.img')
            text=cfg.read_text()
            text=text.replace('path = "rom"',f'path = "{cfg.parent}/rom"')
            text=text.replace('file    = "rom/',f'file    = "{cfg.parent}/rom/')
            text=text.replace('file     = "pcdos_full.img"','file     = "boot.img"')
            text=text.replace('file     = "dosplus.img"','file     = "boot.img"')
            text=text.replace('driver = "sdl"','driver = "null"')
            text=text.replace('driver      = "sdl:lowpass=0"','driver      = "null"')
            text=text.replace('driver      = "sdl:lowpass=5000"','driver      = "null"')
            (dest/'pce.cfg').write_text(text)
            (dest/'autoexec.bat').write_bytes(b'SAVE\r\nPCEEXIT\r\n')
            image=str(dest/'boot.img')
            for p in (work/'programs'/program,exitprog,dest/'autoexec.bat'):
                run('mcopy','-o','-i',image,str(p),'::'+p.name.upper())
            # PCEEXIT returns 0 or 1; require the on-disk guest result instead.
            subprocess.run([os.environ.get('PCE','pce-ibmpc'),'-c','pce.cfg','-t','null','-r','-l','pce.log'],cwd=dest,timeout=60)
            report=subprocess.check_output(['mtype','-i',image,'::RESULT.TXT']).replace(b'\x1a',b'').decode()
            print(target,report.strip())
            assert report.strip()=='VI SAVE PASS: 0 failures',report
if __name__=='__main__':main()
