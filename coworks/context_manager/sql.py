import os
from contextlib import contextmanager

import sqlalchemy
from coworks.coworks import ContextManager
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker, scoped_session


class SqlContextManager(ContextManager):
    NAME = 'sql'

    def __init__(self, app, env_dialect_var_name=None, env_port_var_name=None, env_host_var_name=None,
                 env_dbname_var_name=None, env_user_var_name=None, env_passwd_var_name=None, env_var_prefix="SQL",
                 read_only=False, echo=False, name=NAME, **kwargs):
        super().__init__(app, name)
        self.dialect = self.port = self.host = self.dbname = self.user = self.passwd = None
        self.read_only = read_only
        self.echo = echo
        self.engine = self.scoped_session = None
        if env_var_prefix:
            self.env_dialect_var_name = f"{env_var_prefix}_DIALECT"
            self.env_port_var_name = f"{env_var_prefix}_PORT"
            self.env_host_var_name = f"{env_var_prefix}_HOST"
            self.env_dbname_var_name = f"{env_var_prefix}_DBNAME"
            self.env_user_var_name = f"{env_var_prefix}_USER"
            self.env_passwd_var_name = f"{env_var_prefix}_PASSWD"
        else:
            self.env_dialect_var_name = env_dialect_var_name
            self.env_port_var_name = env_port_var_name
            self.env_host_var_name = env_host_var_name
            self.env_dbname_var_name = env_dbname_var_name
            self.env_user_var_name = env_user_var_name
            self.env_passwd_var_name = env_passwd_var_name

        @app.before_first_activation
        def check_env_vars(event, context):
            self.dialect = os.getenv(self.env_dialect_var_name, 'postgresql+psycopg2')
            self.port = os.getenv(self.env_port_var_name, 5432)
            self.host = os.getenv(self.env_host_var_name)
            if not self.host:
                raise EnvironmentError(f'{self.env_host_var_name} not defined in environment.')
            self.dbname = os.getenv(self.env_dbname_var_name)
            if not self.dbname:
                raise EnvironmentError(f'{self.env_dbname_var_name} not defined in environment.')
            self.user = os.getenv(self.env_user_var_name)
            if not self.user:
                raise EnvironmentError(f'{self.env_user_var_name} not defined in environment.')
            self.passwd = os.getenv(self.env_passwd_var_name)
            if not self.passwd:
                raise EnvironmentError(f'{self.env_passwd_var_name} not defined in environment.')

            self.engine = create_engine(
                f'{self.dialect}://{self.user}:{self.passwd}@{self.host}:{self.port}/{self.dbname}', echo=self.echo
            )
            session_factory = sessionmaker(bind=self.engine)
            self.scoped_session = scoped_session(sessionmaker(session_factory))

        @app.after_activation
        def commit_session(response):
            self.scoped_session.commit()
            self.scoped_session.remove()
            return response

        @app.handle_exception
        def rollback_session(event, context, exception):
            self.scoped_session.rollback()
            self.scoped_session.remove()

    @contextmanager
    def __call__(self, **kwargs) -> scoped_session:
        session = self.scoped_session(future=True, **kwargs)

        if self.read_only:
            def do_nothing(*arg, **kw):
                return

            session.flush = do_nothing

        yield session

    def get_sqlalchemy_version(self):
        """Returns SQLAlchemy version."""
        return sqlalchemy.__version__, {'content-type': 'text/plain'}

    def _reflect_tables(self, schema, tables):
        metadata = MetaData(bind=self.engine)
        return map(lambda table: Table(table, metadata, autoload=True, autoload_with=self.engine, schema=schema),
                   tables)
