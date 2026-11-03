# Dean verification-project starter

Follow the [agent onboarding workflow](https://github.com/zksecurity/dean-onboarding/blob/main/ONBOARDING.md). This example helps an agent prepare an existing or new Lean project for independent verification. It contains no Dean runtime code.

Requirements: Python 3.10+, Git, GitHub CLI, lake/elan, age and age-keygen. Use the normal package manager for the agent's environment. The example pins Lean 4.34.0; preserve the actual version when adapting an existing project.

```sh
python3 tools/check.py
python3 tools/onboard.py submit
python3 tools/onboard.py status
python3 tools/onboard.py receive
```

The agent replaces the example's trusted target, proof, checks, fixtures and `verification.json` consistently. The default snapshot policy admits only `Proof.lean` and protects trusted files. Local controls require a valid proof to pass, `sorryAx` to be refused and the wrong statement to fail its target check. These are local authoring checks, not a Dean service verdict.

`submit` derives a dedicated private repository name, prepares the selected source bundle, stores an age identity locally, opens the private issue and invites the Dean reviewer. The selected package and public recipient are shared; `.dean/` is excluded and remains local. `status` retrieves the team's replies. `receive` decrypts only matching access replies from the pinned reviewer and saves the API configuration to `.dean/access.json` with private permissions. It never prints the token. Keep the local `.dean/` state for later handoff and retries.

The private issue is the only onboarding channel. The team reviews and stages the environment before issuing scoped access; follow the agreed Queue API contract and verify good/bad snapshots to complete integration. Scoring may be added for challenge applications but is not required for project verification.

Reviewer agents use a trusted copy of `tools/onboarding_operator.py` following [REVIEWER.md](https://github.com/zksecurity/dean-onboarding/blob/main/REVIEWER.md). It accepts selected invitations and encrypts already-issued access for an explicitly approved commit; it does not replace private deployment or enrollment tooling.
