"""Shared private-onboarding transport. No Dean runtime or deployment credentials."""
import base64, hashlib, json, os, re, subprocess, tempfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REVIEWER = 'kobizk'
REVIEWER_ID = 291547105
REQUEST_MARKER = '<!-- dean-onboarding-request:v1 -->'
ACCESS_MARKER = '<!-- dean-onboarding-access:v1 -->'
REPO_RE = re.compile(r'[A-Za-z0-9_.-]+/dean-onboarding-[A-Za-z0-9_.-]+')

class GitHubError(RuntimeError):
    def __init__(self, message, missing=False):
        super().__init__(message); self.missing = missing

def command(args, cwd=None, data=None, binary=False):
    result = subprocess.run(args, cwd=cwd, input=data, capture_output=True)
    if result.returncode:
        # Do not echo inputs or raw outputs: commands may handle private material.
        error = result.stderr.decode(errors='replace')
        raise GitHubError(f'{args[0]} failed; check authentication, permissions or tool installation.', 'HTTP 404' in error)
    return result.stdout if binary else result.stdout.decode().strip()

def github(path, method='GET', body=None, raw=False):
    args = ['gh','api','--method',method,'--header','Accept: '+('application/vnd.github.raw+json' if raw else 'application/vnd.github+json'),path]
    if body is not None:args += ['--input','-']
    result = command(args, data=json.dumps(body).encode() if body is not None else None, binary=True)
    return result if raw else (json.loads(result) if result else {})

def pages(path):
    return [item for page in json.loads(command(['gh','api','--paginate','--slurp',path])) for item in page]

def private_repo(name):
    if not REPO_RE.fullmatch(name):raise SystemExit('Use OWNER/dean-onboarding-PROJECT for a dedicated private onboarding repository')
    repo = github('repos/'+name)
    if not repo.get('private'):raise SystemExit('Private onboarding refuses public repositories; visibility is never changed automatically')
    return repo

def issue_parts(url):
    match = re.fullmatch(r'https://github.com/([A-Za-z0-9_.-]+/dean-onboarding-[A-Za-z0-9_.-]+)/issues/(\d+)',url)
    if not match:raise SystemExit('Expected an issue in a dedicated private dean-onboarding-* repository')
    return match.group(1),match.group(2)

def unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate JSON field')
        result[key]=value
    return result

def packet(marker, value):return marker+'\n```json\n'+json.dumps(value,indent=2)+'\n```\n'

def parse_packet(body, marker):
    if body.count(marker)!=1:raise SystemExit('Expected exactly one onboarding metadata packet')
    found=re.search(re.escape(marker)+r'\s*```json\s*\n(.*?)\n```',body,re.S)
    if not found or len(found[1])>60000:raise SystemExit('Invalid onboarding metadata')
    try:return json.loads(found[1],object_pairs_hook=unique_object)
    except (ValueError,TypeError):raise SystemExit('Invalid onboarding JSON')

def secure_write(path, data):
    path=Path(path)
    if path.parent.is_symlink() or path.is_symlink():raise SystemExit('Refusing a symlink for local private state')
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    path.parent.chmod(0o700)
    fd,temporary=tempfile.mkstemp(dir=path.parent,prefix='.pending-')
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(data)
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)

def local_state(root=ROOT):
    directory=Path(root)/'.dean'
    if directory.is_symlink():raise SystemExit('Local private state cannot be a symlink')
    directory.mkdir(exist_ok=True,mode=0o700);directory.chmod(0o700)
    ignore=Path(root)/'.gitignore'
    text=ignore.read_text() if ignore.exists() else ''
    additions=[line for line in ['.dean/','intake-out/'] if line not in text.splitlines()]
    if additions:ignore.write_text(text.rstrip()+'\n'+'\n'.join(additions)+'\n')
    git=subprocess.run(['git','ls-files','--','.dean'],cwd=root,capture_output=True)
    if git.returncode==0 and git.stdout.strip():raise SystemExit('Untrack .dean before storing local keys or access files')
    return directory

def identity(directory):
    path=directory/'identity.txt'
    if path.is_symlink():raise SystemExit('The local identity must be a regular private file')
    if not path.exists():
        old=os.umask(0o077)
        try:command(['age-keygen','-o',str(path)])
        finally:os.umask(old)
    if path.stat().st_mode & 0o077:raise SystemExit('The local identity must have mode 0600')
    recipient=command(['age-keygen','-y',str(path)])
    if not re.fullmatch(r'age1[a-z0-9]{30,100}',recipient):raise SystemExit('Expected a native age public recipient')
    return path,recipient

def read_request(url, approved_commit=None, verify_archive=True):
    repo,number=issue_parts(url);private_repo(repo)
    issue=github(f'repos/{repo}/issues/{number}')
    request=parse_packet(issue.get('body') or '',REQUEST_MARKER)
    if request.get('repository')!=repo or request.get('requester')!=issue['user']['login']:
        raise SystemExit('Request identity does not match the private issue')
    commit=request.get('commit','')
    if not re.fullmatch(r'[0-9a-f]{40}',commit):raise SystemExit('A full pinned commit is required')
    if approved_commit is not None and approved_commit!=commit:raise SystemExit('The request changed since approval; review the new commit first')
    if request.get('reviewer')!=REVIEWER or request.get('reviewer_id')!=REVIEWER_ID:raise SystemExit('Unexpected reviewer identity')
    content=github(f'repos/{repo}/contents/dean-onboarding.json?ref={commit}')
    metadata=json.loads(base64.b64decode(content['content']))
    for field in ['request_id','recipient','package_sha256','requester','reviewer','reviewer_id']:
        if request.get(field)!=metadata.get(field):raise SystemExit('Issue metadata differs from the pinned repository commit')
    if verify_archive:
        archive_content=github(f'repos/{repo}/contents/review.zip?ref={commit}')
        archive=base64.b64decode(archive_content['content'])
        if hashlib.sha256(archive).hexdigest()!=request['package_sha256']:raise SystemExit('Review archive checksum mismatch')
    return repo,number,issue,request

def validate_access(access):
    if not isinstance(access,dict):raise SystemExit('Expected an access configuration object')
    required=['api_base_url','token','challenge','challenge_version','limits']
    if any(key not in access for key in required):raise SystemExit('Access configuration is missing required Queue API fields')
    url=urlparse(access['api_base_url'])
    if url.scheme!='https' or not url.hostname or url.username or url.password or url.fragment:raise SystemExit('Access API URL must be HTTPS without embedded credentials')
    if not isinstance(access['token'],str) or not access['token'].strip():raise SystemExit('Access token is empty')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',access['challenge']):raise SystemExit('Invalid verification configuration identifier')
    if not isinstance(access['challenge_version'],str) or not access['challenge_version'].strip():raise SystemExit('An explicit configuration version is required')
    if not isinstance(access['limits'],dict):raise SystemExit('Expected configured capacity limits')
