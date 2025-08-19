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


	def _remove_item_from_doujinshi(self, doujinshi_id, model, relation_name, value):
		with self.session() as session:
			statement = select(Doujinshi).where(Doujinshi.id == doujinshi_id)
			doujinshi = session.scalar(statement)
			if not doujinshi:
				return_status = DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND
				self.logger.log_remove_item_from_doujinshi(return_status, Doujinshi, value, doujinshi_id)
				return return_status

			statement = select(model).where(model.name == value)
			model_to_remove = session.scalar(statement)
			if not model_to_remove:
				self.logger.log_remove_item_from_doujinshi(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, model, value)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			try:
				model_list = getattr(doujinshi, relation_name)

				if model_to_remove not in model_list:
					self.logger.log_remove_item_from_doujinshi(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, model, value, doujinshi_id)
					return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

				model_list.remove(model_to_remove)
				session.commit()
			except Exception as e:
				self.logger.log_remove_item_from_doujinshi(DatabaseStatus.FATAL, model, value, doujinshi_id, e)
				return DatabaseStatus.FATAL
			else:
				self.logger.log_remove_item_from_doujinshi(DatabaseStatus.OK, model, value, doujinshi_id)
				return DatabaseStatus.OK


	def remove_parody_from_doujinshi(self, doujinshi_id, value):
		return self._remove_item_from_doujinshi(doujinshi_id, Parody, "parodies", value)
	def remove_character_from_doujinshi(self, doujinshi_id, value):
		return self._remove_item_from_doujinshi(doujinshi_id, Character, "characters", value)
	def remove_tag_from_doujinshi(self, doujinshi_id, value):
		return self._remove_item_from_doujinshi(doujinshi_id, Tag, "tags", value)
	def remove_artist_from_doujinshi(self, doujinshi_id, value):
		return self._remove_item_from_doujinshi(doujinshi_id, Artist, "artists", value)
	def remove_group_from_doujinshi(self, doujinshi_id, value):
		return self._remove_item_from_doujinshi(doujinshi_id, Group, "groups", value)
	def remove_language_from_doujinshi(self, doujinshi_id, value):
		return self._remove_item_from_doujinshi(doujinshi_id, Language, "languages", value)


# def remove_all_pages_from_doujinshi(self, doujinshi_id):
# def remove_doujinshi(self, doujinshi_id):


# def execute_raw_sql(self, query, params)
# def add_pages_to_doujinshi(self, doujinshi_id, page_order_list):
# def get_doujinshi(self, doujinshi_id, partial=False):
# def get_doujinshi_in_batch(self, batch_size, offset, partial=False):
# def update_full_name_of_doujinshi(self, doujinshi_id, value):
# def update_full_name_original_of_doujinshi(self, doujinshi_id, value):
# def update_bold_name_of_doujinshi(self, doujinshi_id, value):
# def update_bold_name_original_of_doujinshi(self, doujinshi_id, value):
# def update_note_of_doujinshi(self, doujinshi_id, value):
# def update_path_of_doujinshi(self, doujinshi_id, value):
# def get_count_of_parodies(self, doujinshi_id, values):
# def get_count_of_characters(self, doujinshi_id, values):
# def get_count_of_tags(self, doujinshi_id, values):
# def get_count_of_artists(self, doujinshi_id, values):
# def get_count_of_groups(self, doujinshi_id, values):
# def get_count_of_languages(self, doujinshi_id, values):