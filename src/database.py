from __future__ import annotations
import logging
from typing import List, Optional

from .database_status import DatabaseStatus
from .logger import DatabaseLogger
from .models import Artist, Base, Character, Doujinshi, Group, Language, Parody, Tag, Page
from .models.many_to_many_tables import (
	doujinshi_language as d_language, doujinshi_circle as d_circle, doujinshi_artist as d_artist,
	doujinshi_tag as d_tag, doujinshi_character as d_character, doujinshi_parody as d_parody
)
from .utils import validate_doujinshi
from sqlalchemy import create_engine, event, select, func, update, text
from sqlalchemy import Integer, DateTime
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, validates, selectinload, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from types import SimpleNamespace
import pathlib
from sqlalchemy.pool import StaticPool
import math


# Docstring is the same style as sklearn's.
# https://github.com/scikit-learn/scikit-learn/blob/c5497b7f7/sklearn/neural_network/_rbm.py#L274
class DatabaseManager:
	"""Manager for database connections.

	This class provides a high-level interface for interacting with the underlying database.
	It is responsible for creating and managing the SQLAlchemy session,
	executing queries, and handling transactions.

	For usage examples, refer to {UPDATE HERE}.

	Notes
	-----
	  - This class (right now) is specific to SQLite.
	  - Call the `update_count` methods after any update operations, since
	update methods themselves do not refresh the counts.

	Parameters
	----------
	url : str
		The database connection path to establish the connection.

	log_path : str
		Path to the log file where database operations will be logged.

	echo : bool, default=False
		If True, the database engine will emit all SQL statements.

	test : bool, default=False
		If True, initializes the database in testing mode (remember to set `url` to use an in-memory database).
	"""
	def __init__(self, url, log_path, echo=False, test=False):
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
		self.logger = DatabaseLogger(name=self.__class__.__name__, log_path=log_path)


	def session(self):
		"""Return this database's internal session.

		Returns
		-------
		session : sqlalchemy.orm.Session
			The internal session associated with this object.
		"""
		return self._session()


	@event.listens_for(Engine, "connect")
	def set_sqlite_pragma(dbapi_connection, connection_record):
		"""Ensure SQLite enforces foreign key constraints on connect.

		This is specific to SQLite.
		"""
		# NOTE: omit this function from user docs.
		# the sqlite3 driver will not set PRAGMA foreign_keys
		# if autocommit=False; set to True temporarily
		ac = dbapi_connection.autocommit
		dbapi_connection.autocommit = True

		cursor = dbapi_connection.cursor()
		cursor.execute("PRAGMA foreign_keys = ON;")
		# cursor.execute("PRAGMA cache_size = -5000;") # 5MB
		cursor.close()

		# restore previous autocommit setting
		dbapi_connection.autocommit = ac
		# print("foreign_keys is ON.")


	def create_database(self):
		"""Initialize the database schema and insert default values.

		Creates all tables defined in the SQLAlchemy `Base` metadata and
		inserts a set of default languages ("english", "japanese", "textless", "chinese")
		into the database.

		Does nothing if a schema already exists.

		Returns
		-------
		status : DatabaseStatus.OK
			Indicates the database is successfully created.
		"""
		Base.metadata.create_all(self.engine)
		self.insert_language("english")
		self.insert_language("japanese")
		self.insert_language("textless")
		self.insert_language("chinese")
		return DatabaseStatus.OK


	def _idx_components(self):
		"""Return index definitions.

		Each entry is a tuple of (index_name, on_clause) for the many-to-many
		tables.

		WARNING: this is hardcoded, so update if underlying models change.
		"""
		return [
			# (index name, ON clause)
			("idx_doujinshi_parody__parody_doujinshi", "doujinshi_parody(parody_id, doujinshi_id)"),
			("idx_doujinshi_character__character_doujinshi", "doujinshi_character(character_id, doujinshi_id)"),
			("idx_doujinshi_tag__tag_doujinshi", "doujinshi_tag(tag_id, doujinshi_id)"),
			("idx_doujinshi_artist__artist_doujinshi", "doujinshi_artist(artist_id, doujinshi_id)"),
			("idx_doujinshi_circle__circle_doujinshi", "doujinshi_circle(circle_id, doujinshi_id)"),
			("idx_doujinshi_language__language_doujinshi", "doujinshi_language(language_id, doujinshi_id)"),
		]


	def create_index(self):
		"""Create all extra indices listed in `_idx_components`.

		Returns
		-------
		status : DatabaseStatus.OK
			Indicates indices were successfully created.
		"""
		with self.session() as session:
			for idx_name, on_clause in self._idx_components():
				statement = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {on_clause}"
				session.execute(text(statement))
			session.commit()
			return DatabaseStatus.OK


	def drop_index(self):
		"""Drop all extra indices listed in `_idx_components`..

		Returns
		-------
		status : DatabaseStatus.OK
			Indicates indices were successfully dropped.
		"""
		with self.session() as session:
			for idx_name, _ in self._idx_components():
				statement = f"DROP INDEX IF EXISTS {idx_name}"
				session.execute(text(statement))
			session.commit()
			return DatabaseStatus.OK


	def show_index(self):
		"""Print all indices in the database."""
		with self.session() as session:
			results = session.execute(
				text("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index';")
			).all()
			for name, tbl_name, sql in results:
				print(f"Index: {name}, Table: {tbl_name}, SQL: {sql}")


	def vacuum(self):
		"""Execute the SQLite command `VACUUM` to reduce storage size.

		Use this after bulk inserts or creating indices.

		Other databases may have a different command for this operation.
		"""
		with self.session() as session:
			session.execute(text("VACUUM"))


	def _insert_item(self, model, name):
		"""Insert a single item into the database.

		Use public methods whenever possible.

		Parameters
		----------
		model : `Parody`, `Character`, `Tag`, `Artist`, `Group` or `Language`
			Type of the item being inserted.

		name : str
			Name of the item to insert.

		Returns
		-------
		status : DatabaseStatus
			Status of the operation:
				DatabaseStatus.OK - item inserted.
				DatabaseStatus.NON_FATAL_ITEM_DUPLICATE - item already exists.
				DatabaseStatus.FATAL - other errors.
		"""
		with self.session() as session:
			try:
				new_item = model(name=name)
				session.add(new_item)
				session.commit()

				self.logger.item_inserted(DatabaseStatus.OK, model, name)
				return DatabaseStatus.OK
			except IntegrityError as e:
				self.logger.item_duplicate(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE, model, name)
				return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e)
				return DatabaseStatus.FATAL


	def insert_parody(self, name):
		"""Insert a `Parody` into the database."""
		return self._insert_item(Parody, name)
	def insert_character(self, name):
		"""Insert a `Character` into the database."""
		return self._insert_item(Character, name)
	def insert_tag(self, name):
		"""Insert a `Tag` into the database."""
		return self._insert_item(Tag, name)
	def insert_artist(self, name):
		"""Insert an `Artist` into the database."""
		return self._insert_item(Artist, name)
	def insert_group(self, name):
		"""Insert a `Group` into the database."""
		return self._insert_item(Group, name)
	def insert_language(self, name):
		"""Insert a `Language` into the database."""
		return self._insert_item(Language, name)


	def _add_and_link_item(self, session, doujinshi_model, relation_name, Model, item_names):
		"""Insert `items` into the database (if they don't exist) and link them to a `doujinshi`.

		Notes
		-----
		This function does not commit the change, the caller is responsible for this.

		Parameters
		----------
		session : sqlalchemy.orm.Session
			The session handling this function.

		doujinshi_model : Doujinshi
			`doujinshi` to which `items` will be linked.

		relation_name : "parodies", "characters", "tags", "artists", "groups" or "languages"
			Name of the list-like relationship of `doujinshi_model`.

		Model : `Parody`, `Character`, `Tag`, `Artist`, `Group` or `Language`
			Model of the items to add.

		item_names : list of str
			Names of the items to add and link.
		"""
		existing_models = {
			model.name: model for model in session.scalars(
				select(Model).where(Model.name.in_(item_names))
		)}

		for name in item_names:
			model = existing_models.get(name, None)

			if model:
				self.logger.item_duplicate(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE, model, name)
			else:
				model = Model(name=name, count=0)
				session.add(model)
				self.logger.item_inserted(DatabaseStatus.OK, model, name)

			getattr(doujinshi_model, relation_name).append(model)
			model.count += 1
			self.logger.doujinshi_item_linked(DatabaseStatus.OK, model, name, doujinshi_model.id)


	def insert_doujinshi(self, doujinshi, user_prompt=True):
		"""Insert a single doujinshi into the database.

		Perform these actions in order:
		validates the doujinshi,
		checks for doujinshi duplicates,
		adds the items (if they don't exist yet) then
		link them with the doujinshi.

		Parameters
		----------
		doujinshi : dict
			A dictionary containing doujinshi data. Expected fields:
				Single-valued:
					'id', 'path', 'note',
					'full_name', 'full_name_original',
					'pretty_name', 'pretty_name_original',
				List-like:
					'parodies', 'characters', 'tags',
					'artists', 'groups', 'languages',
					'pages'.

		user_prompt : bool, default=True
			Whether to prompt the user during doujinshi validation.
			If False, it will not alert user about empty list-like attributes or warnings.

		Returns
		-------
		status : DatabaseStatus
			Status of the operation:
				DatabaseStatus.OK - insertion succeeded.
				DatabaseStatus.NON_FATAL_VALIDATION_FAILED - validation failed.
				DatabaseStatus.NON_FATAL_ITEM_DUPLICATE - doujinshi (or its path) exists.
				DatabaseStatus.FATAL - other errors.
		"""
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
				# Add bare info
				d = Doujinshi(
					id=data.id,
					full_name=data.full_name, full_name_original=data.full_name_original,
					pretty_name=data.pretty_name, pretty_name_original=data.pretty_name_original,
					note=data.note,
					path=data.path,
				)
				session.add(d)

				# Add and link item types
				relations = [
					("parodies", Parody, data.parodies),
					("characters", Character, data.characters),
					("tags", Tag, data.tags),
					("artists", Artist, data.artists),
					("groups", Group, data.groups),
					("languages", Language, data.languages),
				]
				for rel_name, model, values in relations:
					self._add_and_link_item(session, d, rel_name, model, values)

				# Add pages
				# validate_doujinshi() should catch duplicate filename
				for i, filename in enumerate(data.pages, start=1):
					d.pages.append(Page(filename=filename, order_number=i))

				session.commit()

				self.logger.item_inserted(DatabaseStatus.OK, Doujinshi, data.id, 2)
				return DatabaseStatus.OK
			except IntegrityError as e:
				# utterly dirty quick fix
				if "UNIQUE constraint failed: doujinshi.path" in str(e):
					self.logger.path_duplicate(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE, 2)
					return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
				# TODO: give this a different status and log msg
				elif "CHECK constraint failed: length(trim(" in str(e):
					self.logger.path_duplicate(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE, 2)
					return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
				elif "UNIQUE constraint failed:" in str(e):
					self.logger.item_duplicate(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE, Doujinshi, data.id, 2)
					return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
				else:
					raise e
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e, 2)
				return DatabaseStatus.FATAL


	def _add_item_to_doujinshi(self, doujinshi_id, model, relation_name, name):
		"""Add a single `item` to an existing `Doujinshi`.

		Use public methods whenever possible.

		Parameters
		----------
		doujinshi_id : int
			ID of the doujinshi to which the item should be added.

		model : `Parody`, `Character`, `Tag`, `Artist`, `Group` or `Language`
			The model of the items to add.

		relation_name : "parodies", "characters", "tags", "artists", "groups" or "languages"
			Name of the list-like relationship of `doujinshi_model`.

		name : str
			Name of the item to add.

		Returns
		-------
		status: DatabaseStatus
			Status of the operation:
				DatabaseStatus.OK - item addeded.
				DatabaseStatus.NON_FATAL_ITEM_DUPLICATE - item already linked to doujinshi.
				DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND - doujinshi or item not found.
				DatabaseStatus.FATAL - other errors.
		"""
		with self.session() as session:
			statement = select(Doujinshi).where(Doujinshi.id == doujinshi_id)
			doujinshi = session.scalar(statement)
			if not doujinshi:
				self.logger.item_not_found(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, Doujinshi, doujinshi_id)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			statement = select(model).where(model.name == name)
			model_to_add = session.scalar(statement)
			if not model_to_add:
				self.logger.item_not_found(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, model, name)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			try:
				getattr(doujinshi, relation_name).append(model_to_add)
				session.commit()
			except IntegrityError as e:
				self.logger.doujinshi_item_duplicate(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE, model, name, doujinshi_id)
				return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e)
				return DatabaseStatus.FATAL
			else:
				self.logger.item_added_to_doujinshi(DatabaseStatus.OK, model, name, doujinshi_id)
				return DatabaseStatus.OK


	def _set_pages_to_doujinshi(self, doujinshi_id, pages=None):
		"""Set pages of an existing `Doujinshi` to a new set of pages.

		Removes all existing pages from the doujinshi and
		optionally adds new pages in the specified order.

		Parameters
		----------
		doujinshi_id : int
			ID of the doujinshi to update.

		pages : list of str, default=None
			Filenames of the new pages in order.
			If None or empty, doujinshi's pages are removed.

		Returns
		-------
		DatabaseStatus
			Status of the operation:
				DatabaseStatus.OK - pages updated.
				DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND - doujinshi not found.
				DatabaseStatus.NON_FATAL_ITEM_DUPLICATE - duplicate page filenames detected.
				DatabaseStatus.FATAL - other errors.
		"""
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
				return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e)
				return DatabaseStatus.FATAL
			else:
				self.logger.page_inserted(DatabaseStatus.OK, doujinshi_id)
				return DatabaseStatus.OK


	def add_parody_to_doujinshi(self, doujinshi_id, name):
		"""Add a `Parody` to an existing `doujinshi`."""
		return self._add_item_to_doujinshi(doujinshi_id, Parody, "parodies", name)
	def add_character_to_doujinshi(self, doujinshi_id, name):
		"""Add a `Character` to an existing `doujinshi`."""
		return self._add_item_to_doujinshi(doujinshi_id, Character, "characters", name)
	def add_tag_to_doujinshi(self, doujinshi_id, name):
		"""Add a `Tag` to an existing `doujinshi`."""
		return self._add_item_to_doujinshi(doujinshi_id, Tag, "tags", name)
	def add_artist_to_doujinshi(self, doujinshi_id, name):
		"""Add an `Artist` to an existing `doujinshi`."""
		return self._add_item_to_doujinshi(doujinshi_id, Artist, "artists", name)
	def add_group_to_doujinshi(self, doujinshi_id, name):
		"""Add a `Group` to an existing `doujinshi`."""
		return self._add_item_to_doujinshi(doujinshi_id, Group, "groups", name)
	def add_language_to_doujinshi(self, doujinshi_id, name):
		"""Add a `Language` to an existing `doujinshi`."""
		return self._add_item_to_doujinshi(doujinshi_id, Language, "languages", name)
	def add_pages_to_doujinshi(self, doujinshi_id, pages):
		"""Remove old `pages` and add new pages for an existing `doujinshi`."""
		return self._set_pages_to_doujinshi(doujinshi_id, pages)


	def _remove_item_from_doujinshi(self, doujinshi_id, model, relation_name, name):
		"""Remove an `item` from an existing `Doujinshi`.

		Use public methods whenever possible.

		Parameters
		----------
		doujinshi_id : int
			ID of the doujinshi from which the item should be removed.

		model : `Parody`, `Character`, `Tag`, `Artist`, `Group` or `Language`
			The model of the items to remove.

		relation_name : "parodies", "characters", "tags", "artists", "groups" or "languages"
			Name of the list-like relationship of `doujinshi_model`.

		name : str
			Name of the item to remove.

		Returns
		-------
		DatabaseStatus
			Status of the operation:
				DatabaseStatus.OK - item successfully removed.
				DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND - doujinshi or item not found, or item not associated with doujinshi.
				DatabaseStatus.FATAL - other errors.
		"""
		with self.session() as session:
			statement = select(Doujinshi).where(Doujinshi.id == doujinshi_id)
			doujinshi = session.scalar(statement)
			if not doujinshi:
				self.logger.item_not_found(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, Doujinshi, doujinshi_id)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			statement = select(model).where(model.name == name)
			model_to_remove = session.scalar(statement)
			if not model_to_remove:
				self.logger.item_not_found(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, model, name)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			try:
				model_list = getattr(doujinshi, relation_name)

				if model_to_remove not in model_list:
					return_status = DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND
					self.logger.item_not_in_doujinshi(return_status, model, name, doujinshi_id)
					return return_status

				model_list.remove(model_to_remove)
				session.commit()

				self.logger.item_removed_from_doujinshi(DatabaseStatus.OK, model, name, doujinshi_id)
				return DatabaseStatus.OK
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e)
				return DatabaseStatus.FATAL


	def remove_parody_from_doujinshi(self, doujinshi_id, name):
		"""Remove a `Parody` from an existing `doujinshi`."""
		return self._remove_item_from_doujinshi(doujinshi_id, Parody, "parodies", name)
	def remove_character_from_doujinshi(self, doujinshi_id, name):
		"""Remove a `Character` from an existing `doujinshi`."""
		return self._remove_item_from_doujinshi(doujinshi_id, Character, "characters", name)
	def remove_tag_from_doujinshi(self, doujinshi_id, name):
		"""Remove a `Tag` from an existing `doujinshi`."""
		return self._remove_item_from_doujinshi(doujinshi_id, Tag, "tags", name)
	def remove_artist_from_doujinshi(self, doujinshi_id, name):
		"""Remove a `Artist` from an existing `doujinshi`."""
		return self._remove_item_from_doujinshi(doujinshi_id, Artist, "artists", name)
	def remove_group_from_doujinshi(self, doujinshi_id, name):
		"""Remove a `Group` from an existing `doujinshi`."""
		return self._remove_item_from_doujinshi(doujinshi_id, Group, "groups", name)
	def remove_language_from_doujinshi(self, doujinshi_id, name):
		"""Remove a `Language` from an existing `doujinshi`."""
		return self._remove_item_from_doujinshi(doujinshi_id, Language, "languages", name)
	def remove_all_pages_from_doujinshi(self, doujinshi_id):
		"""Remove all `pages` from an existing `doujinshi`."""
		return self._set_pages_to_doujinshi(doujinshi_id, None)


	def remove_doujinshi(self, doujinshi_id):
		"""Remove a `doujinshi` (and its related items) from the database by its ID.

		Parameters
		----------
		doujinshi_id : int
			ID of the doujinshi to remove.

		Returns
		-------
		DatabaseStatus
			Status of the operation:
				DatabaseStatus.OK - doujinshi removed.
				DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND - doujinshi not found.
				DatabaseStatus.FATAL - other errors.
		"""
		with self.session() as session:
			statement = select(Doujinshi).where(Doujinshi.id == doujinshi_id)
			doujinshi = session.scalar(statement)
			if not doujinshi:
				self.logger.item_not_found(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, Doujinshi, doujinshi_id, 2)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			try:
				session.delete(doujinshi)
				session.commit()

				self.logger.doujinshi_removed(DatabaseStatus.OK, doujinshi_id, 2)
				return DatabaseStatus.OK
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e, 2)
				return DatabaseStatus.FATAL


	def _update_column_of_doujinshi(self, doujinshi_id, column_name, value):
		"""Update a single column of an existing `doujinshi`.

		Parameters
		----------
		doujinshi_id : int
			ID of the doujinshi to update.

		column_name : str
			Name of the column to update.

		value : str
			New value to set for the column.

		Returns
		-------
		DatabaseStatus
			Status of the operation:
				DatabaseStatus.OK - update succeeded.
				DatabaseStatus.NON_FATAL_ITEM_DUPLICATE - "path" column duplicate.
				DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND - doujinshi not found.
				DatabaseStatus.FATAL - other errors.
		"""
		with self.session() as session:
			statement = select(Doujinshi).where(Doujinshi.id == doujinshi_id)
			doujinshi = session.scalar(statement)
			if not doujinshi:
				self.logger.item_not_found(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, Doujinshi, doujinshi_id)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

			try:
				setattr(doujinshi, column_name, value)
				session.commit()

				self.logger.column_updated(DatabaseStatus.OK, column_name, value, doujinshi_id)
				return DatabaseStatus.OK
			except IntegrityError as e:
				# Only "path" column can trigger this.
				self.logger.path_duplicate(DatabaseStatus.NON_FATAL_ITEM_DUPLICATE)
				return DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e)
				return DatabaseStatus.FATAL


	def update_full_name_of_doujinshi(self, doujinshi_id, value):
		"""Update the full name of a `doujinshi`."""
		return self._update_column_of_doujinshi(doujinshi_id, "full_name", value)
	def update_full_name_original_of_doujinshi(self, doujinshi_id, value):
		"""Update the original full name of a `doujinshi`."""
		return self._update_column_of_doujinshi(doujinshi_id, "full_name_original", value)
	def update_pretty_name_of_doujinshi(self, doujinshi_id, value):
		"""Update the pretty name of a `doujinshi`."""
		return self._update_column_of_doujinshi(doujinshi_id, "pretty_name", value)
	def update_pretty_name_original_of_doujinshi(self, doujinshi_id, value):
		"""Update the original pretty name of a `doujinshi`."""
		return self._update_column_of_doujinshi(doujinshi_id, "pretty_name_original", value)
	def update_note_of_doujinshi(self, doujinshi_id, value):
		"""Update the note of a `doujinshi`."""
		return self._update_column_of_doujinshi(doujinshi_id, "note", value)
	def update_path_of_doujinshi(self, doujinshi_id, value):
		"""Update the path of a `doujinshi`, normalizing to POSIX style."""
		return self._update_column_of_doujinshi(doujinshi_id, "path", pathlib.Path(value).as_posix())


	def _get_count_by_name(self, model, names, session=None):
		"""Get the number of `doujinshi` associated with each `item`.

		Parameters
		----------
		model : `Parody`, `Character`, `Tag`, `Artist`, `Group` or `Language`
			Mdel to retrieve counts.

		names : list of str
			Names of the items to retrieve counts for.

		session : sqlalchemy.orm.Session, default=None
			SQLAlchemy session to use for the query.

		Returns
		-------
		status : DatabaseStatus
			DatabaseStatus.OK - count retrieved.
			DatabaseStatus.FATAL - error occured.

		count_dict : dict
			Dictionary mapping item names to their counts. Items not found will have count 0.
		"""
		if not names:
			return DatabaseStatus.OK, {}

		statement = select(model.name, model.count).where(model.name.in_(names))

		try:
			if session:
				count_dict = dict(session.execute(statement).all())
			else:
				with self.session() as session_in:
					count_dict = dict(session_in.execute(statement).all())

			# fill in missing ones with 0
			return DatabaseStatus.OK, {name: count_dict.get(name, 0) for name in names}
		except Exception as e:
			self.logger.exception(DatabaseStatus.FATAL, e)
			return DatabaseStatus.FATAL, {}


	def get_count_of_parodies(self, names):
		"""Get counts of `parodies` by a list of names."""
		return self._get_count_by_name(Parody, names)
	def get_count_of_characters(self, names):
		"""Get counts of `characters` by a list of names."""
		return self._get_count_by_name(Character, names)
	def get_count_of_tags(self, names):
		"""Get counts of `tags` by a list of names."""
		return self._get_count_by_name(Tag, names)
	def get_count_of_artists(self, names):
		"""Get counts of `artists` by a list of names."""
		return self._get_count_by_name(Artist, names)
	def get_count_of_groups(self, names):
		"""Get counts of `groups` by a list of names."""
		return self._get_count_by_name(Group, names)
	def get_count_of_languages(self, names):
		"""Get counts of `languages` by a list of names."""
		return self._get_count_by_name(Language, names)


	def get_doujinshi(self, doujinshi_id):
		"""
		Retrieve a doujinshi and its data by ID.

		Parameters
		----------
		doujinshi_id : int
			ID of the doujinshi to retrieve.

		Returns
		-------
		status : DatabaseStatus
			DatabaseStatus.OK - doujinshi retrieved.
			DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND - doujinshi not found.
			DatabaseStatus.FATAL - other errors.

		doujinshi : dict or None
			A dictionary if found, containing these fields:
				Single-valued:
					'id',
					'path',
					'note',
					'full_name', 'full_name_original',
					'pretty_name', 'pretty_name_original',
				List-like:
					'parodies', 'characters', 'tags',
					'artists', 'groups', 'languages',
					'pages'.
			Otherwise None.
		"""
		with self.session() as session:
			statement = select(Doujinshi).where(Doujinshi.id == doujinshi_id)
			doujinshi = session.scalar(statement)

			if not doujinshi:
				self.logger.item_not_found(DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, Doujinshi, doujinshi_id, 2)
				return DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND, None

			doujinshi_dict = {
				"id": doujinshi.id,
				"full_name": doujinshi.full_name,
				"full_name_original": doujinshi.full_name_original,
				"pretty_name": doujinshi.pretty_name,
				"pretty_name_original": doujinshi.pretty_name_original,
				"path": doujinshi.path,
				"note": doujinshi.note
			}
			doujinshi_dict["pages"] = [p.filename for p in doujinshi.pages]

			relationships = {
				"parodies": (Parody, doujinshi.parodies),
				"characters": (Character, doujinshi.characters),
				"tags": (Tag, doujinshi.tags),
				"artists": (Artist, doujinshi.artists),
				"groups": (Group, doujinshi.groups),
				"languages": (Language, doujinshi.languages),
			}
			for key, (model, rel_objs) in relationships.items():
				names = [obj.name for obj in rel_objs]
				_, doujinshi_dict[key] = self._get_count_by_name(model, names, session)

			return DatabaseStatus.OK, doujinshi_dict


	def get_doujinshi_in_page(self, page_size, page_number, n_doujinshi=None):
		"""Retrieve a paginated list of (latest ID) doujinshi.

		Parameters
		----------
		page_size : int
			Number of doujinshi per page.

		page_number : int
			Page number to retrieve (1-based).

		n_doujinshi : int, default=None
			Total number of doujinshi. If not None, this value is used to optimize retrieval of later pages.

		Returns
		-------
			status : DatabaseStatus
				DatabaseStatus.OK - retrieval succeeded.
				DatabaseStatus.FATAL - error occured.
			doujinshi_list : list of dict
				Each dict contains: 'id', 'full_name', 'path' and 'cover_filename'.
		"""
		if page_number < 1:
			return DatabaseStatus.OK, []

		doujinshi_list = []

		desc_order = True
		offset = (page_number - 1) * page_size
		limit = page_size

		if n_doujinshi:
			max_page_number = math.ceil(n_doujinshi / page_size)
			last_page_size = n_doujinshi % page_size or page_size

			# Page is in second half
			if page_number > math.ceil(max_page_number / 2):
				desc_order = False
				offset = last_page_size + (max_page_number - page_number - 1) * page_size

				# Special case: last page
				if page_number == max_page_number:
					limit = last_page_size
					offset = (max_page_number - page_number) * page_size

		with self.session() as session:
			try:
				subq = (
					select(Page.filename)
					.where(Page.doujinshi_id == Doujinshi.id)
					.where(Page.order_number == 1)
					.scalar_subquery()
				)

				if desc_order:
					order = Doujinshi.id.desc()
				else:
					order = Doujinshi.id.asc()

				statement = (
					select(
						Doujinshi.id, Doujinshi.full_name, Doujinshi.path,
						subq.label("filename")
					)
					.order_by(order)
					.limit(limit)
					.offset(offset)
				)
				results = session.execute(statement).all()

				iter_results = results if desc_order else reversed(results)
				for doujinshi_id, full_name, path, cover_filename in iter_results:
					doujinshi_list.append({
						"id": doujinshi_id,
						"full_name": full_name,
						"path": path,
						"cover_filename": cover_filename
					})

				return DatabaseStatus.OK, doujinshi_list
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e, 2)
				return DatabaseStatus.FATAL, []


	def get_doujinshi_in_range(self, id_start=1, id_end=None):
		"""Retrieve all doujinshi within an ID range.

		Parameters
		----------
		id_start : int, default=1
			Start ID of the range (inclusive).

		id_end : int, default=None
			End ID of the range (inclusive). If None, retrieves all doujinshi from *id_start*.

		Returns
		-------
		status : DatabaseStatus
			DatabaseStatus.OK - retrieval succeeded.
			DatabaseStatus.FATAL - error occured.

		doujinshi_list : list of dict
			Each dict contains these fields:
				Single-valued:
					'id', 'path', 'note'
					'full_name', 'full_name_original',
					'pretty_name', 'pretty_name_original',
				List-valued:
					'parodies', 'characters', 'tags',
					'artists', 'groups', 'languages'
					'pages'
		"""
		# TODO: get_doujinshi explain query to check if it uses index efficiently.
		with self.session() as session:
			try:
				statement = select(Doujinshi).where(Doujinshi.id >= id_start)
				if id_end:
					statement = statement.where(Doujinshi.id <= id_end)

				retrieved_doujinshi = session.scalars(statement)

				doujinshi_list = []
				single_value_attr = [
					"id",
					"full_name","full_name_original",
					"pretty_name", "pretty_name_original",
					"path", "note"
				]
				list_value_attr = [
					"parodies", "characters", "tags",
					"artists", "groups", "languages"
				]

				for doujinshi in retrieved_doujinshi:
					doujinshi_dict = {attr: getattr(doujinshi, attr) for attr in single_value_attr}
					for attr in list_value_attr:
						doujinshi_dict[attr] = [model.name for model in getattr(doujinshi, attr)]
					doujinshi_dict["pages"] = [page.filename for page in doujinshi.pages]
					doujinshi_list.append(doujinshi_dict)

				return DatabaseStatus.OK, doujinshi_list
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e, 2)
				return DatabaseStatus.FATAL, []


	def _update_count(self, model, model_id_column, d_id_column, session):
		"""Update the 'count' column of a given `item`.

		Parameters
		----------
		model : `Parody`, `Character`, `Tag`, `Artist`, `Group` or `Language`
			Model whose 'count' column will be updated.

		model_id_column : Column
			Column in the many-to-many table representing the model's ID.

		d_id_column : Column
			Column in the many-to-many table representing the doujinshi's ID.

		session : sqlalchemy.orm.Session
			SQLAlchemy session to use for the query.
		"""
		subq = (
			select(model_id_column, func.count(d_id_column).label("item_count"))
			.group_by(model_id_column)
			.subquery()
		)
		session.execute(update(model).values(count=0)) # in case model somehow has no doujinshi.
		session.execute(
			update(model)
			.values(count=subq.c.item_count)
			.where(model.id == subq.c[model_id_column.key])
		)


	def _update_count_by_item_type(self, model, model_id_column, d_id_column, session=None):
		"""Update the 'count' column for a specific item type.

		Parameters
		----------
		model : `Parody`, `Character`, `Tag`, `Artist`, `Group` or `Language`
			Model whose `count` column should be updated.

		model_id_column : Column
			The column in the many-to-many table representing the model's ID.

		d_id_column : Column
			The column in the many-to-many table representing the doujinshi's ID.

		session : sqlalchemy.orm.Session, default=None
			SQLAlchemy session to use for the query.

		Returns
		-------
		status: DatabaseStatus
			DatabaseStatus.OK - count updated.
			DatabaseStatus.FATAL - error occurred.
		"""
		if session:
			self._update_count(model, model_id_column, d_id_column, session)
		else:
			with self.session() as session:
				try:
					self._update_count(model, model_id_column, d_id_column, session)
					session.commit()
				except Exception as e:
					self.logger.exception(DatabaseStatus.FATAL, e)
					return DatabaseStatus.FATAL
				else:
					return DatabaseStatus.OK


	def update_count_of_parody(self):
		"""Update the 'count' column for all `Parody` items."""
		return self._update_count_by_item_type(Parody, d_parody.c.parody_id, d_parody.c.doujinshi_id)
	def update_count_of_character(self):
		"""Update the 'count' column for all `Character` items."""
		return self._update_count_by_item_type(Character, d_character.c.character_id, d_character.c.doujinshi_id)
	def update_count_of_tag(self):
		"""Update the 'count' column for all `Tag` items."""
		return self._update_count_by_item_type(Tag, d_tag.c.tag_id, d_tag.c.doujinshi_id)
	def update_count_of_artist(self):
		"""Update the 'count' column for all `Artist` items."""
		return self._update_count_by_item_type(Artist, d_artist.c.artist_id, d_artist.c.doujinshi_id)
	def update_count_of_group(self):
		"""Update the 'count' column for all `Group` items."""
		return self._update_count_by_item_type(Group, d_circle.c.circle_id, d_circle.c.doujinshi_id)
	def update_count_of_language(self):
		"""Update the 'count' column for all `Language` items."""
		return self._update_count_by_item_type(Language, d_language.c.language_id, d_language.c.doujinshi_id)


	def update_count_of_all(self):
		"""Update the 'count' column for all `item types`.

		Returns
		-------
		status : DatabaseStatus
			DatabaseStatus.OK - all counts updated.
			DatabaseStatus.FATAL - error occurred.
		"""
		params = [
			(Parody, d_parody.c.parody_id, d_parody.c.doujinshi_id),
			(Character, d_character.c.character_id, d_character.c.doujinshi_id),
			(Tag, d_tag.c.tag_id, d_tag.c.doujinshi_id),
			(Artist, d_artist.c.artist_id, d_artist.c.doujinshi_id),
			(Group, d_circle.c.circle_id, d_circle.c.doujinshi_id),
			(Language, d_language.c.language_id, d_language.c.doujinshi_id),
		]
		with self.session() as session:
			try:
				for model, model_id_column, d_id_column in params:
					self._update_count_by_item_type(model, model_id_column, d_id_column, session)
				session.commit()
				return DatabaseStatus.OK
			except Exception as e:
				self.logger.exception(DatabaseStatus.FATAL, e, 2)
				return DatabaseStatus.FATAL


	def how_many_doujinshi(self):
		"""Get the total number of `doujinshi` in the database.

		Returns
		-------
		count : int
			The total number of `doujinshi` rows in the database.
		"""
		with self.session() as session:
			return session.scalar(select(func.count()).select_from(Doujinshi))


	# TODO: implement bulk_insert
	# TODO: check if tests include update_count
	#       add usage examples
	#       add db schema description