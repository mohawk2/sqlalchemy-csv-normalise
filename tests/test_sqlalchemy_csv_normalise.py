"""Tests for `sqlalchemy_csv_normalise` package."""

import pytest
from sqlalchemy import (
    create_engine,
    Column, ForeignKey,
    Integer, String, Boolean,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy_csv_normalise import (
    denormalise_prepare,
    renormalise_prepare,
    empty_deleter,
    type_coercer,
)

_db_uri = 'sqlite:///:memory:'
engine = create_engine(_db_uri)
Session = sessionmaker(bind=engine)
Base = declarative_base(engine)

lookup_rows = [
    { 'description': 'admin' },
    { 'description': 'user' },
]
lookup_nonk_rows = [
    { 'description': 'one' },
    { 'description': 'two' },
]
csv_rows_delete_in = [
    { 'username': 'noname', 'name': '', 'accounttype': 'user', 'age': '33', 'valid': 'False', 'nonk_id': 1 },
]
csv_rows_delete_expect = [
    { 'username': 'noname', 'accounttype': 'user', 'age': '33', 'valid': 'False', 'nonk_id': 1 },
]
csv_rows_coerce_in = [
    { 'username': 'bob', 'name': 'Big Bob', 'accounttype_id': '1', 'age': '31', 'valid': 'True' },
    { 'username': 'joe', 'name': 'Regular Joe', 'accounttype_id': '2', 'age': '32', 'valid': 'False' },
]
csv_rows_coerce_expect = [
    { 'username': 'bob', 'name': 'Big Bob', 'accounttype_id': '1', 'age': '31', 'valid': True },
    { 'username': 'joe', 'name': 'Regular Joe', 'accounttype_id': '2', 'age': '32', 'valid': False },
]
csv_rows_make_in = [
    { 'username': 'bob', 'name': 'Big Bob', 'accounttype': 'admin', 'age': '31', 'valid': 'True' },
    { 'username': 'joe', 'name': 'Regular Joe', 'accounttype': 'user', 'age': '32', 'valid': 'False' },
]
csv_rows_make_expect = [
    { 'username': 'bob', 'name': 'Big Bob', 'accounttype_id': 1, 'age': '31', 'valid': 'True' },
    { 'username': 'joe', 'name': 'Regular Joe', 'accounttype_id': 2, 'age': '32', 'valid': 'False' },
]
csv_rows_extract_in = [
    { 'username': 'bob', 'name': 'Big Bob', 'accounttype_id': 1, 'age': 31, 'valid': True, 'nonk_id': 1 },
    { 'username': 'joe', 'name': 'Regular Joe', 'accounttype_id': 2, 'age': 32, 'valid': False, 'nonk_id': 2 },
    { 'username': 'noname', 'name': '', 'accounttype_id': 2, 'age': 33, 'valid': False, 'nonk_id': 1 },
]
csv_rows_extract_expect = [
    { 'username': 'bob', 'name': 'Big Bob', 'accounttype': 'admin', 'age': 31, 'valid': True, 'nonk_id': 1 },
    { 'username': 'joe', 'name': 'Regular Joe', 'accounttype': 'user', 'age': 32, 'valid': False, 'nonk_id': 2 },
    { 'username': 'noname', 'name': '', 'accounttype': 'user', 'age': 33, 'valid': False, 'nonk_id': 1 },
]

class LookupNoNKTable(Base):
    __tablename__ = 'lookup_nonk_table'
    id = Column(Integer, primary_key=True)
    description = Column(String, nullable=False)

class LookupTable(Base):
    __tablename__ = 'lookup_table'
    id = Column(Integer, primary_key=True) # surrogate
    description = Column(String, unique=True, nullable=False) # natural

class NormalisedTable(Base):
    __tablename__ = 'normalised_table'
    id = Column(Integer, primary_key=True) # surrogate
    username = Column(String, unique=True, nullable=False) # natural
    name = Column(String, nullable=True) # nullable
    accounttype_id = Column(Integer, ForeignKey(LookupTable.id), nullable=False)
    age = Column(Integer, nullable=False)
    valid = Column(Boolean, nullable=False)
    nonk_id = Column(Integer, ForeignKey(LookupNoNKTable.id), nullable=True)

@pytest.fixture
def db_session():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = Session()
    for r in lookup_rows:
        session.add(LookupTable(**r))
    for r in lookup_nonk_rows:
        session.add(LookupNoNKTable(**r))
    session.commit()
    return session

def test_empty_deleter():
    f = empty_deleter(NormalisedTable)
    for input, expected in zip(csv_rows_delete_in, csv_rows_delete_expect):
        assert f(input) == expected

def test_type_coercer():
    f = type_coercer(NormalisedTable)
    for input, expected in zip(csv_rows_coerce_in, csv_rows_coerce_expect):
        assert f(input) == expected

def test_renormalise_prepare(db_session):
    f = renormalise_prepare(db_session, NormalisedTable)
    for input, expected in zip(csv_rows_make_in, csv_rows_make_expect):
        assert f(input) == expected

def test_denormalise_prepare(db_session):
    for r in csv_rows_extract_in:
        db_session.add(NormalisedTable(**r))
    db_session.commit()
    q, col_names = denormalise_prepare(db_session, NormalisedTable)
    for got, expected in zip(
        [ dict(zip(col_names, r)) for r in q.all() ],
        csv_rows_extract_expect,
    ):
        assert got == expected

def test_denormalise_prepare_nonk(db_session):
    q, col_names = denormalise_prepare(db_session, LookupNoNKTable)
    for got, expected in zip(
        [ dict(zip(col_names, r)) for r in q.all() ],
        [ { **r, 'id': id } for id, r in enumerate(lookup_nonk_rows, 1) ],
    ):
        assert got == expected
