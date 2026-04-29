# PySceneDetect Release Checklist

Use one copy per release (e.g. tick the boxes in a tracking issue or draft PR).
Version referenced below as `X.Y[.Z]` - replace with the real version throughout.

## 0. Branch setup

- [X] Create / fast-forward release branch: `releases/X.Y` off `main`.
- [X] All release-prep commits land on `releases/X.Y` (never directly on `main` during the freeze - commits are usually halted to `main` until the release branch is cut, after which the release branch is merged back into `main` and development resumes).

## 1. Code & version

- [ ] Bump `__version__` in `scenedetect/__init__.py`.
- [ ] Bump the installer project: `python scripts/update_installer.py` (rewrites `ProductVersion`, regenerates `ProductCode`, updates the MSI filename via the AdvancedInstaller CLI). Add `--sync-files` after `pyinstaller` if any bundled dependency versions changed since the last release - this re-syncs APPDIR from `dist/scenedetect/` and replaces the manual "delete install dir + re-add files" GUI step. `scripts/pre_release.py --release` asserts the resulting `ProductVersion` matches `__version__`.
- [ ] No `-dev` / pre-release suffix on the version string for a final release.

> **Note:** `pyproject.toml` does not declare a `version` field - the single source of truth is `scenedetect/__init__.py`; the Windows installer `.aip` is the only other place to keep in sync.

## 2. Docs

- [ ] Docstrings / API docs reflect any signature changes (`cd docs/ && make html` builds clean).
- [ ] `docs/api/migration_guide.rst` updated if any public API changed.
- [ ] Docstring examples still run (nothing references removed symbols).

## 3. Website & changelog

- [ ] `website/pages/changelog.md`: rename the bottom **Development** section to `X.Y (YYYY-MM-DD)` and add a fresh empty **Development** section below it for post-release work.
- [ ] Changelog entry covers: new features, breaking changes, bug fixes, known issues.
- [ ] `website/pages/download.md` updated with the new version / installer link.
- [ ] Any other version-stamped pages updated (`supporting.md`, `cli.md` if commands changed).

## 4. Tests

- [ ] Unit tests green locally and in CI: `pytest -vv` (should collect `-m 'not release'` by default).
- [ ] `ruff check scenedetect/ tests/` and `ruff format --check scenedetect/ tests/` pass.
- [ ] Release test suite green: tag a disposable `vX.Y.Z-release-rc` or use `workflow_dispatch` on `.github/workflows/release-test.yml` - all 4 jobs (`static`, `release-tests`, `install-matrix`, `long-stress`) green across the 3-OS x 2-Python matrix. See `RELEASE-TEST-PLAN.md` for what the suite covers.
- [ ] `resources` branch has the artifacts the release tests need (goldens under `tests/resources/goldens/`, `tests/resources/stress_15min.mp4`). Re-push if any golden was regenerated.
- [ ] Manual smoke: fresh venv, `pip install .` (pulls opencv-python automatically) then `pip install .[pyav]`; run `scenedetect -i <video> detect-content list-scenes save-images` and eyeball the output. Repeat after `python packaging/build_headless.py && pip install .` to verify the headless variant.
- [ ] `pip-audit` clean (or exceptions documented in the changelog).

## 5. Windows installer

- [ ] `python scripts/pre_release.py --release` passes (enforces `.aip` <-> `__version__` parity, writes `packaging/windows/.version_info`).
- [ ] `pyinstaller packaging/windows/scenedetect.spec` produces a working `scenedetect.exe` - run it against a sample video.
- [ ] `python scripts/stage_windows_dist.py --ffmpeg-dir <dir>` populates `dist/scenedetect/` with ffmpeg, third-party licenses, sphinx docs, and emits the portable `.zip`. Pass `--ffmpeg-dir` pointing at a recent extracted [GyanD codexffmpeg](https://github.com/GyanD/codexffmpeg/releases) build; omit it only for offline builds (uses the bundled `packaging/windows/thirdparty.7z` with a stub `LICENSE-FFMPEG`).
- [ ] `python scripts/update_installer.py --sync-files` and commit the .aip diff (refreshes the APPDIR baseline so CI's per-build `--sync-only` diff stays small).
- [ ] Build the MSI via Advanced Installer (`packaging/windows/installer/PySceneDetect.aip`); install into a clean Windows VM and run the CLI.
- [ ] After both `pyinstaller` and the MSI build are done (and the portable `.zip` is staged at `dist/PySceneDetect-X.Y.Z-portable.zip`), run `python scripts/generate_manifest.py` to produce `dist/PySceneDetect-X.Y.Z.manifest.json` (per-file SHA256 audit of every artifact) and `dist/SHA256SUMS` (flat `sha256sum -c` compatible). Both are attached to the GitHub release in step 7.

> **GUI required for structural changes.** `scripts/update_installer.py` covers routine version bumps and `--sync-files` covers dependency-driven file-list changes, but anything that touches the *project structure* of the .aip still needs the AdvancedInstaller GUI. Examples:
>
> - Moving the .aip or its source tree (the build's `SourcePath` references are stored relative to the .aip and aren't rewritten by `/NewSync` - cf. the `dist/installer/` -> `packaging/windows/installer/` move that broke the relative paths until they were edited in the GUI).
> - Adding/removing build configurations, features, or prerequisites.
> - Editing dialog layouts, branding bitmaps, install sequences, custom actions, file associations, or shortcuts.
> - Changing `UpgradeCode`, install directory layout (`APPDIR` location), or per-component attributes.
>
> When in doubt, open the .aip in AdvancedInstaller, make the change, save, and commit the resulting diff. Re-run `update_installer.py` afterwards if the version-identity fields need refreshing.

## 6. Cut the release

- [ ] Final commit on `releases/X.Y`: "Release vX.Y[.Z]".
- [ ] Tag `vX.Y[.Z]-release` on that commit and push - this fires `release-test.yml`. Wait for all jobs green.
- [ ] Merge `releases/X.Y` into `main` (fast-forward or merge commit - keep history clean).
- [ ] Tag the final release `vX.Y[.Z]` on the merged commit and push.

## 7. Publish

- [ ] `publish-pypi.yml` ran on the tag and uploaded successfully. Verify both projects: https://pypi.org/project/scenedetect/ and https://pypi.org/project/scenedetect-headless/.
- [ ] Smoke-test PyPI: in a fresh venv, `pip install scenedetect==X.Y.Z`; CLI launches and `pip show scenedetect` lists `opencv-python`. Repeat in a second venv with `pip install scenedetect-headless==X.Y.Z`; verify it lists `opencv-python-headless`.
- [ ] Create GitHub Release from the `vX.Y[.Z]` tag, body = changelog section, attach Windows installer MSI + portable `.zip` + `PySceneDetect-X.Y.Z.manifest.json` + `SHA256SUMS` (both produced by `scripts/generate_manifest.py`).
- [ ] Deploy website: `generate-website.yml` picks up the changelog / download page updates.
- [ ] Deploy docs: `generate-docs.yml` publishes the new version.

## 8. Post-release

- [ ] On `main`: bump `__version__` to the next dev version (e.g. `X.(Y+1)-dev0` or `X.Y.(Z+1)-dev0`), matching `pyproject.toml` and `PySceneDetect.aip`.
- [ ] Clear / archive release-scoped tracking files (`tracking.md`, any release-specific TODOs).
- [ ] Announce: project site, relevant issues / discussions closed and linked to the release.
- [ ] Delete `releases/X.Y` branch once nothing else targets it.

---

## Notes

- **Branching model**: work spans multiple commits on `releases/X.Y`; the final one gets the `vX.Y[.Z]-release` tag which gates the release-test workflow. A passing release-test is a hard prerequisite for publishing.
- **Version consistency** is enforced in two places (`__init__.py`, `PySceneDetect.aip`). The `static` job of `release-test.yml` checks `__init__.py` against the tag and verifies the changelog has a matching `## PySceneDetect X.Y` heading; the installer parity is checked by `scripts/pre_release.py --release`.
- **Changelog convention**: the in-development section lives at the *bottom* of `website/pages/changelog.md` under the "Development" heading - don't move it to the top.
