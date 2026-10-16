#!/usr/bin/env bash
# Set up a dedicated project and verify patent access with a dry run.
set -euo pipefail

project_id="${1:-che126-separators-archi}"
if [[ ! "$project_id" =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]]; then
    printf 'Use a Google Cloud project ID of 6–30 lowercase letters, digits, or hyphens.\n' >&2
    exit 2
fi
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v brew >/dev/null && [[ -x /opt/homebrew/bin/brew ]]; then
    export PATH="/opt/homebrew/bin:$PATH"
fi
if ! command -v gcloud >/dev/null; then
    if ! command -v brew >/dev/null; then
        printf 'Install the Google Cloud CLI: https://docs.cloud.google.com/sdk/docs/install-sdk\n' >&2
        exit 1
    fi
    brew install --cask gcloud-cli
    export PATH="$(brew --prefix)/bin:$(brew --prefix)/share/google-cloud-sdk/bin:$PATH"
fi
command -v uv >/dev/null || {
    printf 'Install uv: https://docs.astral.sh/uv/getting-started/installation/\n' >&2
    exit 1
}

configuration="che126"
existing_config="$(gcloud config configurations list --filter="name=$configuration" --format='value(name)')"
if [[ -z "$existing_config" ]]; then
    gcloud config configurations create "$configuration" --no-activate
fi
gcloud auth login --configuration="$configuration"
existing_project="$(gcloud projects list --filter="projectId=$project_id" --format='value(projectId)' --configuration="$configuration")"
if [[ -z "$existing_project" ]]; then
    gcloud projects create "$project_id" --name='ChE126 Battery Separators' --configuration="$configuration"
fi
gcloud config set project "$project_id" --configuration="$configuration"
gcloud services enable bigquery.googleapis.com --project="$project_id" --configuration="$configuration"
account="$(gcloud config get-value account --configuration="$configuration")"
gcloud auth application-default login "$account" --configuration="$configuration"
gcloud auth application-default set-quota-project "$project_id" --configuration="$configuration"

cd "$repo_dir"
uv sync --locked --extra patents --group dev
export GOOGLE_CLOUD_PROJECT="$project_id"
uv run --locked --extra patents python - <<'PY'
import os
from che126_data_science.data_mining import GooglePatentsClient

project = os.environ['GOOGLE_CLOUD_PROJECT']
client = GooglePatentsClient(project=project)
estimate = client.search(
    ['battery', 'separator', 'porosity'],
    fields=['title', 'abstract'],
    countries=['US'],
    maximum_bytes_billed=1_000_000_000,
    dry_run=True,
)
print(f'Project: {project}')
print(f'Patent access verified with a dry run; estimated scan: {estimate.bytes_processed:,} bytes.')
print('No patent search was executed.')
PY
printf '\nSetup complete. Use GooglePatentsClient(project="%s") in Python.\n' "$project_id"
printf 'Google Cloud configuration: gcloud --configuration=che126 ...\n'
