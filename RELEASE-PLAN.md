# PySceneDetect Release Checklist

Use one copy per release, copy into a pull request and check each box as steps are completed.
Optional: version referenced below as `X.Y[.Z]` - replace with the real version throughout.

## 1. Version Identifiers, Branch Prep

- [ ] Create / fast-forward release branch: `releases/X.Y` off `main` if major/minor release. If patch release, fast-forward current `releases/X.Y` branch.
- [ ] Bump `__version__` in `scenedetect/__init__.py`
- [ ] Bump `docs/LATEST_VERSION` if needed (stable major/minor releases only)
- [ ] Regular release: No `-dev` suffix or other, pre-release: has suffix `-dev0`, `-dev1`, ...

## 2. Documentation, Website, Changelog

- [ ] Docstrings / API docs reflect any signature changes (`cd docs/ && make html` builds clean).
- [ ] `docs/api/migration_guide.rst` updated if any public API changed.
- [ ] Docstring examples all run correctly, nothing references removed or deprecated symbols.
- [ ] Changelog has release notes for major/minor release, all features, breaking changes, bug fixes, and known issues are documented.
- [ ] `website/pages/download.md` updated with the new version / installer link / release date.
- [ ] `website/pages/changelog.md`: move the release changes from the **Development** section at the bottom to the top.
- [ ] `website/pages/index.md`: Latest release version and date updated.

## 3. Tests

- [ ] Static analysis passing (ruff + pyright).
- [ ] Unit tests green locally and in CI: `pytest -vv` (should collect `-m 'not release'` by default).
- [ ] Release test suite green: manually trigger or make a release candidate tag, all 4 jobs (`static`, `release-tests`, `install-matrix`, `long-stress`) green across the OS and Python version matrix.
- [ ] `pip-audit` clean (or exceptions documented in the changelog).

## 4. Prepare Windows Distribution

- [ ] Update `packaging/windows/requirements.txt` and bump bundled ffmpeg version in `appveyor.yml`
- [ ] Run Appyeyor build on release branch, ensure resulting portable distribution and MSI installer are correct

> **GUI required for structural changes.** `scripts/update_installer.py` covers routine version bumps and `--sync-files` covers dependency-driven file-list changes, but anything that touches the *project structure* of the .aip still needs the AdvancedInstaller GUI. Examples:
>
> - Moving the .aip or its source tree (the build's `SourcePath` references are stored relative to the .aip and aren't rewritten by `/NewSync`.
> - Adding/removing build configurations, features, or prerequisites.
> - Install directory layout (`APPDIR` location), or per-component attributes.
> - Editing dialog layouts, branding bitmaps, install sequences, custom actions, file associations, or shortcuts.

## 5. Tag & Draft Release

- [ ] Final commit on `releases/X.Y`: "Release vX.Y[.Z]".
- [ ] Tag `vX.Y[.Z]-release` on that commit and push. Wait for all tests/builds to pass.
- [ ] Approve code signing request on SignPath, download `scenedetect-signed.zip`
- [ ] Finalize Windows artifacts locally (CI can't do this - signing happens after the AppVeyor build, so the signed-exe swap and hashing must run locally):
  - Create `dist/signed/` and copy in both `scenedetect-signed.zip` (from SignPath) and `PySceneDetect-X.Y.Z-portable.zip` (from the AppVeyor `PySceneDetect-win64_portable` artifact).
  - Run `python scripts/finalize_windows_dist.py`. This swaps the signed `scenedetect.exe` into the portable `.zip`, repacks it with 7-Zip, copies out the signed `.msi`, and writes `PySceneDetect-X.Y.Z.manifest.json` + `SHA256SUMS`.
- [ ] Draft release on Github using the tagged commit: include full changelog & release notes, signed portable .ZIP, signed .MSI installer, Python .whl/.tar.gz packages, and checksum manifests (`PySceneDetect-X.Y.Z.manifest.json` + `SHA256SUMS`)
- [ ] Verify all artifacts uploaded to Github release are valid and named correctly
- [ ] Smoke-test all release artifacts

## 6. Publish & Release Checks

- [ ] Publish Github release
- [ ] Upload to PyPI: `publish-pypi.yml` must be manually triggered on a release tag. Specify `testpypi` first, and make sure everything goes okay on the test instance. When verified and smoke tested, specify `pypi` as the environment, and publish the production package.
- [ ] Verify both projects: https://pypi.org/project/scenedetect/ and https://pypi.org/project/scenedetect-headless/.
- [ ] Merge `releases/X.Y` back into `main`.
- [ ] Deploy website: `generate-website.yml` picks up the changelog / download page updates.
- [ ] Deploy docs: `generate-docs.yml` publishes the new version.
- [ ] Smoke-test PyPI release: in a fresh venv, `pip install scenedetect==X.Y.Z`; CLI launches and `scenedetect --version` looks correct.
- [ ] Verify download links on website are correct, PyPI project page is up to date and correct.
- [ ] Clear / archive release-scoped tracking files (`tracking.md`, any release-specific TODOs).
- [ ] Announce: project site, relevant issues / discussions closed and linked to the release.

---

## Notes

- **Branching model**: work spans multiple commits on `releases/X.Y`; the final one gets the `vX.Y[.Z]-release` tag which gates the release-test workflow. A passing release-test is a hard prerequisite for publishing.
- **Version consistency** is enforced in two places (`__init__.py`, `PySceneDetect.aip`). The `static` job of `release-test.yml` checks `__init__.py` against the tag and verifies the changelog has a matching `## PySceneDetect X.Y` heading; the installer parity is checked by `scripts/pre_release.py --release`.
- **Changelog convention**: the in-development section lives at the *bottom* of `website/pages/changelog.md` under the "Development" heading - don't move it to the top.
