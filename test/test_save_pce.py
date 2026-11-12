#!/usr/bin/env python3
"""Run saveprobe against real DOS and Concurrent CP/M kernels, on private images."""
from pathlib import Path
import os
import re
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
            ('dosplus',ROOT/'dosplus.img',ROOT/'dosplus.cfg','save.cmd',ROOT.parent/'cpm86-hacking/pce/pceexit.cmd'),
            ('ccpm31',ROOT/'ccpm86.img',ROOT/'ccpm86.cfg','save.cmd',ROOT.parent/'cpm86-hacking/pce/pceexit.cmd'),
            ('cdos41',ROOT/'cdos41.img',ROOT/'cdos41.cfg','save.cmd',ROOT.parent/'cpm86-hacking/pce/pceexit.cmd')):
            dest=work/target;dest.mkdir();shutil.copyfile(source,dest/'boot.img')
            text=cfg.read_text()
            if target=='cdos41':
                text=text.replace('size    = 384K','size    = 640K')
            text=re.sub(r'^path = .*',f'path = "{cfg.parent}/rom"',text,count=1)
            for boot in ('ccpm86.img','cdos41.img'):
                text=text.replace(f'file     = "{boot}"','file     = "boot.img"')
            text=text.replace('path = "rom"',f'path = "{cfg.parent}/rom"')
            text=text.replace('file    = "rom/',f'file    = "{cfg.parent}/rom/')
            text=text.replace('file     = "pcdos_full.img"','file     = "boot.img"')
            text=text.replace('file     = "dosplus.img"','file     = "boot.img"')
            text=text.replace('driver = "sdl"','driver = "null"')
            text=text.replace('driver      = "sdl:lowpass=0"','driver      = "null"')
            text=text.replace('driver      = "sdl:lowpass=5000"','driver      = "null"')
            text=re.sub(r'disk \{[^{}]*file\s*= \"cpmtest.img\"[^{}]*\}', '', text)
            (dest/'pce.cfg').write_text(text)
            command=b'SAVE' if target=='dos11' else b'SAVE LRBC'
            image=str(dest/'boot.img')
            cpm=target in ('ccpm31','cdos41')
            if cpm:
                ref=ROOT.parent/'ref'
                twist=str(ref/'scripts/cpm86twist')
                shutil.copyfile(ref/'diskdefs',dest/'diskdefs')
                run(twist,'untwist',image,str(dest/'logical.img'))
                if target=='cdos41':
                    # Free space for the probe and its output on this private copy.
                    run('cpmrm','-f','cpm86-320','logical.img','0:vi.cmd',cwd=dest)
                (dest/'startup.0').write_bytes(b'SUBMIT CHECK\r\n\x1a')
                (dest/'check.sub').write_bytes(command+b'\r\nPCEEXIT\r\n\x1a')
                run('cpmcp','-f','cpm86-320','logical.img',str(work/'programs'/program),str(exitprog),'startup.0','check.sub','0:',cwd=dest)
                if target=='cdos41':
                    (dest/'startup1.bat').write_bytes(command+b'\r\nPCEEXIT\r\n\x1a')
                    run('cpmcp','-f','cpm86-320','logical.img','startup1.bat','0:',cwd=dest)
                run(twist,'twist',str(dest/'logical.img'),image)
            else:
                if target=='dosplus':
                    # The stock image has only 15 KiB free. Leave room for the
                    # larger probe, old/new save files and the result report.
                    # This removes an unused editor from the private copy only.
                    run('mdel','-i',image,'::DOSPLUS/ED.CMD')
                (dest/'autoexec.bat').write_bytes(command+b'\r\nPCEEXIT\r\n')
                for p in (work/'programs'/program,exitprog,dest/'autoexec.bat'):
                    run('mcopy','-o','-i',image,str(p),'::'+p.name.upper())
            # PCEEXIT returns 0 or 1; require the on-disk guest result instead.
            video=['-g','vga'] if target=='cdos41' else []
            subprocess.run([os.environ.get('PCE','pce-ibmpc'),'-c','pce.cfg','-t','null','-r','-l','pce.log']+video,cwd=dest,timeout=60)
            if cpm:
                run(twist,'untwist',image,str(dest/'result.img'))
                run('cpmcp','-f','cpm86-320','result.img','0:result.txt','result.txt',cwd=dest)
                raw=(dest/'result.txt').read_bytes()
            else:
                raw=subprocess.check_output(['mtype','-i',image,'::RESULT.TXT'])
            report=raw.replace(b'\x1a',b'').decode()
            print(target,report.strip())
            assert report.strip()=='VI SAVE PASS: 0 failures',report
if __name__=='__main__':main()
