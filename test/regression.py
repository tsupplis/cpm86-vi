#!/usr/bin/env python3
"""Run the complete correctness regression once, with consolidated results."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = (
    'vicp52.cmd', 'vicp100.cmd', 'vicpbios.cmd',
    'vid1bios.com', 'vid1bios.exe', 'vid2bios.exe',
)
SUITES = (
    ('keys', 'test_keys.py'),
    ('scroll', 'test_scroll.py'),
    ('save-host', 'test_save.py'),
    ('editor-state', 'test_editor_state.py'),
    ('eof-lines', 'test_eof_lines.py'),
    ('vt-output', 'test_vt_output.py'),
    ('characters', 'test_characters.py'),
    ('capacity-runtime', 'test_capacity_runtime.py'),
    ('io-runtime', 'test_io_runtime.py'),
    ('yank-lengths', 'test_yank_lengths.py'),
    ('navigation-runtime', 'test_navigation_runtime.py'),
    ('yank-runtime', 'test_yank_runtime.py'),
    ('buffer-runtime', 'test_buffer_runtime.py'),
    ('save-pce', 'test_save_pce.py'),
    ('yank-pce', 'test_yank_pce.py'),
    ('dos1-pce', 'test_dos1_pce.py'),
    ('display-compat', 'test_display_pce.py', '--compat-only'),
    ('vt-compat', 'test_vt_pce.py', '--compat-only'),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        help='New directory for logs and summary.json (default: temporary directory)')
    args = parser.parse_args()
    if args.output is None:
        output = Path(tempfile.mkdtemp(prefix='vi-regression-'))
    else:
        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=False)

    report = {
        'revision': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'worktree': subprocess.check_output(
            ['git', 'status', '--short'], cwd=ROOT, text=True),
        'overall': 'INCOMPLETE',
        'results': [],
    }
    steps = [('build-six-formats', ['make', '-j1', '-B', *PROGRAMS])]
    steps.extend((name, [sys.executable, '-B', 'test/' + script, *flags])
                 for name, script, *flags in SUITES)
    steps.insert(7, ('save-runtime', ['sh', 'test/saveruntime']))
    summary = output / 'summary.json'
    summary.write_text(json.dumps(report, indent=2) + '\n')
    print(f'Regression: {len(steps)} steps, sequential, no retries or benchmarks', flush=True)
    print(f'Logs: {output}', flush=True)

    with tempfile.TemporaryDirectory(prefix='vi-regression-compiler-') as compiler:
        env = os.environ.copy()
        env['TMPDIR'] = compiler
        env['PYTHONUNBUFFERED'] = '1'
        for index, (name, command) in enumerate(steps, 1):
            log = output / (name + '.log')
            print(f'[{index}/{len(steps)}] {name}', flush=True)
            started = time.monotonic()
            with log.open('w') as stream:
                stream.write('$ ' + shlex.join(command) + '\n')
                stream.flush()
                try:
                    result = subprocess.run(
                        command, cwd=ROOT, env=env, stdout=stream,
                        stderr=subprocess.STDOUT, check=False)
                    exit_code = result.returncode
                except OSError as error:
                    stream.write(f'Cannot run command: {error}\n')
                    exit_code = 127
            entry = {
                'name': name,
                'command': command,
                'exit_code': exit_code,
                'status': 'PASS' if exit_code == 0 else 'FAIL',
                'seconds': round(time.monotonic() - started, 1),
                'log': str(log),
            }
            report['results'].append(entry)
            summary.write_text(json.dumps(report, indent=2) + '\n')
            print(f"  {entry['status']} (exit {exit_code}, {entry['seconds']}s)",
                  flush=True)

    failures = [entry for entry in report['results'] if entry['exit_code'] != 0]
    report['overall'] = 'FAIL' if failures else 'PASS'
    summary.write_text(json.dumps(report, indent=2) + '\n')
    print(f"\n{report['overall']}: {len(steps) - len(failures)}/{len(steps)} steps passed")
    for entry in failures:
        print(f"FAIL: {entry['name']} -- {entry['log']}")
    print(f'Summary: {summary}')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
