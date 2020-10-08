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
        def check_env_vars(event, context):
            if self.dialect is None:
                self.dialect = os.getenv(self.dialect_env_var_name)
                if not self.dialect:
                    raise EnvironmentError(f"{self.dialect_env_var_name} not defined in environment.")
            if self.host is None:
                self.host = os.getenv(self.host_env_var_name)
                if not self.host:
                    raise EnvironmentError(f"{self.host_env_var_name} not defined in environment.")
            if self.port is None:
                self.port = os.getenv(self.port_env_var_name)
                if self.port is None:
                    if self.dialect.startswith('mysql'):
                        self.port = 3306
                    elif self.dialect == 'postgres':
                        self.port = 5432
            if self.dbname is None:
                self.dbname = os.getenv(self.dbname_env_var_name)
                if not self.dbname:
                    raise EnvironmentError(f"{self.dbname_env_var_name} not defined in environment.")
            if self.user is None:
                self.user = os.getenv(self.user_env_var_name)
                if not self.user:
                    raise EnvironmentError(f"{self.user_env_var_name} not defined in environment.")
            self.password = os.getenv(self.passwd_env_var_name, '')

        @self.before_activation
        def set_session(event, context):
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
        return sqlalchemy.__version__, {'content-type': 'text/plain'}

    def get_fetch(self, query: str = None, **kwargs):
        conn = self.engine.connect()
        rows = conn.execute(text(query), **kwargs).fetchall()
        return [dict(row) for row in rows]

    def reflect_tables(self, schema, tables):
        metadata = MetaData(bind=self.engine)
        return list(
            map(lambda table: Table(table, metadata, autoload=True, autoload_with=self.engine, schema=schema), tables))

    @property
    def dialect_env_var_name(self):
        return 'DIALECT'

    @property
    def host_env_var_name(self):
        return 'HOST'

    @property
    def port_env_var_name(self):
        return 'PORT'

    @property
    def dbname_env_var_name(self):
        return 'DBNAME'

    @property
    def user_env_var_name(self):
        return 'USER'

    @property
    def passwd_env_var_name(self):
        return 'PASSWD'
