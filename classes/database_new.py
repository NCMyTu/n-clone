from __future__ import annotations
from typing import List, Optional


from .models import Artist, Base, Character, Doujinshi, Group, Language, Parody, Tag
from sqlalchemy import create_engine, event, select
from sqlalchemy import Integer, Text, DateTime
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, validates


class DatabaseManager:
	def __init__(self, url, echo=True):
		self.engine = create_engine(url, echo=echo)
		self._session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
		Base.metadata.create_all(self.engine)


	def session(self):
		return self._session()


	@event.listens_for(Engine, "connect")
	def set_sqlite_pragma(dbapi_connection, connection_record):
		# the sqlite3 driver will not set PRAGMA foreign_keys
		# if autocommit=False; set to True temporarily
		ac = dbapi_connection.autocommit
		dbapi_connection.autocommit = True

		cursor = dbapi_connection.cursor()
		cursor.execute("PRAGMA foreign_keys = ON")
		cursor.close()

		# restore previous autocommit setting
		dbapi_connection.autocommit = ac