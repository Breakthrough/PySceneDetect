# PySceneDetect Release Checklist

Use one copy per release (e.g. tick the boxes in a tracking issue or draft PR).
Version referenced below as `X.Y[.Z]` - replace with the real version throughout.

## 0. Branch setup

- [ ] Create / fast-forward release branch: `releases/X.Y` off `main`.
- [ ] All release-prep commits land on `releases/X.Y` (never directly on `main` during the freeze - commits are usually halted to `main` until the release branch is cut, after which the release branch is merged back into `main` and development resumes).

## 1. Code & version

- [ ] Bump `__version__` in `scenedetect/__init__.py`.
- [ ] Bump `ProductVersion` in `packaging/windows/installer/PySceneDetect.aip` (must match `__version__` - `scripts/pre_release.py --release` asserts this).
- [ ] No `-dev` / pre-release suffix on the version string for a final release.

> **Note:** `setup.cfg` reads the package version dynamically via `version = attr: scenedetect.__version__`, and `pyproject.toml` does not declare a `version` field. The single source of truth is `scenedetect/__init__.py`; the `.aip` is the only other place to keep in sync.

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
- [ ] Release test suite green: tag a disposable `vX.Y.Z-release-rc` or use `workflow_dispatch` on `.github/workflows/release-test.yml` - all 4 jobs (`static`, `release-tests`, `install-matrix`, `long-stress`) green across the 3-OS × 2-Python matrix. See `RELEASE-TEST-PLAN.md` for what the suite covers.
- [ ] `resources` branch has the artifacts the release tests need (goldens under `tests/resources/goldens/`, `tests/resources/stress_15min.mp4`). Re-push if any golden was regenerated.
- [ ] Manual smoke: fresh venv, `pip install .` then `pip install .[opencv]` then `pip install .[pyav]`; run `scenedetect -i <video> detect-content list-scenes save-images` and eyeball the output.
- [ ] `pip-audit` clean (or exceptions documented in the changelog).

## 5. Windows installer

- [ ] `python scripts/pre_release.py --release` passes (enforces `.aip` ↔ `__version__` parity, writes `packaging/windows/.version_info`).
- [ ] `pyinstaller packaging/windows/scenedetect.spec` produces a working `scenedetect.exe` - run it against a sample video.
- [ ] Build the MSI via Advanced Installer (`packaging/windows/installer/PySceneDetect.aip`); install into a clean Windows VM and run the CLI.

## 6. Cut the release

- [ ] Final commit on `releases/X.Y`: "Release vX.Y[.Z]".
- [ ] Tag `vX.Y[.Z]-release` on that commit and push - this fires `release-test.yml`. Wait for all jobs green.
- [ ] Merge `releases/X.Y` into `main` (fast-forward or merge commit - keep history clean).
- [ ] Tag the final release `vX.Y[.Z]` on the merged commit and push.

## 7. Publish

- [ ] `publish-pypi.yml` ran on the tag and uploaded successfully. Verify at https://pypi.org/project/scenedetect/.
- [ ] Smoke-test PyPI: in a fresh venv, `pip install scenedetect==X.Y.Z` (bare), then with `[opencv]` and `[pyav]`. CLI launches.
- [ ] Create GitHub Release from the `vX.Y[.Z]` tag, body = changelog section, attach Windows installer MSI + portable `.zip`.
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
