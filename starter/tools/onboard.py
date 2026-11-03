#!/usr/bin/env python3
"""Requester agent: submit a private project, read review, receive encrypted Queue API access."""
import argparse,hashlib,json,shutil,subprocess,sys,tempfile,uuid
from pathlib import Path
import onboarding_lib as lib

ROOT=Path(__file__).resolve().parents[1]


def submit(name=None):
    actor=lib.github('user')
    reviewer=lib.github('users/'+lib.REVIEWER)
    if reviewer['id']!=lib.REVIEWER_ID:raise SystemExit('Reviewer identity changed; verify the onboarding instructions')
    spec=json.loads((ROOT/'verification.json').read_text())
    subprocess.run([sys.executable,str(ROOT/'tools/package.py')],cwd=ROOT,check=True)
    directory=lib.local_state(ROOT);_,recipient=lib.identity(directory)
    receipt_file=directory/'onboarding.json'
    previous=json.loads(receipt_file.read_text()) if receipt_file.exists() else {}
    name=name or previous.get('repository') or actor['login']+'/dean-onboarding-'+spec['project']['slug']
    if '/' not in name:name=actor['login']+'/'+name
    if not lib.REPO_RE.fullmatch(name):raise SystemExit('Use OWNER/dean-onboarding-PROJECT')
    try:repository=lib.private_repo(name)
    except lib.GitHubError as error:
        if not error.missing:raise
        lib.command(['gh','repo','create',name,'--private','--description','Private Dean verification onboarding'])
        repository=lib.private_repo(name)
    name=repository['full_name']
    if not repository.get('permissions',{}).get('admin'):raise SystemExit('Repository administration access is required to invite the reviewer')
    if previous and previous['repository']!=name:raise SystemExit('This local identity is already bound to another onboarding repository')
    request_id=previous.get('request_id') or str(uuid.uuid4())
    archive=ROOT/'intake-out'/f'{spec["project"]["slug"]}-review.zip'
    if archive.stat().st_size>50*1024*1024:raise SystemExit('Review archive exceeds 50 MiB; pin dependencies instead of bundling build outputs')
    metadata={'format':'dean-private-verification/v1','repository':name,'request_id':request_id,
              'requester':actor['login'],'reviewer':lib.REVIEWER,'reviewer_id':lib.REVIEWER_ID,
              'recipient':recipient,'package_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
    lib.secure_write(receipt_file,(json.dumps({**previous,**metadata,'status':'preparing-private-submission'},indent=2)+'\n').encode())
    with tempfile.TemporaryDirectory(prefix='dean-private-submit-') as temporary:
        checkout=Path(temporary)/'repo'
        lib.command(['gh','repo','clone',name,str(checkout)])
        existing=checkout/'dean-onboarding.json'
        if existing.exists():
            old=json.loads(existing.read_text())
            if old.get('request_id')!=request_id or old.get('recipient')!=recipient:raise SystemExit('Existing repository belongs to another request or key; preserve local .dean state')
        elif any(p.name!='.git' for p in checkout.iterdir()):raise SystemExit('Use a dedicated empty onboarding repository')
        shutil.copyfile(archive,checkout/'review.zip')
        (checkout/'dean-onboarding.json').write_text(json.dumps(metadata,indent=2)+'\n')
        lib.command(['git','config','user.name',actor['login']],cwd=checkout)
        lib.command(['git','config','user.email',f'{actor["id"]}+{actor["login"]}@users.noreply.github.com'],cwd=checkout)
        lib.command(['git','checkout','-B','main'],cwd=checkout)
        lib.command(['git','add','review.zip','dean-onboarding.json'],cwd=checkout)
        staged=lib.command(['git','diff','--cached','--name-only'],cwd=checkout)
        if staged:lib.command(['git','commit','-m','Submit verification project for private onboarding'],cwd=checkout)
        commit=lib.command(['git','rev-parse','HEAD'],cwd=checkout)
        lib.private_repo(name)  # Recheck before every publication.
        lib.command(['git','push','--set-upstream','origin','main'],cwd=checkout)
    request={**metadata,'commit':commit}
    body=lib.packet(lib.REQUEST_MARKER,request)+'\n'+(ROOT/'intake-out/proposal.md').read_text()
    lib.private_repo(name)
    if previous.get('issue_url'):
        repo,number=lib.issue_parts(previous['issue_url'])
        lib.github(f'repos/{repo}/issues/{number}','PATCH',{'body':body})
        issue_url=previous['issue_url']
    else:
        marker=f'"request_id": "{request_id}"'
        matches=[i for i in lib.pages(f'repos/{name}/issues?state=all&per_page=100') if not i.get('pull_request') and marker in (i.get('body') or '')]
        if matches:
            issue_url=matches[0]['html_url'];_,number=lib.issue_parts(issue_url)
            lib.github(f'repos/{name}/issues/{number}','PATCH',{'body':body})
        else:issue_url=lib.github(f'repos/{name}/issues','POST',{'title':'Verification onboarding: '+spec['project']['slug'],'body':body})['html_url']
    receipt={**request,'issue_url':issue_url,'status':'submitted-for-private-review'}
    lib.secure_write(receipt_file,(json.dumps(receipt,indent=2)+'\n').encode())
    if actor['id']!=lib.REVIEWER_ID:
        lib.private_repo(name)
        lib.github(f'repos/{name}/collaborators/{lib.REVIEWER}','PUT',{'permission':'push'})
    print('Private onboarding submitted:',issue_url)
    print('Receipt:',receipt_file,'\nKeep .dean/ locally; it contains the key needed to receive access.')


def receipt():
    path=ROOT/'.dean/onboarding.json'
    if not path.exists():raise SystemExit('Run submit first or restore the existing .dean onboarding state')
    value=json.loads(path.read_text())
    if not value.get('issue_url'):raise SystemExit('Submission is not complete; rerun submit to resume safely')
    return value


def status():
    local=receipt();repo,number,issue,request=lib.read_request(local['issue_url'],verify_archive=False)
    comments=lib.pages(f'repos/{repo}/issues/{number}/comments?per_page=100')
    visible=[]
    for comment in comments:
        if lib.ACCESS_MARKER in (comment.get('body') or ''):
            visible.append({'author':comment['user']['login'],'encrypted_access_reply':True})
        else:visible.append({'author':comment['user']['login'],'body':comment.get('body','')})
    print(json.dumps({'issue_url':local['issue_url'],'state':issue['state'],
        'labels':[x['name'] for x in issue.get('labels',[])],'comments':visible,
        'next_step':'Reply on this private issue. Run receive when the trusted reviewer posts encrypted access.'},indent=2))


def receive():
    local=receipt();repo,number,_,request=lib.read_request(local['issue_url'],verify_archive=False)
    for key in ['request_id','commit','recipient']:
        if local[key]!=request[key]:raise SystemExit('The private request changed; resubmit/review before receiving access')
    comments=lib.pages(f'repos/{repo}/issues/{number}/comments?per_page=100')
    candidates=[]
    for comment in comments:
        if comment['user']['id']!=lib.REVIEWER_ID or lib.ACCESS_MARKER not in (comment.get('body') or ''):continue
        value=lib.parse_packet(comment['body'],lib.ACCESS_MARKER)
        if all(value.get(k)==local[k] for k in ['request_id','commit','recipient']):candidates.append((comment['id'],value))
    if not candidates:raise SystemExit('No matching encrypted access from the trusted Dean reviewer yet')
    comment_id,envelope=max(candidates,key=lambda item:item[0])
    if comment_id<local.get('last_access_comment_id',0):raise SystemExit('Refusing older access delivery')
    identity=ROOT/'.dean/identity.txt'
    if identity.is_symlink() or identity.stat().st_mode&0o077:raise SystemExit('The local identity must be private (mode 0600)')
    plaintext=lib.command(['age','--decrypt','--identity',str(identity)],data=envelope['ciphertext'].encode(),binary=True)
    try:delivery=json.loads(plaintext)
    except (ValueError,TypeError):raise SystemExit('Decrypted access is not valid JSON')
    if any(delivery.get(k)!=local[k] for k in ['request_id','commit','repository']):raise SystemExit('Encrypted access belongs to another request')
    lib.validate_access(delivery.get('access'))
    access_file=ROOT/'.dean/access.json'
    lib.secure_write(access_file,(json.dumps(delivery['access'],indent=2)+'\n').encode())
    local.update(last_access_comment_id=comment_id,status='access-received; run the agreed Queue API smoke test')
    lib.secure_write(ROOT/'.dean/onboarding.json',(json.dumps(local,indent=2)+'\n').encode())
    print('Access saved locally:',access_file,'(mode 0600). Token was not printed.')
    print('Next: use the agreed Queue API contract to verify a known-good and known-bad snapshot, then acknowledge their verdicts.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    create=sub.add_parser('submit');create.add_argument('--repo',help='Optional OWNER/dean-onboarding-PROJECT; otherwise derive from GitHub login and project slug')
    sub.add_parser('status');sub.add_parser('receive');args=parser.parse_args()
    try:
        if args.command=='submit':submit(args.repo)
        elif args.command=='status':status()
        else:receive()
    except lib.GitHubError as error:raise SystemExit(str(error))
