from __future__ import annotations

import zipfile
from pathlib import Path

from build import _document_contains_website_link
from utils.version import WEBSITE


def test_document_hyperlink_check_reads_relationship_target(tmp_path: Path) -> None:
    document_path = tmp_path / "document.docx"
    with zipfile.ZipFile(document_path, "w") as archive:
        archive.writestr("word/footer1.xml", '<w:hyperlink r:id="rId1"/>')
        archive.writestr(
            "word/_rels/footer1.xml.rels",
            f'<Relationship Id="rId1" Target="{WEBSITE}" TargetMode="External"/>',
        )

    assert _document_contains_website_link(document_path)
