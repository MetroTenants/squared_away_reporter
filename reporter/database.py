from __future__ import absolute_import, print_function, unicode_literals

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session


engine = create_engine('postgres://{un}:{pw}@{host}:{port}/{db}'.format(
        un=os.getenv('DB_USER'),
        pw=os.getenv('DB_PASS'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        db=os.getenv('DB_NAME')
    ), convert_unicode=True, server_side_cursors=True)

db_session = scoped_session(
    sessionmaker(bind=engine, autocommit=False, autoflush=False)
)

Base = declarative_base()

from .models import Calls, Issues, Addresses, Categories
