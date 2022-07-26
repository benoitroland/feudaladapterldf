from ldf_adapter.utils import ObjectFactory
from ldf_adapter.approval.db.sqlite import SqlitePendingDBProvider


class PendingDBProvider(ObjectFactory):
    def get(self, db_type, **kwargs):
        """Returns a configured pending DB of given type.

        Args:
            db_type (str): type of database to return. supported db types: sqlite
            **kwargs: additional arguments to pass to db builder.
        Returns:
            PendingDB: configured notifier of given type.
        """
        return self.create(db_type, **kwargs)


databases = PendingDBProvider()
databases.register_builder("sqlite", SqlitePendingDBProvider())
