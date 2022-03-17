import os

from flask_sqlalchemy import SQLAlchemy as FlaskSQLAlchemy

from coworks import Blueprint


class SqlAlchemy(Blueprint):
    SQLALCHEMY_KWARGS = {}

    def __init__(self, name='sqlalchemy', env_engine_var_name: str = '',
                 env_url_var_name: str = '', env_dbname_var_name: str = '', env_user_var_name: str = '',
                 env_passwd_var_name: str = '', env_var_prefix: str = '', **kwargs):
        super().__init__(name=name, **kwargs)
        self.db = None
        if env_var_prefix:
            self.env_engine_var_name = f"{env_var_prefix}_ENGINE"
            self.env_url_var_name = f"{env_var_prefix}_URL"
            self.env_dbname_var_name = f"{env_var_prefix}_DBNAME"
            self.env_user_var_name = f"{env_var_prefix}_USER"
            self.env_passwd_var_name = f"{env_var_prefix}_PASSWD"
        else:
            self.env_engine_var_name = env_engine_var_name
            self.env_url_var_name = env_url_var_name
            self.env_dbname_var_name = env_dbname_var_name
            self.env_user_var_name = env_user_var_name
            self.env_passwd_var_name = env_passwd_var_name

    def init_app(self, app):
        db_engine = os.getenv(self.env_engine_var_name)
        if not db_engine:
            raise EnvironmentError(f'{self.env_engine_var_name} not defined in environment.')
        db_url = os.getenv(self.env_url_var_name)
        if not db_url:
            raise EnvironmentError(f'{self.env_url_var_name} not defined in environment.')
        db_name = os.getenv(self.env_dbname_var_name)
        if not db_name:
            raise EnvironmentError(f'{self.env_dbname_var_name} not defined in environment.')
        db_user = os.getenv(self.env_user_var_name)
        if not db_user:
            raise EnvironmentError(f'{self.env_user_var_name} not defined in environment.')
        db_pasword = os.getenv(self.env_passwd_var_name)
        if not db_pasword:
            raise EnvironmentError(f'{self.env_passwd_var_name} not defined in environment.')

        app.config['SQLALCHEMY_DATABASE_URI'] = f"{db_engine}://{db_user}:{db_pasword}@{db_url}/{db_name}"
        app.config['SQLALCHEMY_BINDS'] = {}
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        self.db = FlaskSQLAlchemy(app, **self.SQLALCHEMY_KWARGS)

    @property
    def session(self):
        return self.db.session
