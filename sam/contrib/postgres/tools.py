import json
import logging

import psycopg

from . import config

logger = logging.getLogger(__name__)


def fetch_all(query: str, _context=None) -> str:
    """Fetch data from a PostgreSQL database using a SELECT query and return it as JSON.

    Args:
        query: SQL query to execute. It should be a SELECT statement.
    """
    with (
        psycopg.connect(
            dbname=config.DATABASE,
            user=config.USERNAME,
            password=config.PASSWORD,
            host=config.HOSTNAME,
            port=config.PORT,
        ) as conn,
        conn.cursor() as cur,
    ):
        try:
            cur.execute(
                f"select jsonb_build_object('data', jsonb_agg(t)) from ({query}) t"  # noqa: S608
            )
        except psycopg.ProgrammingError as e:
            logger.exception("Error executing query: %s", query)
            return str(e)

        # Fetch the results
        return json.dumps([row[0] for row in cur.fetchall()])
