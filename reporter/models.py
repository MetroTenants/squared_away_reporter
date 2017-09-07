from __future__ import absolute_import, print_function, unicode_literals

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, \
    Boolean, Text, Table
from sqlalchemy.orm import relationship, backref, synonym, aliased
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
    management_company = Column(String)
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


class Calls(Base):
    __tablename__ = 'calls'
    id = Column(Integer, primary_key=True)
    created_at = Column('datetime_edit', DateTime)
    updated_at = Column(DateTime)
    address_id = Column(Integer, ForeignKey('addresses.id'))
    address = relationship(Addresses, foreign_keys=address_id)
    categories = relationship('Categories',
                              secondary=call_category_table,
                              backref='calls')
    tenant_id = Column(Integer, ForeignKey('users.id'))
    tenant = relationship('User',
        primaryjoin="Calls.tenant_id==User.id",
        foreign_keys=tenant_id)
    landlord_id = Column(Integer, ForeignKey('users.id'))
    landlord = relationship('User',
        primaryjoin="Calls.landlord_id==User.id",
        foreign_keys=landlord_id)
    rep_id = Column(Integer, ForeignKey('users.id'))
    rep = relationship('User',
        primaryjoin="Calls.rep_id==User.id",
        foreign_keys=rep_id)
    has_lease = Column(Boolean)
    received_lead_notice = Column(Boolean)
    number_of_children_under_six = Column(String)
    number_of_units_in_building = Column(String)
    is_owner_occupied = Column(Boolean)
    is_subsidized = Column(Boolean)
    subsidy_type = Column(String)
    is_rlto = Column(Boolean)
    is_referred_by_info = Column(Boolean)
    is_counseled_in_spanish = Column(Boolean)
    is_referred_to_attorney = Column(Boolean)
    is_referred_to_building_organizer = Column(Boolean)
    referred_to_whom = Column(String)
    notes = Column(Text)
    heard_about_mto_from = Column(String)
    materials_sent = Column(String)
    is_interested_in_membership = Column(Boolean)
    is_interested_in_tenant_congress = Column(Boolean)
    number_of_materials_sent = Column(Integer)
    is_tenant_interested_in_volunteering = Column(Boolean)
    is_referred_to_agency = Column(Boolean)
    is_walkin = Column(Boolean)


class Issues(Base):
    __tablename__ = 'issues'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    address_id = Column(Integer, ForeignKey('addresses.id'))
    address = relationship(Addresses, foreign_keys=address_id)
    tenant_id = Column(Integer, ForeignKey('users.id'))
    tenant = relationship('User',
        primaryjoin="Issues.tenant_id==User.id",
        foreign_keys=tenant_id)
    landlord_id = Column(Integer, ForeignKey('users.id'))
    landlord = relationship('User',
        primaryjoin="Issues.landlord_id==User.id",
        foreign_keys=landlord_id)
    title = Column(Text)
    message = Column(Text)
    categories = relationship('Categories',
                              secondary=issue_category_table,
                              backref='issues')
    closed = Column(DateTime)
    resolved = Column(DateTime)
    area_of_residence = Column(String)
    efforts_to_fix = Column(Text)
    urgency = Column(String)
    entry_availability = Column(Text)
