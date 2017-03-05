from __future__ import absolute_import, print_function, unicode_literals

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, \
    Boolean, Table
from sqlalchemy.orm import relationship, backref, synonym
from .database import Base, db_session
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

call_category_table = Table('calls_categories', Base.metadata,
    Column('call_id', Integer, ForeignKey('calls.id')),
    Column('category_id', Integer, ForeignKey('categories.id'))
)

issue_category_table = Table('categories_issues', Base.metadata,
    Column('issue_id', Integer, ForeignKey('issues.id')),
    Column('category_id', Integer, ForeignKey('categories.id'))
)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, nullable=False, unique=True)
    role = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    phone_number = Column(String)
    password = Column('encrypted_password', String, nullable=False)

    def __repr__(self):
        return '<User {}>'.format(self.email)

    @classmethod
    def get_by_email(cls, email):
        return db_session.query(cls).filter(cls.email == email).first()

    @classmethod
    def check_password(cls, email, value):
        user = cls.get_by_email(email)
        if not user:
            return False
        return bcrypt.check_password_hash(user.password, value)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id


class Calls(Base):
    __tablename__ = 'calls'
    id = Column(Integer, primary_key=True)
    created_at = Column('datetime_edit', DateTime)
    updated_at = Column(DateTime)
    address_id = Column(Integer, ForeignKey('addresses.id'))
    categories = relationship('Categories',
                              secondary=call_category_table,
                              backref='calls')


class Issues(Base):
    __tablename__ = 'issues'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    address_id = Column(Integer, ForeignKey('addresses.id'))
    title = Column(String)
    message = Column(String)
    categories = relationship('Categories',
                              secondary=issue_category_table,
                              backref='issues')


class Addresses(Base):
    __tablename__ = 'addresses'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    street = Column(String)
    city = Column(String)
    state = Column(String)
    zip = Column(String)
    lat = Column(Float)
    lon = Column(Float)
    unit_number = Column(String)


class Categories(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
