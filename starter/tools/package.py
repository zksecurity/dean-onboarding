#!/usr/bin/env python3
"""Prepare a private project-verification review bundle. No publication or credential issuance."""
import hashlib,json,re,subprocess,sys,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'intake-out'
spec=json.loads((ROOT/'verification.json').read_text())
if spec.get('format')!='dean-verification-intake/v1' or spec.get('visibility')!='private':raise SystemExit('Use a private dean-verification-intake/v1 specification')
slug=spec['project']['slug']
if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug):raise SystemExit('Use a lowercase hyphenated project slug')
subprocess.run([sys.executable,str(ROOT/'tools/check.py')],cwd=ROOT,check=True)
files=set()
for entry in spec['package_include']:
    relative=Path(entry)
    if relative.is_absolute() or '..' in relative.parts:raise SystemExit('Package paths must remain inside the project')
    item=ROOT/relative
    if item.is_symlink() or not item.resolve().is_relative_to(ROOT):raise SystemExit('Refusing a package path outside the project')
    if not item.exists():raise SystemExit('A required package path is missing')
    for path in ([item] if item.is_file() else item.rglob('*')):
        if any(p in {'.git','.lake','.dean','.env','.aws','.ssh','.local','intake-out','__pycache__'} for p in path.relative_to(ROOT).parts):continue
        if path.is_symlink():raise SystemExit('Package only regular files')
        if path.is_file():files.add(path)
archive=OUT/f'{slug}-review.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for path in sorted(files):z.write(path,path.relative_to(ROOT).as_posix())
    z.write(OUT/'local-checks.json','local-checks.json')
    for path in sorted(OUT.glob('*.log')):z.write(path,'authoring-logs/'+path.name)
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
(OUT/'SHA256SUMS').write_text(f'{digest}  {archive.name}\n')
report=json.loads((OUT/'local-checks.json').read_text())
summary='\n'.join(f"- {r['case']}: build {r['build_exit']}, acceptance check {r['check_exit']}" for r in report['cases'])
body=f'''## Verification project\n{spec['project']['title']}\n\n{spec['project']['description']}\n\n## Required targets and environment\n```json\n{json.dumps({k:spec[k] for k in ['project','lean_toolchain','targets','source_policy','verification','requested_resources','controls']},indent=2)}\n```\n\n## Local controls\n{summary}\n\nThese are authoring checks, not a Dean service verdict. The private repository contains review.zip pinned by the request metadata.\n\nReply on this issue for review and setup. Access is delivered only as an encrypted reply bound to this request. Proof snapshots use the Queue API after the verification configuration is enabled.\n'''
(OUT/'proposal.md').write_text(body)
(OUT/'review-email.eml').unlink(missing_ok=True)
print('Private review bundle:',archive,'\nSHA-256:',digest,'\nStatus: prepared locally; run tools/onboard.py submit')
