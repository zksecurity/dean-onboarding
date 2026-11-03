#!/usr/bin/env python3
"""Dean reviewer agent: discover invitations, accept a selected private repo, deliver encrypted access."""
import argparse,json,stat
from pathlib import Path
import onboarding_lib as lib


def reviewer():
    actor=lib.github('user')
    if actor['id']!=lib.REVIEWER_ID:raise SystemExit('Use the pinned Dean reviewer GitHub identity')
    return actor


def inbox():
    reviewer()
    invites=lib.pages('user/repository_invitations?per_page=100')
    print(json.dumps([{'repository':x['repository']['full_name'],'inviter':x['inviter']['login']} for x in invites if lib.REPO_RE.fullmatch(x['repository']['full_name'])],indent=2))


def accept(repo):
    reviewer()
    if not lib.REPO_RE.fullmatch(repo):raise SystemExit('Use the exact dedicated private onboarding repository')
    invitations=lib.pages('user/repository_invitations?per_page=100')
    selected=next((x for x in invitations if x['repository']['full_name'].lower()==repo.lower()),None)
    if selected:
        if not selected['repository'].get('private'):raise SystemExit('Refusing a public repository invitation')
        lib.github('user/repository_invitations/'+str(selected['id']),'PATCH')
    lib.private_repo(repo)
    issues=lib.pages(f'repos/{repo}/issues?state=open&per_page=100')
    print(json.dumps([{'url':x['html_url'],'title':x['title']} for x in issues if lib.REQUEST_MARKER in (x.get('body') or '')],indent=2))


def inspect(url):
    reviewer();_,_,_,request=lib.read_request(url)
    print(json.dumps(request,indent=2))
    print('Pinned review bundle checksum verified. Inspect the proposed targets and use trusted build/staging tooling; do not run customer scripts with operator credentials.')


def deliver(url,approved_commit,access_file):
    reviewer();repo,number,_,request=lib.read_request(url,approved_commit)
    path=Path(access_file)
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode) or path.stat().st_mode&0o077:raise SystemExit('Access input must be a regular mode-0600 file')
    try:access=json.loads(path.read_bytes())
    except (ValueError,TypeError):raise SystemExit('Access input is not valid JSON')
    lib.validate_access(access)
    payload={'request_id':request['request_id'],'repository':repo,'commit':approved_commit,'access':access}
    plaintext=json.dumps(payload).encode()
    if len(plaintext)>24000:raise SystemExit('Access configuration is too large for an encrypted issue reply')
    ciphertext=lib.command(['age','--encrypt','--armor','--recipient',request['recipient']],data=plaintext)
    envelope={k:request[k] for k in ['request_id','commit','recipient']};envelope['ciphertext']=ciphertext
    _,_,_,current=lib.read_request(url,approved_commit)
    if current!=request:raise SystemExit('Request changed during delivery; review again')
    lib.private_repo(repo)
    lib.github(f'repos/{repo}/issues/{number}/comments','POST',{'body':lib.packet(lib.ACCESS_MARKER,envelope)+'\nScoped access issued for this approved configuration. Receive it locally and run the agreed Queue API smoke test.'})
    print('Encrypted access posted to the private onboarding issue. No plaintext credential was printed or committed.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('inbox')
    invitation=sub.add_parser('accept');invitation.add_argument('--repo',required=True)
    review=sub.add_parser('inspect');review.add_argument('--issue',required=True)
    send=sub.add_parser('deliver');send.add_argument('--issue',required=True);send.add_argument('--approved-commit',required=True);send.add_argument('--access-file',required=True)
    args=parser.parse_args()
    try:
        if args.command=='inbox':inbox()
        elif args.command=='accept':accept(args.repo)
        elif args.command=='inspect':inspect(args.issue)
        else:deliver(args.issue,args.approved_commit,args.access_file)
    except lib.GitHubError as error:raise SystemExit(str(error))
