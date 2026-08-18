from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import duckdb


def write_tsv(path: Path, columns: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize the current compiled post-Horwasp residual across games, hulls, "
            "settings hashes and simple movement-state signatures."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("validation/corpus/compiled/v1/corpus.duckdb"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--top", type=int, default=100)
    args = parser.parse_args()

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(args.database), read_only=True)
    try:
        hull_rows_raw = con.execute(
            """
            SELECT
                hull_id,
                count(*) AS residual_rows,
                count(DISTINCT game_id) AS games,
                count(DISTINCT settings_hash) AS settings_hashes,
                sum(CASE WHEN warp = 0 THEN 1 ELSE 0 END) AS warp0_rows,
                sum(CASE WHEN target_x = x_before AND target_y = y_before THEN 1 ELSE 0 END) AS waypoint_self_rows,
                sum(CASE WHEN x_after = target_x AND y_after = target_y THEN 1 ELSE 0 END) AS endpoint_target_rows,
                sum(CASE WHEN observed_distance <= 2.0 THEN 1 ELSE 0 END) AS micro_rows,
                sum(CASE WHEN abs(observed_dx) > 1000 OR abs(observed_dy) > 1000 THEN 1 ELSE 0 END) AS raw_seam_rows,
                round(avg(observed_distance), 3) AS avg_distance,
                round(min(observed_distance), 3) AS min_distance,
                round(max(observed_distance), 3) AS max_distance
            FROM movement_post_horwasp_strong_residual
            WHERE hull_id IS NOT NULL
            GROUP BY hull_id
            ORDER BY residual_rows DESC, hull_id
            """
        ).fetchall()

        hull_columns = (
            "hull_id",
            "residual_rows",
            "games",
            "settings_hashes",
            "warp0_rows",
            "waypoint_self_rows",
            "endpoint_target_rows",
            "micro_rows",
            "raw_seam_rows",
            "avg_distance",
            "min_distance",
            "max_distance",
        )
        hull_rows = [dict(zip(hull_columns, row)) for row in hull_rows_raw]

        game_hull_raw = con.execute(
            """
            SELECT
                game_id,
                hull_id,
                count(*) AS residual_rows,
                sum(CASE WHEN warp = 0 THEN 1 ELSE 0 END) AS warp0_rows,
                sum(CASE WHEN target_x = x_before AND target_y = y_before THEN 1 ELSE 0 END) AS waypoint_self_rows,
                sum(CASE WHEN observed_distance <= 2.0 THEN 1 ELSE 0 END) AS micro_rows,
                sum(CASE WHEN abs(observed_dx) > 1000 OR abs(observed_dy) > 1000 THEN 1 ELSE 0 END) AS raw_seam_rows,
                round(avg(observed_distance), 3) AS avg_distance
            FROM movement_post_horwasp_strong_residual
            WHERE hull_id IS NOT NULL
            GROUP BY game_id, hull_id
            ORDER BY residual_rows DESC, game_id, hull_id
            """
        ).fetchall()
        game_hull_columns = (
            "game_id",
            "hull_id",
            "residual_rows",
            "warp0_rows",
            "waypoint_self_rows",
            "micro_rows",
            "raw_seam_rows",
            "avg_distance",
        )
        game_hull_rows = [dict(zip(game_hull_columns, row)) for row in game_hull_raw]

        signature_raw = con.execute(
            """
            SELECT
                hull_id,
                warp,
                CASE WHEN target_x = x_before AND target_y = y_before THEN true ELSE false END AS waypoint_self,
                CASE WHEN x_after = target_x AND y_after = target_y THEN true ELSE false END AS endpoint_target,
                CASE
                    WHEN observed_distance <= 0.75 THEN 'stationary'
                    WHEN observed_distance <= 2.0 THEN 'micro_1_2'
                    WHEN observed_distance <= 10.0 THEN 'tiny_2_10'
                    WHEN observed_distance <= 40.0 THEN 'short_10_40'
                    WHEN observed_distance <= 100.0 THEN 'medium_40_100'
                    WHEN observed_distance <= 500.0 THEN 'long_100_500'
                    ELSE 'very_long_500_plus'
                END AS distance_bucket,
                CASE WHEN abs(observed_dx) > 1000 OR abs(observed_dy) > 1000 THEN true ELSE false END AS raw_seam,
                coalesce(horwasp_candidate_kind, 'none') AS horwasp_kind,
                coalesce(horwasp_category, 'none') AS horwasp_category,
                count(*) AS rows,
                count(DISTINCT game_id) AS games
            FROM movement_post_horwasp_strong_residual
            WHERE hull_id IS NOT NULL
            GROUP BY ALL
            ORDER BY rows DESC, hull_id
            LIMIT ?
            """,
            [max(1, int(args.top) * 10)],
        ).fetchall()
        signature_columns = (
            "hull_id",
            "warp",
            "waypoint_self",
            "endpoint_target",
            "distance_bucket",
            "raw_seam",
            "horwasp_kind",
            "horwasp_category",
            "rows",
            "games",
        )
        signature_rows = [dict(zip(signature_columns, row)) for row in signature_raw]

        settings_raw = con.execute(
            """
            SELECT
                settings_hash,
                count(*) AS residual_rows,
                count(DISTINCT game_id) AS games,
                count(DISTINCT hull_id) AS hulls
            FROM movement_post_horwasp_strong_residual
            GROUP BY settings_hash
            ORDER BY residual_rows DESC, settings_hash
            """
        ).fetchall()
        settings_columns = ("settings_hash", "residual_rows", "games", "hulls")
        settings_rows = [dict(zip(settings_columns, row)) for row in settings_raw]

        category_raw = con.execute(
            """
            SELECT
                coalesce(horwasp_candidate_kind, 'none') AS horwasp_kind,
                coalesce(horwasp_category, 'none') AS horwasp_category,
                count(*) AS rows,
                count(DISTINCT game_id) AS games,
                count(DISTINCT hull_id) AS hulls
            FROM movement_post_horwasp_strong_residual
            GROUP BY 1, 2
            ORDER BY rows DESC, 1, 2
            """
        ).fetchall()
        category_columns = ("horwasp_kind", "horwasp_category", "rows", "games", "hulls")
        category_rows = [dict(zip(category_columns, row)) for row in category_raw]

        total = con.execute(
            "SELECT count(*) FROM movement_post_horwasp_strong_residual"
        ).fetchone()[0]
        games = con.execute(
            "SELECT count(DISTINCT game_id) FROM movement_post_horwasp_strong_residual"
        ).fetchone()[0]
    finally:
        con.close()

    write_tsv(out / "hulls.tsv", hull_columns, hull_rows)
    write_tsv(out / "game-hulls.tsv", game_hull_columns, game_hull_rows)
    write_tsv(out / "signatures.tsv", signature_columns, signature_rows)
    write_tsv(out / "settings.tsv", settings_columns, settings_rows)
    write_tsv(out / "categories.tsv", category_columns, category_rows)

    summary = {
        "schema": "planets-lab.compiled-residual-cross-game-summary.v1",
        "database": str(args.database),
        "residual_rows": int(total),
        "games": int(games),
        "top_hulls": hull_rows[: max(1, int(args.top))],
        "top_signatures": signature_rows[: max(1, int(args.top))],
        "categories": category_rows,
        "settings": settings_rows,
    }
    (out / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("===== COMPILED CROSS-GAME RESIDUAL SUMMARY =====")
    print(f"residual_rows: {total}")
    print(f"games:         {games}")
    print("top_hulls:")
    for row in hull_rows[: min(max(1, int(args.top)), 30)]:
        print(row)
    print("top_signatures:")
    for row in signature_rows[: min(max(1, int(args.top)), 40)]:
        print(row)
    print(f"output_dir: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
