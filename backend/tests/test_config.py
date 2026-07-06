"""DATABASE_URL scheme normalization (app/config.py) - so managed-host URLs use our psycopg driver."""

from app.config import Settings


def test_bare_postgres_scheme_gets_psycopg_driver():
    assert Settings(database_url="postgres://u:p@h:5432/d").database_url == "postgresql+psycopg://u:p@h:5432/d"


def test_postgresql_scheme_gets_psycopg_driver():
    assert Settings(database_url="postgresql://u:p@h/d").database_url == "postgresql+psycopg://u:p@h/d"


def test_explicit_driver_is_left_alone():
    assert Settings(database_url="postgresql+psycopg://u:p@h/d").database_url == "postgresql+psycopg://u:p@h/d"
    assert Settings(database_url="postgresql+asyncpg://u:p@h/d").database_url == "postgresql+asyncpg://u:p@h/d"


def test_query_params_survive_normalization():
    got = Settings(database_url="postgres://u:p@h/d?sslmode=require").database_url
    assert got == "postgresql+psycopg://u:p@h/d?sslmode=require"
