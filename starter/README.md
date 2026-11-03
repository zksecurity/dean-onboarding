# Dean challenge starter for agents

Copy this starter into the author's project and follow [the agent workflow](https://github.com/zksecurity/dean-challenges/blob/main/CHALLENGE_AUTHORING.md). These authoring files are intended to be copied and adapted for a challenge; they contain no Dean runtime source.

Requirements: Python 3.10+, lake/elan, and GitHub CLI for a public proposal. The toy example uses Lean 4.34.0. Preserve an existing project's actual pinned toolchain and request compatibility review.

```sh
python3 tools/check.py
python3 tools/package.py
python3 tools/propose.py submit --source-repo OWNER/REPO --commit FULL_COMMIT_SHA
python3 tools/propose.py status
```

Replace the example's statement, candidate, checks, fixtures and handoff specification together. The candidate source policy admits only `Submission.lean`; it must never replace trusted files. Add required source/data and dependency locks explicitly to `package_include`.

The public helper checks that the linked source repository is public, the full commit matches clean local HEAD and packaged source files are tracked. It creates a proposal issue in `zksecurity/dean-challenges`, keeps a receipt and retrieves the team's comments/status from the same thread. Public proposals need no email contact. Do not publish private source without authorization or put tokens in an issue.

For a private proposal, set `visibility` to `private`, provide `contact.email`, and run `python3 tools/package.py --private-email`. An authorized mail tool can send the generated `.eml` to kobi@zksecurity.xyz; the team replies on that email thread. The script does not send email.

Packaging produces a ZIP, checksum, proposal text, local report and logs. Generated outputs are ignored by Git. Compilation alone does not prove a submission acceptable: the controls also reject `sorryAx` and the wrong target type. These are local authoring checks, not a Dean service verdict.

All enabled proof workloads use the Queue API. The Dean team reviews runtime integration, stages the actual sandbox and issues scoped access privately. The handoff JSON is a proposal, not a production registration request.
