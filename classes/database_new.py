from __future__ import annotations
import logging
from typing import List, Optional

from .models import Artist, Base, Character, Doujinshi, Group, Language, Parody, Tag
from .logger import DatabaseLogger
from sqlalchemy import create_engine, event, select
from sqlalchemy import Integer, Text, DateTime
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, validates
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


class DatabaseManager:
	def __init__(self, url, echo=False, log_path="database.log"):
		self.engine = create_engine(url, echo=echo)
		self._session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
		self.logger = DatabaseLogger(name=__name__, log_path=log_path)
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
		# print("foreign_keys is ON.")



	def handle_verbose(self, orm_object, verbose):
		if verbose:
			log.debug(f"Inserted into table [{orm_object.__tablename__}] new value: {orm_object.name}")


	def _insert_generic(self, model, value, verbose=True):
		"""
		Insert a new parody, character, tag, artist, group, or language by name.

		Returns:
			Tuple[bool, Union[ORM object, str]]:
				- On success: (True, new_obj)
				- On failure: (False, error_type)
		"""
		with self.session() as session:
			try:
				new_obj = model(name=value)
				session.add(new_obj)
				session.commit()
			except IntegrityError as e:
				self.logger.log_insert(is_success=False, model=model, value=value, exception=e)
				return False
			except Exception as e:
				self.logger.log_insert(is_success=False, model=model, value=value, exception=e)
				return False
			else:
				self.logger.log_insert(is_success=True, model=model, value=value)
				return True


	def insert_parody(self, value, verbose=True):
		return self._insert_generic(Parody, value, verbose=verbose)


	def insert_character(self, value, verbose=True):
		pass


	# def insert_character(self, character):
	# def insert_tag(self, tag):
	# def insert_artist(self, artist):
	# def insert_group(self, group):
	# def insert_language(self, language):