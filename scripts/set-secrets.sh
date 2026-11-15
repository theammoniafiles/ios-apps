#!/bin/bash
# Set all GitHub secrets for the iOS workflow from local files.
# Run from the repo root after the signing assets exist (see README.md).
# Requires: gh CLI, authenticated (gh auth login) with admin access to the repo.
#
# Usage: ./scripts/set-secrets.sh [repo]
#   repo defaults to the 'origin' remote, e.g. theammoniafiles/ios-apps
set -euo pipefail
cd "$(dirname "$0")/.."

REPO="${1:-$(git config --get remote.origin.url | sed -E 's#.*github.com[:/]([^/]+/[^/.]+)(\.git)?#\1#')}"
[ -n "$REPO" ] || { echo "No repo given and no origin remote found. Usage: $0 owner/repo"; exit 1; }
echo "Setting secrets on $REPO"

# Team ID + ASC API key (paste values in the files, or set env vars first)
: "${APPLE_TEAM_ID:?Set APPLE_TEAM_ID env var (from developer.apple.com -> Account -> Membership)}"
: "${ASC_KEY_ID:?Set ASC_KEY_ID env var (App Store Connect API Key ID)}"
: "${ASC_ISSUER_ID:?Set ASC_ISSUER_ID env var (App Store Connect Issuer ID)}"
[ -f signing/AuthKey.p8 ] || { echo "Missing signing/AuthKey.p8 — download the .p8 from App Store Connect and save it as signing/AuthKey.p8"; exit 1; }
[ -f signing/dist.p12 ] || { echo "Missing signing/dist.p12 — run scripts/create-distribution-cert.sh first"; exit 1; }
: "${IOS_DIST_P12_PASSWORD:?Set IOS_DIST_P12_PASSWORD env var (the .p12 password you chose)}"
for f in signing/tools.mobileprovision signing/store.mobileprovision; do
  [ -f "$f" ] || { echo "Missing $f — download the provisioning profiles from developer.apple.com and save them with these exact names"; exit 1; }
done

gh secret set APPLE_TEAM_ID --repo "$REPO" --body "$APPLE_TEAM_ID"
gh secret set APP_STORE_CONNECT_API_KEY_ID --repo "$REPO" --body "$ASC_KEY_ID"
gh secret set APP_STORE_CONNECT_ISSUER_ID --repo "$REPO" --body "$ASC_ISSUER_ID"
gh secret set APP_STORE_CONNECT_API_PRIVATE_KEY --repo "$REPO" < signing/AuthKey.p8
gh secret set IOS_DIST_P12 --repo "$REPO" < <(base64 -w0 signing/dist.p12)
gh secret set IOS_DIST_P12_PASSWORD --repo "$REPO" --body "$IOS_DIST_P12_PASSWORD"
gh secret set IOS_TOOLS_PROFILE_B64 --repo "$REPO" < <(base64 -w0 signing/tools.mobileprovision)
gh secret set IOS_STORE_PROFILE_B64 --repo "$REPO" < <(base64 -w0 signing/store.mobileprovision)

echo "All 8 secrets set on $REPO."
