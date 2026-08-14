from __future__ import annotations

import io
import zipfile

from planets_lab.corpus.archive import read_archive_members


def _zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("player1-turn0.trn", b"zero")
        archive.writestr("player1-turn1.trn", b"one")
        archive.writestr("ignored.txt", b"ignored")
    return buffer.getvalue()


def test_read_archive_members_reads_requested_members_in_one_bulk_call() -> None:
    data = _zip_bytes()

    result = read_archive_members(
        data,
        ["player1-turn0.trn", "player1-turn1.trn"],
    )

    assert result == {
        "player1-turn0.trn": b"zero",
        "player1-turn1.trn": b"one",
    }
