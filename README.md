# iOS builds — The Ammonia Files (cloud Mac via GitHub Actions)

Apple Developer account: **Blake Goddard — bgcustom@outlook.com**,
Enrollment ID `M3583CT345`, membership active (paid $99 on 14 Nov 2026,
Order #W1489169329). There is no Mac in this Linux VM, so iPhone builds
run on GitHub's cloud Mac (`macos-26` runner, Xcode 26) and upload
straight to App Store Connect / TestFlight.

**Status — 15 Nov 2026, ~00:05 CST**

| Item | State |
|---|---|
| Capacitor iOS projects (both apps) | ✅ Built locally, bundle IDs + versions set, icons + splash replaced |
| GitHub Actions workflow (`.github/workflows/build-ios.yml`) | ✅ Written, YAML-validated |
| Distribution certificate private key + CSR | ✅ Generated — `signing/dist.csr` ready to upload |
| GitHub repo | ❌ **Not created** — needs a human/gh action (see §1) |
| Distribution certificate (.cer → .p12) | ❌ Blocked on CSR upload (see §3B) |
| Provisioning profiles (2) | ❌ Blocked — create in developer.apple.com (see §3C) |
| App Store Connect API key (.p8) | ❌ Blocked — create in App Store Connect (see §3D) |
| Team ID | ❌ Needed — read from developer.apple.com (see §3A) |
| GitHub secrets (8) | ❌ Blocked on the above |
| First workflow run / .ipa / TestFlight | ❌ Not run yet — first run is **untested** |
| App Store Connect app records | 🔄 Being created in a separate browser task (needed before first upload) |
| Privacy policy page (`theammoniafiles.com/privacy`) | ❌ Not built yet — **required before App Store submission** (also required for Google Play) |

## The two apps

| App | Bundle ID | Version | Contents (baked in) |
|---|---|---|---|
| Refrigeration Tools | `com.theammoniafiles.tools` | 1.0.0 (build = GitHub run #) | 29-tab tools app, 93 refrigerants, Ask Frosty (107 topics, does P-T math), GCAP removed from contacts |
| The Ammonia Files Store | `com.theammoniafiles.store` | 1.0.0 (build = GitHub run #) | All 45 merch products, Buy on Amaze buttons, Books section (PSM + CMRP → Amazon) |

Both are Capacitor 7.6.10 wrappers around the static web apps in `www/`
(same code as the Android builds). Icons and launch screens use the
frosted NH3 emblem (verified 3 H) — 1024×1024 app icon, dark splash screen.

## Repo layout (this folder IS the repo root)

```
.github/workflows/build-ios.yml   # the workflow (matrix: both apps)
tools-app/                         # Capacitor project (ios/ inside)
store-app/                         # Capacitor project (ios/ inside)
scripts/create-distribution-cert.sh
scripts/set-secrets.sh
icon-source.png                    # frosted NH3 emblem (source for icons)
.gitignore                         # keeps node_modules, build output, signing/ out of git
signing/                           # gitignored: private key, CSR, .p12, .p8, profiles
```

`node_modules/` is present locally (29 MB per app) but is **not** committed;
the workflow runs `npm ci` from the committed `package-lock.json` files.

## 1. Create the GitHub repo and push (Muse / anyone with gh)

```bash
cd ~/workspace/apps/ios
gh repo create theammoniafiles/ios-apps --public --source=. --push
```

**Make it PUBLIC.** macOS runners are free in public repos. In a private
repo they cost $0.062/min (GitHub Free includes ~$12/mo credit ≈ 190
macOS minutes; each run is ~5–10 min per app). The code is just the
public-facing web apps — nothing secret in it. Secrets live in GitHub
Secrets, never in the repo.

Without `gh`: create an empty repo named `ios-apps` under the
`theammoniafiles` GitHub org/account on github.com, then
`git init; git add -A; git commit -m "iOS apps"; git remote add origin …; git push -u origin main`.

## 2. What the workflow does

`runs-on: macos-26` (Xcode 26 — **required**: Apple rejects uploads built
with Xcode < 26 since 28 Apr 2026). One job per app (matrix):

1. Check out, select latest Xcode 26, Node 24, `npm ci`
2. `npx cap sync ios` (copies `www/` into the Xcode project)
3. `pod install` (Capacitor via CocoaPods)
4. Import the distribution `.p12` into a throwaway keychain
5. Install the app's provisioning profile (from a base64 secret)
6. `xcodebuild archive` — manual signing, `Apple Distribution` identity,
   build number = GitHub run number, version 1.0.0
7. `xcodebuild -exportArchive` with `destination: upload` — signs the
   `.ipa` **and uploads it to App Store Connect** in one step, using the
   App Store Connect API key. The build then appears in
   App Store Connect → TestFlight.
8. Keeps the `.ipa` as a workflow artifact when one is written
   (best effort — with `destination: upload` the upload is the point).

Triggers: push to `main` touching either app, or Actions → Run workflow.

## 3. Signing assets — what is needed and who does each step

### 3A. Team ID — read it (browser task, 1 minute)

developer.apple.com → Account → Membership → **Team ID**
(10 characters, e.g. `ABCDE12345`). Goes into secret `APPLE_TEAM_ID`.

### 3B. Distribution certificate — CSR ready, upload pending

**Already done here:** `signing/dist.csr` + private key
`signing/dist.key.pem` (RSA 2048, CN=Blake Goddard, O=The Ammonia Files).
The private key never leaves this folder and is gitignored — **back it up**:
if it is lost, the certificate is useless and a new one must be made.

**Next (browser task, uses Blake's signed-in session):**

1. developer.apple.com → Certificates, Identifiers & Profiles →
   Certificates → **+**
2. Choose **Apple Distribution** → Continue → upload `signing/dist.csr`
   → Continue → **Download** the `.cer` file.
3. Run locally: `./scripts/create-distribution-cert.sh finish <file.cer>`
   → creates `signing/dist.p12` (you choose the password;
   that password becomes secret `IOS_DIST_P12_PASSWORD`).

Note: an account can hold at most 3 distribution certificates. If 3
already exist, revoke an unused one first.

### 3C. Provisioning profiles — create two (browser task)

developer.apple.com → Certificates, Identifiers & Profiles → Profiles → **+**

| Profile | Type | App ID | Certificate | Name (exact) |
|---|---|---|---|---|
| Tools | App Store | `com.theammoniafiles.tools` | the Apple Distribution cert from §3B | `TAF Tools App Store` |
| Store | App Store | `com.theammoniafiles.store` | same cert | `TAF Store App Store` |

The App IDs must exist first — they are created automatically when the
App Store Connect app records are created (separate browser task in
progress). If the App ID dropdown is empty, the app records aren't done
yet. Download each `.mobileprovision` and save as
`signing/tools.mobileprovision` / `signing/store.mobileprovision`.
The profile **names must match exactly** — the workflow passes them to
`xcodebuild` as `PROVISIONING_PROFILE_SPECIFIER` and in
`ExportOptions.plist`. (Profile UUIDs are read from the files, so the
filenames don't matter.)

### 3D. App Store Connect API key — create once (Blake or browser task)

App Store Connect → Users and Access → Integrations →
App Store Connect API → **Generate API Key**, name it e.g. `ios-ci`,
role **App Manager**. Download the `.p8` file **once** (Apple shows it
only at creation) and save as `signing/AuthKey.p8`. Record the
**Key ID** and **Issuer ID** shown on the same page.

### 3E. Put the 8 secrets into GitHub (Muse, one command)

```bash
export APPLE_TEAM_ID=XXXXXXXXXX
export ASC_KEY_ID=XXXXXXXXXX
export ASC_ISSUER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
export IOS_DIST_P12_PASSWORD='the password you chose in §3B'
./scripts/set-secrets.sh theammoniafiles/ios-apps
```

| Secret | Value |
|---|---|
| `APPLE_TEAM_ID` | §3A |
| `IOS_DIST_P12` | base64 of `signing/dist.p12` |
| `IOS_DIST_P12_PASSWORD` | the .p12 password |
| `IOS_TOOLS_PROFILE_B64` | base64 of `signing/tools.mobileprovision` |
| `IOS_STORE_PROFILE_B64` | base64 of `signing/store.mobileprovision` |
| `APP_STORE_CONNECT_API_KEY_ID` | §3D Key ID |
| `APP_STORE_CONNECT_ISSUER_ID` | §3D Issuer ID |
| `APP_STORE_CONNECT_API_PRIVATE_KEY` | **raw contents** of `signing/AuthKey.p8` (not base64) |

`set-secrets.sh` does the base64 encoding itself. Never paste a secret
into chat.

## 4. First run

1. Push any commit to `main` (or Actions → Build iOS → Run workflow).
2. Watch the Actions tab. Expect ~5–10 min per app.
3. When green, the builds appear in App Store Connect → My Apps →
   each app → TestFlight (processing takes a few minutes).
4. Add Blake as an internal tester (TestFlight → Internal Testing) and
   install via the TestFlight app on his iPhone — this is the first
   real-device test of the iOS builds.
5. Submit for review (App Store Connect → app → App Information /
   Version): fill the listing from `~/workspace/apps/store-listings.md`,
   add screenshots (take from the phone once installed), answer the
   content-rating questionnaire and data-safety form (both apps collect
   no data), and provide the privacy policy URL — see §5.

## 5. Blockers outside this setup

- **Privacy policy page (required).** Apple and Google both require a
  public privacy policy URL before submission. It does not exist yet:
  needs a page live at `https://theammoniafiles.com/privacy`
  (both apps collect no data, no accounts, no tracking — a one-page
  statement is enough). The website update is a separate job
  (Cloudflare Worker `raspy-heart-47a8`).
- **EU trader status.** App Store Connect shows a notice: developers
  must declare trader status for EU distribution under the Digital
  Services Act. Leaving it blank only affects the EU storefront, not
  US submission — but Blake should complete it in
  App Store Connect → Business when the listing is filled in.
- **App Store Connect app records** must exist before the first upload
  (bundle IDs must match exactly). A browser task is creating them now.

## 6. Rebuilds and version bumps

- **Web app changed?** Re-export the artifact HTML into
  `tools-app/www/index.html` or `store-app/www/index.html`
  (or run `npx cap sync ios` after replacing it), commit, push —
  the workflow rebuilds and uploads automatically. Build number
  auto-increments (GitHub run number). **The store app does NOT
  auto-update** — after each Amaze merch wave, re-export and push a
  new build, same as Android.
- **New release version (1.1 etc.):** change `MARKETING_VERSION=1.0.0`
  in `.github/workflows/build-ios.yml` (archive step) and the
  `MARKETING_VERSION` in both Xcode projects, commit, push.
- **Profiles expire yearly; certificates expire yearly.** When a build
  fails with a signing error a year from now, re-download the profiles
  and re-set the two `*_PROFILE_B64` secrets (and make a new cert if
  the distribution certificate expired).

## 7. Costs

- GitHub Actions macOS minutes: **$0 in a public repo**; ~$0.062/min
  in a private repo (Free tier ≈ 190 macOS min/month).
- Apple Developer Program: $99/year (already paid, renews Nov 2027).
- Nothing else in this pipeline costs money. No paid CI service,
  no Mac rental, no fastlane subscription.

## 8. Risks and fallbacks

- **First run is untested.** No repo, no secrets and no Mac exist yet
  to run against — the workflow is written from verified patterns
  (Xcode 26 on `macos-26`, `destination: upload` export, manual
  signing), but the first green run is the real test. Likely first-run
  failure points, in order: wrong profile name, profile/certificate
  mismatch, missing app record in App Store Connect.
- **Capacitor 7 + Xcode 26.** The projects use Capacitor 7.6.10
  (same as Android). If the Xcode 26 build fails on Capacitor 7,
  upgrade the iOS projects to Capacitor 8 (current: 8.6.2):
  `npm install @capacitor/core@8 @capacitor/cli@8 @capacitor/ios@8`
  in each app dir, then `npx cap sync ios`. Capacitor 8 targets
  newer Xcode; the web code is unchanged.
- **April 2027 cutoff.** From April 2027 Apple requires Xcode 27 /
  iOS 27 SDK for uploads. When that lands, the workflow needs
  `runs-on: macos-26` → the macOS 27 runner and the latest Xcode —
  a one-line change, but check it before the first 2027 release.
- **If GitHub Actions is ever abandoned**, the same Xcode projects
  build on any Mac with `xcodebuild` (or Xcode Cloud — 25 compute
  hours/month included with the Developer Program).
