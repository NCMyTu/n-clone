from __future__ import annotations
import logging
from typing import List, Optional

from .database_status import DatabaseStatus
from .logger import DatabaseLogger
from .models import Artist, Base, Character, Doujinshi, Group, Language, Parody, Tag, Page, many_to_many_tables
from .models.many_to_many_tables import (
	doujinshi_language as d_language, doujinshi_circle as d_circle, doujinshi_artist as d_artist,
	doujinshi_tag as d_tag, doujinshi_character as d_character, doujinshi_parody as d_parody
)
from .utils import validate_doujinshi
from sqlalchemy import create_engine, event, select, func
from sqlalchemy import Integer, Text, DateTime
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, validates, selectinload, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from types import SimpleNamespace
import pathlib
from sqlalchemy.pool import StaticPool


class DatabaseManager:
	def __init__(self, url, echo=False, log_path="database.log", test=False):
		if test:
			self.engine = create_engine(
			url,
			echo=echo,
			connect_args={"check_same_thread": False},
			poolclass=StaticPool,
		)
		else:
			self.engine = create_engine(url, echo=echo)
		self._session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
		self.logger = DatabaseLogger(name="DatabaseManager", log_path=log_path)


	def create_database(self):
		Base.metadata.create_all(self.engine)
		self.insert_language("english")
		self.insert_language("japanese")
		self.insert_language("textless")
		self.insert_language("chinese")
		return DatabaseStatus.OK


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
				self.logger.item_duplicate(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE, model, value)
				return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e)
				return DatabaseStatus.FATAL
			else:
				self.logger.item_inserted(DatabaseStatus.OK, model, value)
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

		for name in item_names:
			model = existing_models.get(name)

			if model:
				self.logger.item_duplicate(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE, model, name)
			else:
				model = Model(name=name)
				session.add(model)
				self.logger.item_inserted(DatabaseStatus.OK, model, name)

			getattr(doujinshi_model, relation_name).append(model)
			self.logger.doujinshi_item_linked(DatabaseStatus.OK, model, name, doujinshi_model.id)


	def insert_doujinshi(self, doujinshi, user_prompt=True):
		try:
			if not validate_doujinshi(doujinshi, user_prompt=user_prompt):
				self.logger.validation_failed(DatabaseStatus.NON_FATAL_VALIDATION_FAILED)
				return DatabaseStatus.NON_FATAL_VALIDATION_FAILED
		except Exception as e:
			self.logger.exception(DatabaseStatus.FATAL, e)
			return DatabaseStatus.FATAL

		data = SimpleNamespace(**doujinshi)

		with self.session() as session:
			statement = select(Doujinshi.id).where(Doujinshi.id == data.id)
			if session.scalar(statement):
				self.logger.item_duplicate(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE, Doujinshi, data.id, 2)
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
				# validate_doujinshi() should catch duplicate filename
				for i, filename in enumerate(data.pages, start=1):
					d.pages.append(Page(filename=filename, order_number=i))

				session.commit()
			except IntegrityError as e:
				if "path" in str(e):
					self.logger.path_duplicate(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE, 2)
					return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
				self.logger.item_duplicate(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE, Doujinshi, data.id, 2)
				return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e, 2)
				return DatabaseStatus.FATAL
			else:
				self.logger.item_inserted(DatabaseStatus.OK, Doujinshi, data.id, 2)
				return DatabaseStatus.OK


	def _add_item_to_doujinshi(self, doujinshi_id, model, relation_name, value):
		"""
		Helper function for adding a single item (e.g., parody, character) to a Doujinshi.
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
				self.logger.item_not_found(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, Doujinshi, doujinshi_id)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			statement = select(model).where(model.name == value)
			model_to_add = session.scalar(statement)
			if not model_to_add:
				self.logger.item_not_found(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, model, value)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			try:
				getattr(doujinshi, relation_name).append(model_to_add)
				session.commit()
			except IntegrityError as e:
				self.logger.doujinshi_item_duplicate(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE, model, value, doujinshi_id)
				return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e)
				return DatabaseStatus.FATAL
			else:
				self.logger.item_added_to_doujinshi(DatabaseStatus.OK, model, value, doujinshi_id)
				return DatabaseStatus.OK


	def _set_pages_to_doujinshi(self, doujinshi_id, pages=None):
		# IMPORTANT: this does 2 things:
			# remove old pages
			# then, add new ones.
		with self.session() as session:
			statement = select(Doujinshi).where(Doujinshi.id == doujinshi_id)
			doujinshi = session.scalar(statement)
			if not doujinshi:
				self.logger.item_not_found(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, Doujinshi, doujinshi_id)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			try:
				# Remove old pages
				doujinshi.pages.clear()

				if not pages:
					# Analogous to remove
					session.commit()
					msg = f"[doujinshi] #{doujinshi_id} has had all pages removed."
					self.logger.success(DatabaseStatus.OK, msg)
					return DatabaseStatus.OK

				session.commit()

				# Add new pages with correct order
				for i, filename in enumerate(pages, start=1):
					doujinshi.pages.append(Page(filename=filename, order_number=i))

				session.commit()
			except IntegrityError as e:
				self.logger.page_duplicate(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE)
				print(e)
				return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e)
				return DatabaseStatus.FATAL
			else:
				self.logger.page_inserted(DatabaseStatus.OK, doujinshi_id)
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
				self.logger.item_not_found(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, Doujinshi, doujinshi_id)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			statement = select(model).where(model.name == value)
			model_to_remove = session.scalar(statement)
			if not model_to_remove:
				self.logger.item_not_found(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, model, value)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			try:
				model_list = getattr(doujinshi, relation_name)

				if model_to_remove not in model_list:
					return_status = DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND
					self.logger.item_not_in_doujinshi(return_status, model, value, doujinshi_id)
					return return_status

				model_list.remove(model_to_remove)
				session.commit()
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e)
				return DatabaseStatus.FATAL
			else:
				self.logger.item_removed_from_doujinshi(DatabaseStatus.OK, model, value, doujinshi_id)
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
	def remove_all_pages_from_doujinshi(self, doujinshi_id):
		return self._set_pages_to_doujinshi(doujinshi_id, None)


	def remove_doujinshi(self, doujinshi_id):
		with self.session() as session:
			statement = select(Doujinshi).where(Doujinshi.id == doujinshi_id)
			doujinshi = session.scalar(statement)
			if not doujinshi:
				self.logger.item_not_found(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, Doujinshi, doujinshi_id, 2)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			try:
				session.delete(doujinshi)
				session.commit()
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e, 2)
				return DatabaseStatus.FATAL
			else:
				self.logger.doujinshi_removed(DatabaseStatus.OK, doujinshi_id, 2)
				return DatabaseStatus.OK


	def _update_column_of_doujinshi(self, doujinshi_id, column_name, value):
		with self.session() as session:
			statement = select(Doujinshi).where(Doujinshi.id == doujinshi_id)
			doujinshi = session.scalar(statement)
			if not doujinshi:
				self.logger.item_not_found(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, Doujinshi, doujinshi_id)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			try:
				setattr(doujinshi, column_name, value)
				session.commit()
			except IntegrityError as e:
				# Only "path" column can trigger this
				self.logger.path_duplicate(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE)
				return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e)
				return DatabaseStatus.FATAL
			else:
				self.logger.column_updated(DatabaseStatus.OK, column_name, value, doujinshi_id)
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


	def _get_count_by_name(self, model, many_to_many_table, col_to_join, values, session=None):
		if not values:
			return DatabaseStatus.OK, {}

		statement = (
			select(model.name, func.count("*"))
			.select_from(many_to_many_table)
			.join(model, model.id == col_to_join)
			.where(model.name.in_(values))
			.group_by(model.name)
		)

		try:
			if session:
				count_dict = dict(session.execute(statement).all())
			else:
				with self.session() as session_in:
					count_dict = dict(session_in.execute(statement).all())
			return DatabaseStatus.OK, {name: count_dict.get(name, 0) for name in values}
		except Exception as e:
			self.logger.exception(DatabaseStatus.FATAL, e)
			return DatabaseStatus.FATAL, {}


	def get_count_of_parodies(self, values):
		return self._get_count_by_name(Parody, d_parody, d_parody.c.parody_id, values)
	def get_count_of_characters(self, values):
		return self._get_count_by_name(Character, d_character, d_character.c.character_id,values)
	def get_count_of_tags(self, values):
		return self._get_count_by_name(Tag, d_tag, d_tag.c.tag_id,values)
	def get_count_of_artists(self, values):
		return self._get_count_by_name(Artist, d_artist, d_artist.c.artist_id, values)
	def get_count_of_groups(self, values):
		return self._get_count_by_name(Group, d_circle, d_circle.c.circle_id, values)
	def get_count_of_languages(self, values):
		return self._get_count_by_name(Language, d_language, d_language.c.language_id, values)


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
			doujinshi = session.scalar(statement)

			if not doujinshi:
				self.logger.item_not_found(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, Doujinshi, doujinshi_id, 2)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, None

			djs_dict = {
				"id": doujinshi.id,
				"full_name": doujinshi.full_name,
				"full_name_original": doujinshi.full_name_original,
				"pretty_name": doujinshi.pretty_name,
				"pretty_name_original": doujinshi.pretty_name_original,
				"path": doujinshi.path,
				"note": doujinshi.note
			}
			djs_dict["pages"] = [p.filename for p in doujinshi.pages]

			count = self._get_count_by_name
			_, djs_dict["parodies"] = count(Parody, d_parody, d_parody.c.parody_id,
				[p.name for p in doujinshi.parodies], session
			)
			_, djs_dict["characters"] = count(Character, d_character, d_character.c.character_id,
				[c.name for c in doujinshi.characters], session
			)
			_, djs_dict["tags"] = count(Tag, d_tag, d_tag.c.tag_id,
				[t.name for t in doujinshi.tags], session
			)
			_, djs_dict["artists"] = count(Artist, d_artist, d_artist.c.artist_id,
				[a.name for a in doujinshi.artists], session
			)
			_, djs_dict["groups"] = count(Group, d_circle, d_circle.c.circle_id,
				[g.name for g in doujinshi.groups], session
			)
			_, djs_dict["languages"] = count(Language, d_language, d_language.c.language_id,
				[l.name for l in doujinshi.languages], session
			)

			return DatabaseStatus.OK, djs_dict


# def get_doujinshi_in_batch(self, batch_size, offset, partial=False):