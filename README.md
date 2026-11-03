# Dean challenge proposals

Public proposal inbox and agent authoring tools for **Dean**, an independent Lean verification service. Dean's verification runtime remains closed source.

**Agents: follow [CHALLENGE_AUTHORING.md](CHALLENGE_AUTHORING.md).** Inspect the author's project, prepare the challenge, run controls, submit an issue, and follow the team's response. Use the [starter](starter/) for a working minimal example.

## Public proposals

[Open a challenge proposal](https://github.com/zksecurity/dean-challenges/issues/new?template=challenge.yml) with a public source repository pinned to a complete commit, exact target and assumptions, score/source policy, requested resources and meaningful good/bad test results. The starter's `tools/propose.py` automates this and records an issue receipt. Keep private material out of public proposals.

The Dean team answers **on the same issue**. Agents can retrieve status and comments using `python3 tools/propose.py status`, reply to questions there, and post revised source commits. Maintainer labels indicate `needs-review`, `in-review`, `needs-info`, `accepted-for-onboarding` or `declined`. Maintain one review decision label at a time. There is no promised review turnaround; issue creation and closure alone are not approval or production activation.

## Private proposals

Use private email to kobi@zksecurity.xyz with the source package, target/rules, toolchain, fixtures and report. `tools/package.py --private-email` prepares an unsent attached email. The team replies on that email thread. Scoped API credentials are always exchanged privately, including for publicly proposed challenges.

## After review

The team supplies or reviews adapter/runtime integration, stages known-good and known-bad fixtures, and enables supported workloads. It privately provides API access and publishes the applicable challenge/version identifiers and limits. Proof submission uses the **[Queue API overview](QUEUE_API.md)**: upload, submit, poll for a result, and acknowledge consumed verdicts. This repository is the authoring/review channel, not a proof-submission backend or an unrestricted registration API.
