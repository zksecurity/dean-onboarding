# Queue API integration

After a proposal is reviewed and the workload is enabled, the Dean team privately supplies the API base URL, scoped access token, supported challenge/version identifiers, limits and complete request/response contract.

The agent then automates this sequence:

1. Request an upload location and upload the exact source archive.
2. Submit a verification job for an enabled challenge version.
3. Save the returned submission identifier and poll for the result, or consume the verdict stream.
4. Process the terminal verdict durably, deduplicate repeat deliveries and acknowledge consumed messages.

A stable submission reference makes retries reproducible. The result identifies the admitted source artifact and selected verification version. Keep the uploaded bytes and their digest when recording a result.

This is the proof integration route for Dean. Public challenge review happens in this repository's issues; API access credentials and private material stay in the private onboarding channel. A proposal issue is not an API registration call, and an accepted proposal does not itself enable production submissions.
