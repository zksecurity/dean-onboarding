#!/usr/bin/env python3
"""Submit a public proposal to Dean and retrieve the team's response using GitHub CLI."""
import argparse, hashlib, json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'intake-out'
INBOX = 'zksecurity/dean-challenges'
RECEIPT = OUT / 'submission-receipt.json'


def run(*args):
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise SystemExit(result.stderr.strip() or f'{args[0]} failed')
    return result.stdout.strip()


def api(path, paginate=False):
    flags = ['--paginate', '--slurp'] if paginate else []
    return json.loads(run('gh', 'api', *flags, path))


def issue_number(url):
    match = re.fullmatch(r'https://github.com/zksecurity/dean-challenges/issues/(\d+)', url)
    if not match:
        raise SystemExit('Expected an issue URL in zksecurity/dean-challenges')
    return match[1]


def submit(source, commit):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', source) or not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise SystemExit('Provide OWNER/REPO and a complete 40-character commit SHA')
    repository = api(f'repos/{source}')
    if repository.get('private') or repository.get('visibility') not in (None, 'public'):
        raise SystemExit('Source repository is private. Use the private-email route; this tool never changes repository visibility.')
    canonical = repository['full_name']
    if api(f'repos/{canonical}/commits/{commit}').get('sha') != commit:
        raise SystemExit('The pinned source commit was not found')
    if run('git', 'rev-parse', 'HEAD') != commit:
        raise SystemExit('Local HEAD differs from the proposed public commit')
    if run('git', 'status', '--porcelain', '--untracked-files=normal', '--', '.'):
        raise SystemExit('Commit the challenge files before submitting; generated intake-out files should remain ignored')
    spec = json.loads((ROOT / 'dean-challenge.json').read_text())
    if spec.get('visibility', 'public') != 'public':
        raise SystemExit('This challenge is marked private; use the private-email route')
    subprocess.run([sys.executable, str(ROOT / 'tools/package.py')], cwd=ROOT, check=True)
    with __import__('zipfile').ZipFile(OUT / f'{spec["challenge"]["slug"]}-review.zip') as archive:
        for name in archive.namelist():
            if name == 'local-checks.json' or name.startswith('authoring-logs/'):
                continue
            run('git', 'ls-files', '--error-unmatch', '--', name)
    marker = 'dean-proposal:' + hashlib.sha256(f'{canonical}@{commit}:{spec["challenge"]["slug"]}'.encode()).hexdigest()
    # Reuse an existing issue for an exact proposal, including after a lost response.
    issues = [issue for page in api(f'repos/{INBOX}/issues?state=all&per_page=100', True) for issue in page]
    existing = next((issue for issue in issues if not issue.get('pull_request') and marker in (issue.get('body') or '')), None)
    if existing:
        url = existing['html_url']
    else:
        prefix = run('git', 'rev-parse', '--show-prefix').strip('/')
        source_url = f'https://github.com/{canonical}/tree/{commit}' + ('/' + prefix if prefix else '')
        body = (OUT / 'proposal.md').read_text() + f'\n## Pinned public source\n{source_url}\n\n<!-- {marker} -->\n'
        (OUT / 'proposal.md').write_text(body)
        with tempfile.TemporaryDirectory(prefix='dean-proposal-') as temporary:
            body_file = Path(temporary) / 'body.md'
            body_file.write_text(body)
            url = run('gh', 'issue', 'create', '--repo', INBOX, '--title', f'Challenge proposal: {spec["challenge"]["slug"]}', '--body-file', str(body_file), '--label', 'proposal', '--label', 'needs-review')
    number = issue_number(url)
    OUT.mkdir(exist_ok=True)
    receipt = {'status': 'submitted-for-review', 'issue_url': url, 'issue_number': int(number), 'source_repository': canonical, 'source_commit': commit, 'review_status': 'pending', 'credential_delivery': 'private; never in public issue'}
    RECEIPT.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


def status(url):
    number = issue_number(url)
    issue = api(f'repos/{INBOX}/issues/{number}')
    comments = [comment for page in api(f'repos/{INBOX}/issues/{number}/comments?per_page=100', True) for comment in page]
    labels = [label['name'] for label in issue['labels']]
    # Labels are set by repository maintainers. Closing an issue alone is not approval.
    decision = next((name for name in ['declined', 'accepted-for-onboarding', 'needs-info', 'in-review'] if name in labels), 'awaiting-review')
    output = {'issue_url': url, 'issue_state': issue['state'], 'review_status': decision, 'labels': labels,
              'comments': [{'author': c['user']['login'], 'association': c['author_association'], 'created_at': c['created_at'], 'body': c['body']} for c in comments],
              'next_step': 'Read maintainer replies; respond on this issue. Accepted for onboarding does not mean production is active. Receive scoped API access privately.'}
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('submit', help='Publish the authorized proposal using an already public pinned source repository')
    create.add_argument('--source-repo', required=True, help='OWNER/REPO, public and accessible to reviewers')
    create.add_argument('--commit', required=True, help='Full commit SHA matching local HEAD')
    inspect = sub.add_parser('status', help='Retrieve the review labels and conversation')
    inspect.add_argument('--issue', help='Issue URL; otherwise use the saved submission receipt')
    args = parser.parse_args()
    if args.command == 'submit':
        submit(args.source_repo, args.commit)
    else:
        url = args.issue or (json.loads(RECEIPT.read_text())['issue_url'] if RECEIPT.exists() else None)
        if not url:
            raise SystemExit('Supply --issue or use a project with intake-out/submission-receipt.json')
        status(url)
