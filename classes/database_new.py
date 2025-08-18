# TODO: implement def execute_raw_sql(self, query, params)
from __future__ import annotations
import logging
from typing import List, Optional

from .database_status import DatabaseStatus
from .logger import DatabaseLogger
from .models import Artist, Base, Character, Doujinshi, Group, Language, Parody, Tag
from sqlalchemy import create_engine, event, select
from sqlalchemy import Integer, Text, DateTime
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, validates, selectinload, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


class DatabaseManager:
	def __init__(self, url, echo=False, log_path="database.log"):
		self.engine = create_engine(url, echo=echo)
		self._session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
		self.logger = DatabaseLogger(name="DatabaseManager", log_path=log_path)
		

	def create_database(self):
		Base.metadata.create_all(self.engine)
		self.insert_language("english")
		self.insert_language("japanese")
		self.insert_language("chinese")
		self.insert_language("textless")


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


	def get_doujinshi(self, doujinshi_id):
		# TODO: measure performance of joinedload and selectinload
		#       log
		with self.session() as session:
			statement = (
				select(Doujinshi)
				.options(
					selectinload(Doujinshi.parodies),
					selectinload(Doujinshi.characters),
					selectinload(Doujinshi.tags),
					selectinload(Doujinshi.artists),
					selectinload(Doujinshi.groups),
					selectinload(Doujinshi.languages),
				)
				.where(Doujinshi.id == doujinshi_id)
			)
			# print(f"---------------\n{statement}\n---------------")
			doujinshi = session.scalar(statement)

			if not doujinshi:
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			return doujinshi


	def insert_doujinshi(self, doujinshi_id, full_name, path):
		# TODO: use self.logger
		with self.session() as session:
			try:
				d = Doujinshi(id=doujinshi_id, full_name=full_name, path=path)
				session.add(d)
				session.commit()
			except IntegrityError as e:
				self.logger.logger.info(f"[doujinshi] #{doujinshi_id} already existed.")
				return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
			except Exception as e:
				# self.logger.logger.error(f"{doujinshi_id} already existed.")
				return DatabaseStatus.FATAL
			else:
				self.logger.logger.info(f"{doujinshi_id} inserted.")
				return DatabaseStatus.OK


	def _insert_item(self, model, value):
		"""
		Insert a new parody, character, tag, artist, group, or language by name.

		Returns:
			- On success: DatabaseStatus.OK
			- On failure: DatabaseStatus.NON_FATAL_ITEM_DUPLICATE or DatabaseStatus.FATAL
		"""
		with self.session() as session:
			try:
				new_item = model(name=value)
				session.add(new_item)
				session.commit()
			except IntegrityError as e:
				self.logger.log_insert_item(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE, model, value, e)
				return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
			except Exception as e:
				self.logger.log_insert_item(DatabaseStatus.FATAL, model, value, e)
				return DatabaseStatus.FATAL
			else:
				self.logger.log_insert_item(DatabaseStatus.OK, model, value)
				return DatabaseStatus.OK


	def insert_parody(self, value):
		return self._insert_item(Parody, value)
	def insert_character(self, value):
		return self._insert_item(Character, value)
	def insert_tag(self, value):
		return self._insert_item(Tag, value)
	def insert_artist(self, value):
		return self._insert_item(Artist, value)
	def insert_group(self, value):
		return self._insert_item(Group, value)
	def insert_language(self, value):
		return self._insert_item(Language, value)


	def _add_item_to_doujinshi(self, doujinshi_id, model, relation_name, value):
		with self.session() as session:
			statement = select(Doujinshi).where(Doujinshi.id == doujinshi_id)
			doujinshi = session.scalar(statement)
			if not doujinshi:
				return_status = DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND
				self.logger.log_add_item_to_doujinshi(return_status, Doujinshi, value, doujinshi_id)
				return return_status

			statement = select(model).where(model.name == value)
			model_to_add = session.scalar(statement)
			if not model_to_add:
				self.logger.log_add_item_to_doujinshi(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, model, value)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			try:
				getattr(doujinshi, relation_name).append(model_to_add)
				session.commit()
			except IntegrityError as e:
				self.logger.log_add_item_to_doujinshi(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE, model, value, doujinshi_id)
				return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
			except Exception as e:
				self.logger.log_add_item_to_doujinshi(DatabaseStatus.FATAL, model, value, doujinshi_id, e)
				return DatabaseStatus.FATAL
			else:
				self.logger.log_add_item_to_doujinshi(DatabaseStatus.OK, model, value, doujinshi_id)
				return DatabaseStatus.OK


	def add_parody_to_doujinshi(self, doujinshi_id, value):
		return self._add_item_to_doujinshi(doujinshi_id, Parody, "parodies", value)
	def add_character_to_doujinshi(self, doujinshi_id, value):
		return self._add_item_to_doujinshi(doujinshi_id, Character, "characters", value)
	def add_tag_to_doujinshi(self, doujinshi_id, value):
		return self._add_item_to_doujinshi(doujinshi_id, Tag, "tags", value)
	def add_artist_to_doujinshi(self, doujinshi_id, value):
		return self._add_item_to_doujinshi(doujinshi_id, Artist, "artists", value)
	def add_group_to_doujinshi(self, doujinshi_id, value):
		return self._add_item_to_doujinshi(doujinshi_id, Group, "groups", value)
	def add_language_to_doujinshi(self, doujinshi_id, value):
		return self._add_item_to_doujinshi(doujinshi_id, Language, "languages", value)