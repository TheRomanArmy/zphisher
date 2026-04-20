import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

    # Separate bookkeeping database.
    BOOKKEEPING_DB = os.path.join(INSTANCE_DIR, "bookkeeping.sqlite3")

    # Existing scheduler/invoice database path (read-only by convention in v1).
    SCHEDULER_DB = os.environ.get(
        "SCHEDULER_DB_PATH", os.path.join(INSTANCE_DIR, "scheduler.sqlite3")
    )
