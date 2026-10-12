# Release checklist

No build script publishes automatically. Obtain approval before uploading assets or deploying the site.

1. Bump the version and review the diff.
2. Run `python3 -m unittest discover -s tests -v`.
3. Run `scripts/notarise-mac.py release` with the correct Python, architecture and Developer ID identity.
4. Review `mac-binary-audit.json`, `notary-log.json` and `verification.txt`. Require no unresolved Apple issues.
5. Test a browser-downloaded candidate on a second Mac/user account and the oldest claimed OS. Universal candidates also need both architecture smoke tests. Do not infer runtime support from the plist.
6. Build Windows for the intended tag and build the source ZIP. Assemble **one** `SHA256SUMS.txt` covering every ZIP. Do not overwrite it with a partial manifest.
7. After approval, upload only verified final assets and the consolidated checksum file. Never upload an intermediate Mac submission ZIP.
8. Update the website's download metadata with verified URLs, byte sizes, SHA-256 and tested requirements.
9. Run the website link check and review legal claims before publication.

Release notes must list the exact tested OS/architectures, signing status, known limitations and a link to the single `SHA256SUMS.txt`.
