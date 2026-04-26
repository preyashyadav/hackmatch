from collections.abc import Generator
import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

import config


logger = logging.getLogger(__name__)

connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(config.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_sqlite_schema() -> None:
    if not config.DATABASE_URL.startswith("sqlite"):
        return

    with engine.begin() as connection:
        inspector = inspect(connection)
        if "matches" not in inspector.get_table_names():
            return

        columns = {column["name"] for column in inspector.get_columns("matches")}
        missing_columns = [
            ("proposer_attendee_id", "VARCHAR(12)"),
            ("pair_key", "VARCHAR(25)"),
            ("theme_alignment_a_score", "FLOAT"),
            ("theme_alignment_b_score", "FLOAT"),
        ]

        for column_name, column_type in missing_columns:
            if column_name not in columns:
                connection.execute(text(f"ALTER TABLE matches ADD COLUMN {column_name} {column_type}"))

        connection.execute(
            text(
                "UPDATE matches "
                "SET proposer_attendee_id = COALESCE(proposer_attendee_id, attendee_a_id) "
                "WHERE proposer_attendee_id IS NULL"
            )
        )
        connection.execute(
            text(
                "UPDATE matches "
                "SET theme_alignment_a_score = COALESCE(theme_alignment_a_score, theme_alignment_score) "
                "WHERE theme_alignment_a_score IS NULL"
            )
        )
        connection.execute(
            text(
                "UPDATE matches "
                "SET theme_alignment_b_score = COALESCE(theme_alignment_b_score, theme_alignment_score) "
                "WHERE theme_alignment_b_score IS NULL"
            )
        )
        connection.execute(
            text(
                "UPDATE matches "
                "SET pair_key = COALESCE("
                "pair_key, "
                "CASE "
                "WHEN attendee_a_id < attendee_b_id THEN attendee_a_id || ':' || attendee_b_id "
                "ELSE attendee_b_id || ':' || attendee_a_id "
                "END"
                ") "
                "WHERE pair_key IS NULL"
            )
        )

        try:
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_matches_pair_key ON matches(pair_key)"))
        except Exception:
            logger.exception("Failed to create unique pair_key index for matches.")
