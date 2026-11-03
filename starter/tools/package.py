#!/usr/bin/env python3
"""Prepare a review bundle and public proposal, or an explicitly private email draft."""
import argparse, email.policy, hashlib, json, re, subprocess, sys, zipfile
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'intake-out'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--private-email', action='store_true', help='Generate an unsent private email; requires a reply email in the specification')
args = parser.parse_args()
spec = json.loads((ROOT / 'dean-challenge.json').read_text())
if spec.get('format') != 'dean-challenge-intake/v1':
    raise SystemExit('Unexpected handoff format')
slug = spec['challenge']['slug']
if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
    raise SystemExit('Use a lowercase hyphenated challenge slug')
if args.private_email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', spec.get('contact', {}).get('email', '')):
    raise SystemExit('A private email proposal needs an actual reply email in contact.email')
subprocess.run([sys.executable, str(ROOT / 'tools/check.py')], check=True)
files = set()
for entry in spec['package_include']:
    relative = Path(entry)
    if relative.is_absolute() or '..' in relative.parts:
        raise SystemExit('Package paths must remain within this project')
    item = ROOT / relative
    if item.is_symlink() or not item.resolve().is_relative_to(ROOT):
        raise SystemExit('Package paths cannot traverse a symlink outside this project')
    if not item.exists():
        raise SystemExit(f'Missing package path: {entry}')
    for path in ([item] if item.is_file() else item.rglob('*')):
        if path.is_symlink():
            raise SystemExit('Package only regular files')
        if path.is_file() and not any(p in {'.git', '.lake', '.env', '.aws', '.ssh', '.local', 'intake-out', '__pycache__'} for p in path.relative_to(ROOT).parts):
            files.add(path)
archive = OUT / f'{slug}-review.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for path in sorted(files):
        z.write(path, path.relative_to(ROOT).as_posix())
    z.write(OUT / 'local-checks.json', 'local-checks.json')
    for path in sorted(OUT.glob('*.log')):
        z.write(path, 'authoring-logs/' + path.name)
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
(OUT / 'SHA256SUMS').write_text(f'{digest}  {archive.name}\n')
report = json.loads((OUT / 'local-checks.json').read_text())
summary = '\n'.join(f"- {r['case']}: build exit {r['build_exit']}, check exit {r['check_exit']}" for r in report['cases'])
body = f'''## Challenge\n{spec['challenge']['title']}\n\n{spec['challenge']['description']}\n\n## Acceptance specification\n```json\n{json.dumps({k: spec[k] for k in ['challenge', 'lean_toolchain', 'target', 'source_policy', 'score', 'requested_resources', 'canaries']}, indent=2)}\n```\n\n## Local authoring controls\n{summary}\n\nThese are local authoring checks, not a Dean service verdict.\n\n## Handoff\n- Integration: Queue API.\n- Local review archive SHA-256: `{digest}`. The archive is retained locally; it is not attached to this issue. The submission tool adds a pinned, public source link below.\n- Reply here for review questions and the onboarding decision. Deliver scoped tokens privately.\n'''
(OUT / 'proposal.md').write_text(body)
(OUT / 'review-email.eml').unlink(missing_ok=True)
if args.private_email:
    contact = spec['contact']
    message = EmailMessage(policy=email.policy.SMTP)
    message['To'] = 'kobi@zksecurity.xyz'
    message['From'] = contact['email']
    message['Reply-To'] = contact['email']
    message['Subject'] = f'Dean private challenge review: {slug}'
    message.set_content(f"Private challenge proposal from {contact.get('name') or contact.get('github') or contact['email']}. Please reply to this email thread.\n\n" + body)
    message.add_attachment(archive.read_bytes(), maintype='application', subtype='zip', filename=archive.name)
    (OUT / 'review-email.eml').write_bytes(message.as_bytes())
    print('Private email draft: intake-out/review-email.eml. NOT SENT. Use an authorized email tool and keep the reply in that thread.')
print(f'Review bundle: {archive}\nSHA-256: {digest}\nProposal: intake-out/proposal.md\nSubmission status: NOT SUBMITTED')
