# Universal Mac candidate: 12 October 2026

This is local build evidence, not a published compatibility promise.

- Isolated python.org Python 3.12.10 universal2, with the pinned build requirements.
- Official installer signature and Apple notarisation verified before extraction. The framework was relocated into a temporary folder for this local test, without a system-wide installation.
- PyInstaller candidate built successfully for `universal2`.
- All 58 distinct bundled Mach-O files contain both `x86_64` and `arm64`.
- Highest audited deployment target: **11.0**. Bundle `LSMinimumSystemVersion`: **11.0**.
- Native arm64 packaged `--smoke-test`: passed, using a temporary library.
- Full regression suite: **28 passed**, including four deployment-parser tests.
- Source ZIP builds with the packaging helper and release documentation included.

## Still required before release

- Intel execution: this build Mac currently returns `Bad CPU type in executable` for `arch -x86_64 /bin/zsh`. Rosetta installation is awaiting permission. This is not a failed app test; Intel execution cannot start on this host.
- Developer ID signing, Apple submission/stapling and final archive verification for this new candidate. The existing public archive's notarisation does not apply to this candidate.
- Manual launch on the oldest macOS version to be advertised. Do not infer it from the binary deployment target.
- Windows workflow execution for the selected release tag, if making a new cross-platform release.

The existing published v1.10.3-beta.1 download URLs and compatibility statements are deliberately unchanged. No new release or asset has been published.
