# Versioning Guide

## 1. Update version references

Edit these files:

1. **`utils/version.py`** — single source of truth (`APP_VERSION`)
2. **`tests/test_gui_layout.py`** — hardcoded version assertion
3. **`README.md`** — 3 occurrences (release line, download filename, zip filename)

## 2. Build the portable distribution

```powershell
python build.py
```

`build.py` automatically regenerates `build/version_info.txt` from `utils/version.py`, so you do not need to edit that file manually. The final ZIP is written to `dist/XLSForm2Word_v<VERSION>_Windows.zip`.

## 3. Commit, tag, and push

```powershell
git add utils/version.py tests/test_gui_layout.py README.md
git commit -m "feat: Update version to <VERSION>"
git tag v<VERSION>
git push origin main
git push origin v<VERSION>
```

## 4. Create a GitHub release

1. Go to **Releases → Draft a new release** on GitHub (or use `gh release create`).
2. Select the `v<VERSION>` tag.
3. Title the release `v<VERSION>`.
4. Upload `dist/XLSForm2Word_v<VERSION>_Windows.zip` as a release asset.
5. Publish the release.

The README download link (`releases/latest`) will automatically point to the newest release.
