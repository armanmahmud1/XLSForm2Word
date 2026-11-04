# Versioning Guide

When bumping the version, update these files:

1. **`utils/version.py`** — single source of truth (`APP_VERSION`)
2. **`tests/test_gui_layout.py`** — hardcoded version assertion
3. **`README.md`** — 3 occurrences (release line, download filename, zip filename)

Then run:

```powershell
python build.py
```

`build.py` automatically regenerates `build/version_info.txt` from `utils/version.py`, so you do not need to edit that file manually.
