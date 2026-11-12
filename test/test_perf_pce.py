#!/usr/bin/env python3
"""One bounded 8088 baseline; report coarse ticks, fixture hashes and build sizes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import tempfile

from test_buffer_runtime import ROOT, PROGRAMS, build, run
from test_display_pce import run_probe

EXPECTED = {
    'load': 1, 'save': 1, 'middle_read': 1, 'beginning_edit': 8,
    'scroll': 2, 'longline_cursor': 8, 'search_miss': 4,
}


def parse_report(report):
    assert report.startswith('VI PERF PASS\n'), report
    assert re.search(r'^capacity 42112 spare 4096$', report, re.M), report
    cases = re.findall(r'^(\w+) ticks (\d+) repeats (\d+)$', report, re.M)
    assert len(cases) == len(EXPECTED), report
    assert {name: int(count) for name, _, count in cases} == EXPECTED, report
    return {name: {'ticks': int(ticks), 'repeats': int(count)}
            for name, ticks, count in cases}


def build_sizes():
    sizes = {}
    for name in PROGRAMS:
        data = (ROOT / name).read_bytes()
        entry = {'file_bytes': len(data),
                 'sha256': hashlib.sha256(data).hexdigest()}
        if name.endswith('.cmd'):
            groups = {}
            for index, label in enumerate(('code', 'data', 'extra')):
                kind, length, base, minimum, maximum = struct.unpack_from(
                    '<BHHHH', data, index * 9)
                assert kind == index + 1 and base == 0, (name, label)
                groups[label] = {'image_bytes': length * 16,
                                 'minimum_bytes': minimum * 16,
                                 'maximum_bytes': maximum * 16}
            entry['cmd_groups'] = groups
        elif name.endswith('.exe'):
            header = struct.unpack_from('<14H', data)
            assert header[0] == 0x5a4d, name
            image_start = header[4] * 16
            entrypoint = image_start + header[11] * 16 + header[10]
            # These Aztec small-model stubs start with MOV BP,dataseg.
            assert data[entrypoint] == 0xbd, name
            data_segment = struct.unpack_from('<H', data, entrypoint + 1)[0]
            assert data_segment == header[7] and header[11] == 0, name
            entry['mz_load_image_bytes'] = len(data) - image_start
            entry['code_image_bytes'] = data_segment * 16
            entry['data_image_bytes'] = len(data) - image_start - data_segment * 16
            assert entry['data_image_bytes'] >= 0, name
            entry['mz_initial_ss_bytes'] = header[7] * 16
            entry['mz_initial_sp'] = header[8]
        else:
            assert data[:2] != b'MZ', name
            entry['combined_code_data_image_bytes'] = len(data)
        sizes[name] = entry
    return sizes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        help='Save the validated baseline as JSON')
    args = parser.parse_args()
    sizes = build_sizes()
    dos = Path(os.environ.get(
        'DOS11_SOURCE', Path.home() / 'Projects/DOS/pcdos11-hacking'))
    base = bytes(10 if i % 64 == 63 else 97 + i // 64 % 23
                 for i in range(4096))
    payloads = {'BASE.TXT': base, 'IMPORT.TXT': b'X' * 128}
    with tempfile.TemporaryDirectory(prefix='vi-perf-') as directory:
        work = Path(directory)
        # Isolate Aztec's global compiler temporary path as well as output files.
        with tempfile.TemporaryDirectory(prefix='vi-perf-compiler-') as compiler:
            previous = os.environ.get('TMPDIR')
            os.environ['TMPDIR'] = compiler
            try:
                build(work, ('vid1bios.exe',), (ROOT / 'test/perfprb.c').read_text())
            finally:
                if previous is None:
                    del os.environ['TMPDIR']
                else:
                    os.environ['TMPDIR'] = previous
        inputs = []
        for name, data in payloads.items():
            path = work / name
            path.write_bytes(data)
            inputs.append((path, name))
        report = run_probe(work, 'dos11-perf', dos / 'pcdos_base.img',
                           dos / 'pcdos.cfg', dos / 'pce/pceexit.com',
                           'vid1bios.exe', 'cga', ram=256, timing=True,
                           inputs=inputs, timeout=60)
        results = parse_report(report)
        saved = run(['mtype', '-i', 'boot.img', '::SAVED.TXT'],
                    work / 'dos11-perf').stdout.encode()
        assert saved == base, 'Saved fixture differs from input'
    commit = run(['git', 'rev-parse', 'HEAD'], ROOT).stdout.strip()
    state = run(['git', 'status', '--porcelain', '--untracked-files=normal'], ROOT)
    record = {
        'schema_version': 1,
        'source_commit': commit,
        'worktree_dirty': bool(state.stdout.strip()),
        'profile': {'kernel': 'PC-DOS 1.1', 'program': 'vid1bios.exe',
                    'cpu': '8088', 'speed': 1, 'video': 'cga', 'ram_kib': 256,
                    'timeout_seconds': 60, 'timer': 'BIOS 18.2 Hz low-word ticks'},
        'fixtures': {name: {'bytes': len(data),
                            'sha256': hashlib.sha256(data).hexdigest()}
                     for name, data in payloads.items()},
        'probe_sha256': hashlib.sha256(
            (ROOT / 'test/perfprb.c').read_bytes()).hexdigest(),
        'machine_fixture_sha256': {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in (('boot_image', dos / 'pcdos_base.img'),
                               ('source_config', dos / 'pcdos.cfg'))},
        'results': results,
        'held_spare_heap_bytes': 4096,
        'production_builds': sizes,
        'scope': [
            'One short sample per case; coarse ticks, not a statistical benchmark.',
            'Load/read include status output; save includes flush/truncate/close.',
            'Beginning edit is eight insert/delete primitive pairs without redraw.',
            'Scroll includes viewport/render/output for two one-line moves.',
            'Long-line cursor excludes redraw; failed searches include status output.',
            'Display A/B measurements and six-variant heap budgets are reused, not rerun.',
            'Header sizes describe load images, not maximum available heap.',
        ],
    }
    text = json.dumps(record, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    print(text)


if __name__ == '__main__':
    main()
