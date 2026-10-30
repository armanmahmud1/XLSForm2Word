# Stable File Path Layout Design

## Goal

Prevent a selected XLSX file path from widening the main application window.

## Approach

Keep the full selected path in the file-drop zone, but make its label eligible
to shrink within the horizontal layout. The label will wrap to additional lines
when the available width is insufficient rather than expanding the scroll
content or main window. The full value remains selectable and is available in
the existing tooltip.

## Scope

- Update only the reusable `FileDropZone` path label sizing behavior.
- Preserve existing drag-and-drop, file browsing, selection, and tooltip
  behavior.
- Add a focused GUI test if the existing test setup supports it.

## Error Handling

No new error paths are introduced. Empty paths continue to show the existing
placeholder text.

## Verification

Verify that a long selected path increases the drop-zone height when needed,
without increasing its width or the main window's width.
