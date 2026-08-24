from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")


def _print_rows(con: duckdb.DuckDBPyConnection, title: str, sql: str) -> None:
    print(f"\n===== {title} =====")
    for row in con.execute(sql).fetchall():
        print(*row)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit current Chunnel labels whose match set contains multiple events. "
            "The production matcher has already constrained every event in such a set "
            "to the same pre-Chunnel position and observed destination, so this audit "
            "measures route-equivalent event multiplicity rather than discovering new events."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    con = duckdb.connect(str(args.database), read_only=True)
    try:
        totals = con.execute(
            """
            SELECT
                count(*) AS labeled_rows,
                sum(CASE WHEN chunnel_match_count > 1 THEN 1 ELSE 0 END) AS multiple_match_rows,
                sum(CASE WHEN chunnel_match_count > 1 AND chunnel_explained = false THEN 1 ELSE 0 END)
                    AS multiple_match_unexplained,
                sum(CASE WHEN chunnel_match_count > 1 AND post_chunnel_residual = true THEN 1 ELSE 0 END)
                    AS multiple_match_post_chunnel,
                sum(CASE WHEN chunnel_match_count > 1 AND post_horwasp_strong_residual = true THEN 1 ELSE 0 END)
                    AS multiple_match_final_residual,
                sum(CASE WHEN chunnel_match_count > 1
                              AND warp = 0
                              AND target_x = x_before
                              AND target_y = y_before
                         THEN 1 ELSE 0 END) AS multiple_match_warp0_self_waypoint
            FROM movement_labeled_residual
            """
        ).fetchone()
        print("===== CHUNNEL ROUTE-EQUIVALENT AMBIGUITY AUDIT =====")
        names = (
            "labeled_rows",
            "multiple_match_rows",
            "multiple_match_unexplained",
            "multiple_match_post_chunnel",
            "multiple_match_final_residual",
            "multiple_match_warp0_self_waypoint",
        )
        for name, value in zip(names, totals or ()):
            print(f"{name}= {int(value or 0)}")

        _print_rows(
            con,
            "MATCH COUNT DISTRIBUTION",
            """
            SELECT chunnel_match_count, count(*) AS n
            FROM movement_labeled_residual
            WHERE chunnel_match_count > 1
            GROUP BY chunnel_match_count
            ORDER BY chunnel_match_count
            """,
        )
        _print_rows(
            con,
            "CURRENT CHUNNEL CATEGORIES",
            """
            SELECT coalesce(chunnel_category, '<null>'), count(*) AS n
            FROM movement_labeled_residual
            WHERE chunnel_match_count > 1
            GROUP BY 1
            ORDER BY n DESC, 1
            """,
        )
        _print_rows(
            con,
            "BY GAME",
            """
            SELECT game_id, count(*) AS n
            FROM movement_labeled_residual
            WHERE chunnel_match_count > 1
            GROUP BY game_id
            ORDER BY n DESC, game_id
            """,
        )
        _print_rows(
            con,
            "BY HULL",
            """
            SELECT hull_id, count(*) AS n, count(DISTINCT game_id) AS games
            FROM movement_labeled_residual
            WHERE chunnel_match_count > 1
            GROUP BY hull_id
            ORDER BY n DESC, hull_id
            LIMIT 40
            """,
        )
        _print_rows(
            con,
            "BY BASELINE CATEGORY",
            """
            SELECT baseline_category, count(*) AS n
            FROM movement_labeled_residual
            WHERE chunnel_match_count > 1
            GROUP BY baseline_category
            ORDER BY n DESC, baseline_category
            """,
        )
        _print_rows(
            con,
            "FINAL-RESIDUAL EXAMPLES",
            """
            SELECT
                game_id,
                before_archive_turn,
                ship_id,
                hull_id,
                baseline_category,
                warp,
                chunnel_match_count,
                round(observed_distance, 3) AS observed_distance
            FROM movement_post_horwasp_strong_residual
            WHERE chunnel_match_count > 1
            ORDER BY game_id, before_archive_turn, ship_id
            LIMIT 80
            """,
        )
    finally:
        con.close()

    print("\n===== INTERPRETATION =====")
    print(
        "Every counted row already has multiple observed Chunnel events with the same "
        "candidate pre-Chunnel position and the same observed destination, because that "
        "is the production match predicate. Event identity may be ambiguous; the movement "
        "route is not. Compare this count with the later production differential after "
        "route-equivalent match handling is changed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
