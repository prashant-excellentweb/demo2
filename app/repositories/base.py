from sqlalchemy.orm import Session


class BaseRepository:
    """Owns data access for one aggregate.

    Repositories never commit: the calling service decides the transaction
    boundary so a single request stays one atomic unit of work.
    """

    def __init__(self, session: Session):
        self.session = session

    def add(self, instance: object) -> None:
        self.session.add(instance)

    def delete(self, instance: object) -> None:
        self.session.delete(instance)

    def flush(self) -> None:
        self.session.flush()
