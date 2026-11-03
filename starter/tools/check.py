#!/usr/bin/env python3
"""Authoring checks only. Dean independently verifies the package during onboarding."""
import json, shutil, subprocess, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'intake-out'
OUT.mkdir(exist_ok=True)
REPORT = OUT / 'local-checks.json'
REPORT.unlink(missing_ok=True)  # A failed rerun must never leave an earlier pass report.


def command(args, cwd, log):
    start = time.monotonic()
    try:
        p = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=1800)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f'Unable to complete authoring check: {type(exc).__name__}') from exc
    (OUT / log).write_text(p.stdout)
    return p.returncode, p.stdout, round(time.monotonic() - start, 3)


spec = json.loads((ROOT / 'verification.json').read_text())
if (ROOT / 'lean-toolchain').read_text().strip() != spec['lean_toolchain']:
    raise SystemExit('lean-toolchain differs from the handoff specification')
rows = []
with tempfile.TemporaryDirectory(prefix='dean-verification-') as temporary:
    for name, fixture in [('known-good', ROOT / 'Proof.lean'),
                          ('known-bad', ROOT / 'fixtures/known-bad/Proof.lean'),
                          ('wrong-statement', ROOT / 'fixtures/wrong-statement/Proof.lean')]:
        project = Path(temporary) / name
        shutil.copytree(ROOT, project, ignore=shutil.ignore_patterns('.git', '.lake', 'intake-out', '__pycache__'))
        shutil.copyfile(fixture, project / 'Proof.lean')
        build, _, build_seconds = command(['lake', 'build'], project, f'{name}-build.log')
        if build != 0:
            raise SystemExit(f'{name}: compilation failed; inspect intake-out/{name}-build.log. This is not a valid negative-control result.')
        result, output, check_seconds = command(['lake', 'env', 'lean', 'checks/Acceptance.lean'], project, f'{name}-check.log')
        if name == 'known-good':
            passed = result == 0
        elif name == 'known-bad':
            passed = result != 0 and 'UNPERMITTED_AXIOM' in output and 'sorryAx' in output
        else:
            passed = result != 0 and any(t in output.lower() for t in ['type mismatch', 'has type'])
        if not passed:
            raise SystemExit(f'{name}: unexpected acceptance-check result; inspect its check log')
        rows.append({'case': name, 'build_exit': build, 'check_exit': result,
                     'build_seconds': build_seconds, 'check_seconds': check_seconds})
        print(f'{name}: expected result observed')
report = {'status': 'passed', 'scope': 'local authoring checks; not a Dean service verdict',
          'toolchain': spec['lean_toolchain'], 'cases': rows}
REPORT.write_text(json.dumps(report, indent=2) + '\n')
print('All local authoring checks passed. Report: intake-out/local-checks.json')
