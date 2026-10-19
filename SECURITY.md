# Repository secrets

Keep credentials in environment variables or a local `.env` file. Never add `.env`, downloaded credentials, service-account files, or private keys to Git. Use `.env.example` only for placeholder names and non-secret sample values.

Install the repository's local commit and push checks after cloning:

```sh
./scripts/install_git_hooks.sh
```

The commit check scans staged content for common Google API and AWS key formats. The push check scans the Git objects being sent, including their history, so a credential already committed cannot be pushed again just because it was later deleted. Do not bypass these checks to publish a branch containing a credential. Revoke or rotate an exposed credential and remove it from every published branch's history.
