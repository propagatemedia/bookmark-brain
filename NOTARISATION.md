# Developer ID signing and notarisation

The current public download is still ad-hoc signed. This workflow does not change that until a new signed archive has been accepted by Apple, checked and published.

## One-time setup on the build Mac

1. In Xcode → Settings → Accounts, sign in to the Apple Developer account and select the correct team.
2. Under Manage Certificates, create or install a **Developer ID Application** certificate with its private key. An Apple Development or Mac App Distribution certificate is not a substitute. Your account holder may need to do this.
3. In your own Terminal, run `xcrun notarytool store-credentials bookmark-brain-notary`. Follow the secure prompts to store and validate credentials in Keychain. For Apple ID authentication, use an app-specific password and the correct Team ID. Do not paste credentials into chat or commit them to Git.

## Workflow

```sh
.venv-mac/bin/python scripts/notarise-mac.py prepare --identity 'Developer ID Application: YOUR NAME (TEAMID)'
.venv-mac/bin/python scripts/notarise-mac.py submit --workspace /path/printed/by/prepare
.venv-mac/bin/python scripts/notarise-mac.py finalise --workspace /path/printed/by/prepare
```

Prepare builds outside Google Drive, signs bundled code using PyInstaller's Developer ID support and hardened runtime, verifies the signature and runs an isolated smoke test. No permissive entitlements are added speculatively.

Submit uploads the signed archive to Apple using the Keychain profile and records its submission ID. Finalise checks Apple's result; it refuses to continue unless Accepted. It saves the review log, staples and validates the ticket, checks Gatekeeper, creates a fresh ZIP and tests the extracted app. Review any warnings and test a downloaded copy before releasing it. None of these commands replaces GitHub assets or deploys the website.

If Apple rejects the build, retrieve the submission log with notarytool and fix the reported issue before resubmitting. Do not claim notarisation, weaken Gatekeeper or replace the existing working download to work around rejection.
