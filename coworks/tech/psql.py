import os
import sqlalchemy
from sqlalchemy import create_engine, text

from ..coworks import TechMicroService


class PsqlMicroService(TechMicroService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialect = self.host = self.port = self.dbname = self.user = self.password = None
        self.engine = None

        @self.before_first_request
        def check_env_vars():
            self.dialect = os.getenv('DIALECT')
            if not self.dialect:
                raise EnvironmentError('DIALECT not defined in environment')
            self.host = os.getenv('HOST')
            if not self.host:
                raise EnvironmentError('HOST not defined in environment')
            self.port = os.getenv('PORT')
            self.dbname = os.getenv('DB_NAME')
            if not self.dbname:
                raise EnvironmentError('DB_NAME not defined in environment')
            self.user = os.getenv('USER')
            if not self.user:
                raise EnvironmentError('USER not defined in environment')
            self.password = os.getenv('PASSWD')
            if not self.password:
                raise EnvironmentError('PASSWD not defined in environment')

        @self.before_first_request
        def engine():
            if self.port is None:
                if self.dialect == 'mysql':
                    self.port = 3306
                elif self.dialect == 'postgres':
                    self.port = 5432

            print(f'{self.dialect}://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}')
            self.engine = create_engine(
                f'{self.dialect}://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}',
                echo=True)

    def get_version(self):
        """Returns SQLAlchemy version."""
        return sqlalchemy.__version__

    def get_fetch(self, query: str = None, **kwargs):
        conn = self.engine.connect()
        rows = conn.execute(text(query), **kwargs).fetchall()
        return [dict(row) for row in rows]
