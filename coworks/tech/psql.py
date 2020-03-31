import os
import sqlalchemy
import re

from chalice import BadRequestError
from sqlalchemy import create_engine, text, MetaData, or_, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from collections import defaultdict
from typing import List

from ..coworks import TechMicroService


class PsqlMicroService(TechMicroService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialect = self.host = self.port = self.dbname = self.user = self.password = None
        self.engine = None
        self.session = None
        self.tables = defaultdict(dict)

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
                self.password = ''

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
                echo=False)

    def get_version(self):
        """Returns SQLAlchemy version."""
        return sqlalchemy.__version__

    def get_fetch(self, query: str = None, **kwargs):
        conn = self.engine.connect()
        rows = conn.execute(text(query), **kwargs).fetchall()
        return [dict(row) for row in rows]

    def reflect_table(self, schema, table):
        """ Given a schema and a table name, reflects the table to declarative ans stores it in a dict.
        Saves the session object bound to the engine created. """
        Base = declarative_base()
        metadata = MetaData(bind=self.engine)
        Base.metadata = metadata
        metadata.reflect(schema=schema)
        tablename = f'{schema}.{table}'
        try:
            tableobj = metadata.tables[tablename]
        except KeyError:
            raise BadRequestError(f"Table {table} not found in schema {schema}")
        else:
            self.tables[schema][table] = type(str(table), (Base,), {'__table__': tableobj})
            self.session = sessionmaker(bind=self.engine)()

    def eval(self, string, schema):
        """ Eval string as sqlalchemy.sql.elements.BinaryExpression expression. Undefined names must correspond to
        tables existing in the database so that the tables are reflected and stored in self.tables. Undefined names
        are then replaced by names corresponding to the objects thus created. """
        print("evaluating", string)
        try:
            return eval(string) if string else None
        except NameError as e:
            table_name = re.search("\'(.*?)\'", str(e))
            table_name = re.sub("'", "", table_name.group())
            if not self.tables['schema'].get(table_name):
                self.reflect_table(schema, table_name)
            string = re.sub(f"({table_name})", rf"self.tables['{schema}']['{table_name}']", string)
            return self.eval(string, schema)

    def get_query(self, entities: str, methods: str, arguments: List[str] = None, schema: str = 'public'):
        """ Execute SQLAlchemy method of the Query class and returns the result as Json

        schema : name of the database schema used for the query
        entities : comma-separated list of arguments passed to the query() method
        methods : comma-separated list of methods from the Query class to be exectued in sequence
        arguments : list of arguments to pass to each of the previous methods, syntax: ?arguments=val1&arguments=val2

        example : get http://127.0.0.1:8000/query/order_orderline.id,order_orderline.status/filter,all?arguments=or_(order_orderline.order_id%3D%3D123,%20order_orderline.order_id%3D%3D456)&arguments&schema=tenant_kc
        """
        methods = methods.split(',')
        entities = entities.split(',')
        arguments = list(map(lambda x: self.eval(x, schema), arguments))
        query = self.session.query(*entities)
        for method, args in zip(methods, arguments):
            query = getattr(query, method)(args) if args is not None else getattr(query, method)()
        return query
