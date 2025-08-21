from __future__ import annotations
import logging
from typing import List, Optional

from .database_status import DatabaseStatus
from .logger import DatabaseLogger
from .models import Artist, Base, Character, Doujinshi, Group, Language, Parody, Tag, Page
from .utils import validate_doujinshi
from sqlalchemy import create_engine, event, select
from sqlalchemy import Integer, Text, DateTime
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, validates, selectinload, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from types import SimpleNamespace
import pathlib


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
					selectinload(Doujinshi.pages)
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
		Helper function for inserting an item (e.g., parody, character) into the database.
		Use insert_doujinshi, insert_character, etc. instead.

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


	def _add_and_link_item(self, session, doujinshi_model, relation_name, Model, item_names):
		existing_models = {
			model.name: model for model in session.scalars(
				select(Model).where(Model.name.in_(item_names))
		)}

		tbl_name = Model.__tablename__
		for name in item_names:
			model = existing_models.get(name)

			if model:
				print(f"[{tbl_name}] already has value: {name!r}")
			else:
				model = Model(name=name)
				session.add(model)
				print(f"[{tbl_name}] created: {name!r}")

			getattr(doujinshi_model, relation_name).append(model)
			print(f"Linked [{tbl_name}] {name!r} <---> [doujinshi] #{doujinshi_model.id}")


	def insert_doujinshi(self, doujinshi, user_prompt=True):
		# TODO: use self.logger
		# doujinshi: a dict. refer to src/utils/create_empty_doujinshi
		print("INFO | DatabaseManager | func: insert_doujinshi")
		if not validate_doujinshi(doujinshi, user_prompt=user_prompt):
			print("validation failed. insertion skip.")
			return DatabaseStatus.NON_FATAL_VALIDATION_FAILED

		data = SimpleNamespace(**doujinshi)

		with self.session() as session:
			statement = select(Doujinshi.id).where(Doujinshi.id == data.id)
			if session.scalar(statement):
				print("DOUJINSHI ALREADY EXISTS")
				return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE

			try:
				d = Doujinshi(
					id=data.id,
					full_name=data.full_name, full_name_original=data.full_name_original,
					pretty_name=data.pretty_name, pretty_name_original=data.pretty_name_original,
					note=data.note,
					path=data.path,
				)
				session.add(d)

				relations = [
					("parodies", Parody, data.parodies),
					("characters", Character, data.characters),
					("tags", Tag, data.tags),
					("artists", Artist, data.artists),
					("groups", Group, data.groups),
					("languages", Language, data.languages),
				]
				for rel_name, Model, values in relations:
					self._add_and_link_item(session, d, rel_name, Model, values)

				# Add pages
				for i, filename in enumerate(data.pages, start=1):
					d.pages.append(Page(filename=filename, order_number=i))

				session.commit()
			except IntegrityError as e:
				self.logger.logger.info(f"[doujinshi] #{d.id} already exists. {e}")
				return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
			except Exception as e:
				self.logger.logger.info(f"insert_doujinshi UNEXPECTED EXCEPTION {e}")
				return DatabaseStatus.FATAL
			else:
				self.logger.logger.info(f"{d.id} inserted.")
				return DatabaseStatus.OK


	def _add_item_to_doujinshi(self, doujinshi_id, model, relation_name, value):
		"""
		Helper function for adding an item (e.g., parody, character) to a Doujinshi.
		Use add_parody_to_doujinshi, add_character_to_doujinshi, etc. instead.

		Returns:
			- On success: DatabaseStatus.OK
			- On failure: DatabaseStatus.NON_FATAL_ITEM_DUPLICATE,
				DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND or DatabaseStatus.FATAL
		"""
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


	def _set_pages_to_doujinshi(self, doujinshi_id, pages=None):
		# IMPORTANT: this does 2 things:
			# remove old pages
			# then, add new ones.
		with self.session() as session:
			statement = select(Doujinshi).where(Doujinshi.id == doujinshi_id)
			doujinshi = session.scalar(statement)
			if not doujinshi:
				self.logger.log_add_remove_pages(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, doujinshi_id)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			try:
				# Remove old pages.
				doujinshi.pages.clear()

				if not pages:
					# analogous to remove
					session.commit()
					self.logger.log_add_remove_pages(DatabaseStatus.OK, doujinshi_id, mode="remove")
					return DatabaseStatus.OK

				# 2. Add new pages with correct order
				for i, filename in enumerate(pages, start=1):
					doujinshi.pages.append(Page(filename=filename, order_number=i))

				session.commit()
			except IntegrityError as e:
				self.logger.log_add_remove_pages(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE, doujinshi_id)
				return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
			except Exception as e:
				self.logger.log_add_remove_pages(DatabaseStatus.FATAL, doujinshi_id, exception=e)
				return DatabaseStatus.FATAL
			else:
				self.logger.log_add_remove_pages(DatabaseStatus.OK, doujinshi_id, mode="add")
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
	def add_pages_to_doujinshi(self, doujinshi_id, pages):
		return self._set_pages_to_doujinshi(doujinshi_id, pages)


	def _remove_item_from_doujinshi(self, doujinshi_id, model, relation_name, value):
		"""
		Helper function for removing an item (e.g., parody, character) from a Doujinshi.
		Use remove_parody_from_doujinshi, remove_character_from_doujinshi, etc. instead.

		Returns:
			- On success: DatabaseStatus.OK
			- On failure: DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND or DatabaseStatus.FATAL
		"""
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
	def remove_pages_from_doujinshi(self, doujinshi_id):
		return self._set_pages_to_doujinshi(doujinshi_id, None)


	def remove_doujinshi(self, doujinshi_id):
		with self.session() as session:
			statement = select(Doujinshi).where(Doujinshi.id == doujinshi_id)
			doujinshi = session.scalar(statement)

			if not doujinshi:
				self.logger.log_remove_doujinshi(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, doujinshi_id)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			try:
				session.delete(doujinshi)
				session.commit()
			except Exception as e:
				self.logger.log_remove_doujinshi(DatabaseStatus.FATAL, doujinshi_id, exception=e)
				return DatabaseStatus.FATAL
			else:
				self.logger.log_remove_doujinshi(DatabaseStatus.OK, doujinshi_id)
				return DatabaseStatus.OK


	def _update_column_of_doujinshi(self, doujinshi_id, column_name, value):
		with self.session() as session:
			statement = select(Doujinshi).where(Doujinshi.id == doujinshi_id)
			doujinshi = session.scalar(statement)

			if not doujinshi:
				self.logger.log_update_column(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, column_name, value, doujinshi_id)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			try:
				setattr(doujinshi, column_name, value)
				session.commit()
			except IntegrityError as e:
				self.logger.log_update_column(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE, column_name, value, doujinshi_id, exception=e)
				return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
			except Exception as e:
				self.logger.log_update_column(DatabaseStatus.FATAL, column_name, value, doujinshi_id, exception=e)
				return DatabaseStatus.FATAL
			else:
				self.logger.log_update_column(DatabaseStatus.OK, column_name, value, doujinshi_id)
				return DatabaseStatus.OK
	

	def update_full_name_of_doujinshi(self, doujinshi_id, value):
		return self._update_column_of_doujinshi(doujinshi_id, "full_name", value)
	def update_full_name_original_of_doujinshi(self, doujinshi_id, value):
		return self._update_column_of_doujinshi(doujinshi_id, "full_name_original", value)
	def update_pretty_name_of_doujinshi(self, doujinshi_id, value):
		return self._update_column_of_doujinshi(doujinshi_id, "pretty_name", value)
	def update_pretty_name_original_of_doujinshi(self, doujinshi_id, value):
		return self._update_column_of_doujinshi(doujinshi_id, "pretty_name_original", value)
	def update_note_of_doujinshi(self, doujinshi_id, value):
		return self._update_column_of_doujinshi(doujinshi_id, "note", value)
	def update_path_of_doujinshi(self, doujinshi_id, value):
		return self._update_column_of_doujinshi(doujinshi_id, "path", pathlib.Path(value).as_posix())


# def execute_raw_sql(self, query, params)
# def get_doujinshi_in_batch(self, batch_size, offset, partial=False):
# def get_count_of_parodies(self, values):
# def get_count_of_characters(self, values):
# def get_count_of_tags(self, values):
# def get_count_of_artists(self, values):
# def get_count_of_groups(self, values):
# def get_count_of_languages(self, values):