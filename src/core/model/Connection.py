from src.core.model.Database import Database


class Connection:
    def __init__(self, db: Database) -> None:
        self.db = db
