import os
from contextlib import contextmanager
from typing import Iterator

from dotenv import load_dotenv
from psycopg import Connection
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

load_dotenv()

_pool: ConnectionPool | None = None


def _connection_kwargs() -> dict[str, object]:
    required = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [
        name for name in required if not os.getenv(name) or os.getenv(name) == "CHANGE_ME"
    ]
    if missing:
        raise RuntimeError(f"Missing required database settings: {', '.join(missing)}")
    return {
        "host": os.environ["DB_HOST"],
        "port": int(os.environ["DB_PORT"]),
        "dbname": os.environ["DB_NAME"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "sslmode": "require",
        "connect_timeout": 10,
    }


def open_pool() -> None:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            kwargs={**_connection_kwargs(), "row_factory": dict_row},
            min_size=1,
            max_size=5,
            open=False,
        )
        _pool.open(wait=True, timeout=15)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def get_connection() -> Iterator[Connection]:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    with _pool.connection() as connection:
        yield connection
