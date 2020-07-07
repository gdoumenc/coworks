import os

import sqlalchemy
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.orm import sessionmaker

from ..coworks import TechMicroService


class SqlMicroService(TechMicroService):

    def __init__(self, *, dialect=None, host=None, port=None, dbname=None, user=None, **kwargs):
        super().__init__(**kwargs)
        self.dialect = dialect
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.password = None
        self.session = None

        self.__engine = None

        @self.before_first_activation
        def check_env_vars():
            if self.dialect is None:
                self.dialect = os.getenv('DIALECT')
                if not self.dialect:
                    raise EnvironmentError('DIALECT not defined in environment')
            if self.host is None:
                self.host = os.getenv('HOST')
                if not self.host:
                    raise EnvironmentError('HOST not defined in environment')
            if self.port is None:
                self.port = os.getenv('PORT')
                if self.port is None:
                    if self.dialect == 'mysql':
                        self.port = 3306
                    elif self.dialect == 'postgres':
                        self.port = 5432
            if self.dbname is None:
                self.dbname = os.getenv('DB_NAME')
                if not self.dbname:
                    raise EnvironmentError('DB_NAME not defined in environment')
            if self.user is None:
                self.user = os.getenv('USER')
                if not self.user:
                    raise EnvironmentError('USER not defined in environment')
            self.password = os.getenv('PASSWD', '')

        @self.before_activation
        def set_session():
            self.session = sessionmaker(bind=self.engine)()

    @property
    def engine(self):
        if not self.__engine:
            self.__engine = create_engine(
                f'{self.dialect}://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}', echo=False
            )
        return self.__engine

    def get_version(self):
        """Returns SQLAlchemy version."""
        return sqlalchemy.__version__

    def get_fetch(self, query: str = None, **kwargs):
        conn = self.engine.connect()
        rows = conn.execute(text(query), **kwargs).fetchall()
        return [dict(row) for row in rows]

    def reflect_tables(self, schema, tables):
        metadata = MetaData(bind=self.engine)
        return list(
            map(lambda table: Table(table, metadata, autoload=True, autoload_with=self.engine, schema=schema), tables))
