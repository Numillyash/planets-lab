from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "tools" / "cleanup-obsolete-corpus-db-generations.sh"


def test_obsolete_corpus_cleanup_is_guarded_and_exact() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)

    text = RUNNER.read_text(encoding="utf-8")

    assert "corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb" in text
    assert "corpus-v2compact-public36-20261002T083138Z-11cd75fa918d.duckdb" in text

    assert "corpus-v1-g233558-20260930T041155Z-8e2e7416675d.duckdb" in text
    assert "corpus-v1typed-g233558-20260930T143229Z-8e2e7416675d.duckdb" in text
    assert "corpus-v1typed-public36-20260930T211714Z-11cd75fa918d.duckdb" in text

    assert "5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a" in text
    assert "e1c0adc0a699d9d776f1fddb7dfc37c5a6714dfd9262f911a5939fda41cc7004" in text

    assert "DRY RUN ONLY." in text
    assert "--apply" in text
    assert "rm -f --" in text
    assert "rm -rf --" in text

    # Raw corpus ZIP/TRN cache must remain until public100 parity is complete.
    assert "validation/corpus/cache/loadall" not in text
