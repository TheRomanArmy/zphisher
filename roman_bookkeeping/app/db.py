import os
import sqlite3
from flask import current_app, g


def get_db():
    if "db" not in g:
        db_path = current_app.config["BOOKKEEPING_DB"]
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    schema_path = os.path.join(current_app.config["BASE_DIR"], "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        db.executescript(f.read())
    db.commit()


def init_app(app):
    os.makedirs(app.config["INSTANCE_DIR"], exist_ok=True)
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        """Initialize the bookkeeping SQLite database schema."""
        init_db()
        print("Initialized bookkeeping database.")
