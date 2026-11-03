# Queue API verification

After onboarding, the access bundle privately supplies the API URL, scoped token, verification configuration/version, limits and agreed request/response contract.

An agent or application uploads an exact source archive, submits a verification job, saves its ID and polls for the outcome or consumes the verdict stream. Process results durably, deduplicate repeat deliveries and acknowledge consumed verdicts. Stable submission references support retries. Results identify admitted source content and the chosen configuration version.

The API's `challenge` and `challenge_version` fields select a registered verification configuration and immutable revision. They are compatibility field names; an ordinary project-verification workflow needs no competition or ranking. The enabled configuration determines which targets, definitions, dependencies and assumptions are checked. Existing projects and new environments require compatibility review before enabling submissions.

All onboarding discussion and encrypted credential handoff use the same private onboarding issue. The public documentation repository receives no customer submissions, tokens or source bundles. The Queue API is the proof-snapshot submission route after onboarding, not an unrestricted self-registration endpoint.
