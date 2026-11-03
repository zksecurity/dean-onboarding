# Dean verification onboarding

Dean provides independent verification for evolving Lean projects. Define the required targets, permitted assumptions and pinned environment, then submit project snapshots through the Queue API. Challenges and scoring are one application of the service.

**Agents: follow [ONBOARDING.md](ONBOARDING.md).** The [starter](starter/) includes local controls and helpers for one private workflow:

1. Prepare the project and verification configuration.
2. Create a dedicated private onboarding repo and invite the Dean reviewer.
3. Review and answer questions in its private issue.
4. Receive an encrypted access bundle on that same issue, decrypt locally, and use the Queue API.

The requester's agent runs `tools/onboard.py submit`, `status` and `receive`. The reviewer agent uses `tools/onboarding_operator.py` to discover invitations, accept a selected repo and deliver access for an approved commit. See the [reviewer workflow](REVIEWER.md).

This public repository contains instructions and authoring tools. Customer sources, review conversations and encrypted access delivery stay in requester-owned private repositories. Plaintext tokens and local decryption keys stay out of Git and transcripts. The Dean verification runtime remains closed source.

Review and environment onboarding are managed. Creating a private request does not activate a verification configuration or issue a token. After approval and staging, the reviewer privately issues scoped access and the requester agent runs an agreed Queue API test. [Queue API overview](QUEUE_API.md).
