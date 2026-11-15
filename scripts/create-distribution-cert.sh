#!/bin/bash
# Create an Apple Distribution certificate the CI way:
#   1. This script generates a private key + Certificate Signing Request (CSR).
#   2. Upload the CSR at developer.apple.com -> Certificates -> + -> Apple Distribution.
#   3. Download the .cer, then run: ./scripts/create-distribution-cert.sh finish <file.cer>
#      to make the .p12 the GitHub workflow needs (secret IOS_DIST_P12).
#
# Run from the repo root:  ./scripts/create-distribution-cert.sh
# Everything is written under signing/ (gitignored — never commit keys).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p signing

if [ "${1:-}" = "finish" ]; then
  CER="${2:-}"
  [ -n "$CER" ] && [ -f "$CER" ] || { echo "Usage: $0 finish <downloaded.cer>"; exit 1; }
  [ -f signing/dist.key.pem ] || { echo "No signing/dist.key.pem — run '$0' first to create the CSR."; exit 1; }
  openssl x509 -in "$CER" -inform DER -out signing/dist.cert.pem
  echo "Enter a password for the .p12 (this becomes secret IOS_DIST_P12_PASSWORD):"
  openssl pkcs12 -export -inkey signing/dist.key.pem -in signing/dist.cert.pem -out signing/dist.p12
  echo
  echo "Done. Files:"
  echo "  signing/dist.p12        -> base64 it into secret IOS_DIST_P12"
  echo "  signing/dist.key.pem    -> KEEP PRIVATE. Back it up somewhere safe."
  echo "  signing/dist.cert.pem   -> the certificate (public part)."
  echo
  echo "To set the secrets (needs 'gh' logged in to the repo):"
  echo "  ./scripts/set-secrets.sh"
  exit 0
fi

if [ -f signing/dist.key.pem ]; then
  echo "signing/dist.key.pem already exists — refusing to overwrite."
  echo "If you lost the matching certificate, delete signing/ and re-run."
  exit 1
fi

openssl req -new -newkey rsa:2048 -nodes \
  -keyout signing/dist.key.pem \
  -out signing/dist.csr \
  -subj "/CN=Blake Goddard/O=The Ammonia Files/C=US"
chmod 600 signing/dist.key.pem

echo
echo "CSR created: signing/dist.csr"
echo
echo "NEXT STEP — upload the CSR (do this in the browser, or ask Muse to do it):"
echo "  1. Go to developer.apple.com -> Certificates, Identifiers & Profiles -> Certificates -> +"
echo "  2. Choose 'Apple Distribution' -> Continue"
echo "  3. Upload signing/dist.csr -> Continue -> Download the .cer file"
echo "  4. Then run: ./scripts/create-distribution-cert.sh finish <downloaded.cer>"
echo
echo "NOTE: an Apple Developer account can have at most 3 distribution"
echo "certificates. If 3 already exist, revoke an unused one first."
