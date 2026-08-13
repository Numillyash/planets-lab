import io
import zipfile

import pytest

from planets_lab.corpus.archive import archive_members
from planets_lab.corpus.manifest import settings_hash


def test_settings_hash_is_key_order_independent() -> None:
    assert settings_hash({"a": 1, "b": 2}) == settings_hash({"b": 2, "a": 1})


def test_archive_members_validates_zip() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("turns/example.json", "{}")
    assert archive_members(buffer.getvalue()) == ("turns/example.json",)


def test_archive_members_rejects_non_zip() -> None:
    with pytest.raises(ValueError, match="not a ZIP"):
        archive_members(b"not a zip")
