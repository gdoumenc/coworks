import os
import sqlalchemy
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import Session

from ..coworks import Blueprint


class SqlAlchemy(Blueprint):

    def __init__(self, env_dialect_var_name=None, env_port_var_name=None, env_host_var_name=None,
                 env_dbname_var_name=None, env_user_var_name=None, env_passwd_var_name=None, env_var_prefix="SQL",
                 read_only=False, echo=False, **kwargs):
        super().__init__(name='sqlalchemy', **kwargs)
        self.dialect = self.port = self.host = self.dbname = self.user = self.passwd = None
        self.read_only = read_only
        self.echo = echo
        self.__engine = self.__session = None
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

        @self.before_first_activation
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

        @self.after_activation
        def commit_session(response):
            if hasattr(self, '__session'):
                session = getattr(self, '__session')
                session.commit()
                delattr(self, '__session')
            return response

        @self.handle_exception
        def rollback_session(event, context, exception):
            if hasattr(self, '__session'):
                session = getattr(self, '__session')
                session.rollback()
                delattr(self, '__session')

    @property
    def engine(self):
        """Creates the engine once."""
        if not hasattr(self, '__engine'):
            self.__engine = create_engine(
                f'{self.dialect}://{self.user}:{self.passwd}@{self.host}:{self.port}/{self.dbname}', echo=self.echo
            )
        return self.__engine

    @property
    def session(self):
        """Creates the session on demand."""
        if not hasattr(self, '__session'):
            self.__session = self._get_session()
        return self.__session

    @property
    def schema_translate_map(self):
        """May be redefined to have a specific shema."""
        return {}

    def get_sqlalchemy_version(self):
        """Returns SQLAlchemy version."""
        return sqlalchemy.__version__, {'content-type': 'text/plain'}

    def _get_session(self):
        schema_engine = self.engine.execution_options(schema_translate_map=self.schema_translate_map)
        session = Session(schema_engine, future=True)

        if self.read_only:
            def do_nothing(*arg, **kwargs):
                return

            session.flush = do_nothing

        return session

    def _reflect_tables(self, schema, tables):
        engine = self.session.get_bind()
        metadata = MetaData(bind=engine)
        return map(lambda table: Table(table, metadata, autoload=True, autoload_with=engine, schema=schema), tables)
