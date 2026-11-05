#!/usr/bin/env python3
"""Measure VT52 on native XIOS; compare complete old/new BDOS byte streams."""
from pathlib import Path
import re
import sys
import tempfile

from test_buffer_runtime import ROOT, build
from test_display_pce import run_probe


def main():
    baseline = '--baseline' in sys.argv[1:]
    timing = '--compat-only' not in sys.argv[1:]
    with tempfile.TemporaryDirectory(prefix='vi-vt-pce-') as directory:
        work = Path(directory)
        build(work, ('vicp52.cmd',), (ROOT / 'test/vtprobe.c').read_text())
        for kernel, video in (('dosplus', 'cga'), ('cdos41', 'vga')):
            name = kernel + '-vt52'
            if timing:
                report = run_probe(work, name + '-compat', ROOT / (kernel + '.img'),
                                   ROOT / (kernel + '.cfg'),
                                   ROOT.parent / 'cpm86-hacking/pce/pceexit.cmd',
                                   'vicp52.cmd', video, timing=False)
                assert report.startswith('VI VT PASS'), report
            report = run_probe(work, name, ROOT / (kernel + '.img'),
                               ROOT / (kernel + '.cfg'),
                               ROOT.parent / 'cpm86-hacking/pce/pceexit.cmd',
                               'vicp52.cmd', video, timing=timing)
            assert report.startswith('VI VT PASS'), report
            cases = re.findall(r'(\d) ticks (\d+) (\d+) bytes (\d+)', report)
            assert len(cases) == 4, report
            before = after = 0
            for case, old, new, length in cases:
                assert int(length) > 0, report
                if timing and case == '2':
                    assert int(new) <= int(old) + 2, report
                else:
                    before += int(old)
                    after += int(new)
            if timing:
                print(f'{name}: bulk ticks {before} -> {after}', flush=True)
                if not baseline:
                    assert after + 2 < before, report


if __name__ == '__main__':
    main()
