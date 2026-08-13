from __future__ import annotations

import io
import zipfile


def archive_members(data: bytes) -> tuple[str, ...]:
    buffer = io.BytesIO(data)
    if not zipfile.is_zipfile(buffer):
        raise ValueError("response is not a ZIP archive")
    buffer.seek(0)
    with zipfile.ZipFile(buffer) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise ValueError(f"ZIP CRC failure at {bad!r}")
        return tuple(archive.namelist())
