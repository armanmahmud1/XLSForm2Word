# Stable File Path Layout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep long selected XLSX paths from increasing the application window width.

**Architecture:** `FileDropZone` owns the label that displays the selected path. Configure that label's horizontal size policy to permit shrinking in its existing expanding text-layout column; its existing word-wrap setting then uses available height rather than forcing the parent layout wider. A narrow GUI test validates the policy without modifying main-window behavior.

**Tech Stack:** Python 3.12, PySide6, pytest.

---

### Task 1: Add a regression test for the path label sizing

**Files:**
- Modify: `tests/test_core.py`
- Test: `tests/test_core.py`

**Step 1: Write the failing test**

Add a GUI test that creates a `QApplication` if one does not exist, constructs `FileDropZone`, and asserts that its internal path label has `QSizePolicy.Policy.Ignored` horizontally while word wrapping remains enabled.

```python
def test_file_drop_zone_path_label_can_shrink_horizontally() -> None:
    app = QApplication.instance() or QApplication([])
    drop_zone = FileDropZone()

    assert drop_zone._path.wordWrap()
    assert drop_zone._path.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Ignored
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_core.py::test_file_drop_zone_path_label_can_shrink_horizontally -q`

Expected: FAIL because the path label currently has the default horizontal size policy.

**Step 3: Commit the test**

    git add tests/test_core.py
    git commit -m "test: cover file path label shrink behavior"

### Task 2: Make the path label shrink within the drop zone

**Files:**
- Modify: `gui/widgets.py:40-43`
- Test: `tests/test_core.py`

**Step 1: Implement the minimal change**

Immediately after enabling word wrap on `self._path`, set a horizontal `QSizePolicy.Policy.Ignored` and vertical `QSizePolicy.Policy.Preferred` policy.

```python
self._path.setSizePolicy(
    QSizePolicy.Policy.Ignored,
    QSizePolicy.Policy.Preferred,
)
```

This preserves the existing layout stretch factor while allowing the text label to accept the width offered by the drop zone and wrap long paths.

**Step 2: Run the focused test**

Run: `python -m pytest tests/test_core.py::test_file_drop_zone_path_label_can_shrink_horizontally -q`

Expected: PASS.

**Step 3: Run the full test suite**

Run: `python -m pytest -q`

Expected: PASS with no regressions.

**Step 4: Commit the implementation**

    git add gui/widgets.py tests/test_core.py
    git commit -m "fix: prevent selected file path widening window"

### Task 3: Manually validate a long-path selection

**Files:**
- Modify: none

**Step 1: Launch the application**

Run: `python app/main.py`

**Step 2: Select a deeply nested XLSX file**

Confirm the file-drop zone uses additional vertical space as necessary while the main window width remains unchanged. Confirm the full path can be selected and appears in its tooltip.
