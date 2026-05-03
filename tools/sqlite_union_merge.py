#!/usr/bin/env python3
import argparse
import sqlite3
import sys


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_exists(conn: sqlite3.Connection, db_alias: str, table_name: str) -> bool:
    row = conn.execute(
        f"SELECT 1 FROM {db_alias}.sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def get_tables(conn: sqlite3.Connection, db_alias: str) -> list[str]:
    rows = conn.execute(
        f"""
        SELECT name
        FROM {db_alias}.sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [row[0] for row in rows]


def get_columns(conn: sqlite3.Connection, db_alias: str, table_name: str) -> list[str]:
    rows = conn.execute(
        f"PRAGMA {db_alias}.table_info({quote_ident(table_name)})"
    ).fetchall()
    return [row[1] for row in rows]


def get_pk_columns(conn: sqlite3.Connection, db_alias: str, table_name: str) -> list[str]:
    rows = conn.execute(
        f"PRAGMA {db_alias}.table_info({quote_ident(table_name)})"
    ).fetchall()
    pk_rows = sorted((row for row in rows if row[5] > 0), key=lambda r: r[5])
    return [row[1] for row in pk_rows]


def create_missing_table_from_source(conn: sqlite3.Connection, table_name: str) -> None:
    table_sql_row = conn.execute(
        """
        SELECT sql
        FROM src.sqlite_master
        WHERE type='table' AND name=?
        """,
        (table_name,),
    ).fetchone()

    if table_sql_row and table_sql_row[0]:
        conn.execute(table_sql_row[0])

    index_rows = conn.execute(
        """
        SELECT sql
        FROM src.sqlite_master
        WHERE type='index' AND tbl_name=? AND sql IS NOT NULL
        """,
        (table_name,),
    ).fetchall()

    for row in index_rows:
        if row[0]:
            conn.execute(row[0])


def merge_source_into_target(target_db: str, source_db: str) -> int:
    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("ATTACH DATABASE ? AS src", (source_db,))

    merged_tables = 0
    try:
        conn.execute("BEGIN")
        for table_name in get_tables(conn, "src"):
            if not table_exists(conn, "main", table_name):
                create_missing_table_from_source(conn, table_name)

            main_cols = get_columns(conn, "main", table_name)
            src_cols = get_columns(conn, "src", table_name)
            common_cols = [col for col in src_cols if col in set(main_cols)]

            if not common_cols:
                continue

            pk_cols = get_pk_columns(conn, "main", table_name)
            quoted_cols = ", ".join(quote_ident(c) for c in common_cols)
            select_cols = ", ".join(quote_ident(c) for c in common_cols)

            insert_sql = (
                f"INSERT INTO {quote_ident(table_name)} ({quoted_cols}) "
                f"SELECT {select_cols} FROM src.{quote_ident(table_name)}"
            )

            if pk_cols and all(pk in common_cols for pk in pk_cols):
                non_pk = [c for c in common_cols if c not in set(pk_cols)]
                quoted_pk = ", ".join(quote_ident(c) for c in pk_cols)
                if non_pk:
                    updates = ", ".join(
                        f"{quote_ident(c)}=excluded.{quote_ident(c)}" for c in non_pk
                    )
                    insert_sql += f" ON CONFLICT ({quoted_pk}) DO UPDATE SET {updates}"
                else:
                    insert_sql += f" ON CONFLICT ({quoted_pk}) DO NOTHING"

            conn.execute(insert_sql)
            merged_tables += 1

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("DETACH DATABASE src")
        conn.close()

    return merged_tables


def run_git_merge_driver(base_db: str, ours_db: str, theirs_db: str) -> int:
    _ = base_db
    merged_tables = merge_source_into_target(ours_db, theirs_db)
    print(f"sqlite_union merge completed: merged {merged_tables} table(s)")
    return 0


def run_manual_merge(target_db: str, source_db: str) -> int:
    merged_tables = merge_source_into_target(target_db, source_db)
    print(f"manual sqlite merge completed: merged {merged_tables} table(s)")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Best-effort union merge for SQLite databases."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    git_driver = subparsers.add_parser("git-driver", help="Git merge driver mode")
    git_driver.add_argument("base")
    git_driver.add_argument("ours")
    git_driver.add_argument("theirs")

    manual = subparsers.add_parser("merge", help="Manual merge mode")
    manual.add_argument("--target", required=True, help="Target SQLite file to update")
    manual.add_argument("--source", required=True, help="Source SQLite file to merge from")

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        if args.mode == "git-driver":
            return run_git_merge_driver(args.base, args.ours, args.theirs)
        if args.mode == "merge":
            return run_manual_merge(args.target, args.source)
        print("Unsupported mode", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"sqlite_union merge failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
