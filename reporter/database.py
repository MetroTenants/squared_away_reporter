from __future__ import absolute_import, print_function, unicode_literals

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from .config import DB_CONN


engine = create_engine(DB_CONN, convert_unicode=True, server_side_cursors=True)

db_session = scoped_session(
    sessionmaker(bind=engine, autocommit=False, autoflush=False)
)

Base = declarative_base()

from .models import Calls, Issues, Addresses, Categories
