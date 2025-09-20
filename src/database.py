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
from sqlalchemy import create_engine, event, select, func, update, text, insert, delete, update
from sqlalchemy import Integer, DateTime
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, validates, selectinload, joinedload, load_only
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
		self.enable_logger()


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


	def disable_logger(self):
		self.logger.disable()
	def enable_logger(self):
		self.logger.enable()


	def create_database(self):
		"""Initialize the database schema and insert default languages.

		Creates all tables defined in the SQLAlchemy `Base` metadata and
		inserts a set of default languages ("english", "japanese", "textless", "chinese").

		Does nothing if a schema already exists.

		Returns
		-------
		status : DatabaseStatus
			Status of the operation:
				DatabaseStatus.OK - database created.
		"""
		Base.metadata.create_all(self.engine)
		self.logger.success(msg="database created", stacklevel=1)
		self.create_index()
		self.create_triggers()

		# Note:
		# The language insertion order determines priority.
		# MIN(language_id) maps to primary (most prioritized) language, starts from 1.
		self.insert_language("english")
		self.insert_language("japanese")
		self.insert_language("chinese")
		self.insert_language("textless")
		return DatabaseStatus.OK


	def _create_triggers_increase(self):
		tbl_names = ["parody", "character", "tag", "artist", "circle", "language"]
		return [f"""
			CREATE TRIGGER IF NOT EXISTS trig_a_i_incr_{tbl_name}_count
			AFTER INSERT ON doujinshi_{tbl_name}
			FOR EACH ROW
			BEGIN
				UPDATE {tbl_name}
				SET count = count + 1
				WHERE id = NEW.{tbl_name}_id;
			END;
		""" for tbl_name in tbl_names
		]
	def _create_triggers_decrease(self):
		tbl_names = ["parody", "character", "tag", "artist", "circle", "language"]
		return [f"""
			CREATE TRIGGER IF NOT EXISTS trig_a_d_decr_{tbl_name}_count
			AFTER DELETE ON doujinshi_{tbl_name}
			FOR EACH ROW
			BEGIN
				UPDATE {tbl_name}
				SET count = count - 1
				WHERE id = OLD.{tbl_name}_id;
			END;
		""" for tbl_name in tbl_names
		]


	def create_triggers(self):
		with self.session() as session:
			for trigger in self._create_triggers_increase():
				session.execute(text(trigger))
			for trigger in self._create_triggers_decrease():
				session.execute(text(trigger))
			self.logger.success("triggers created", stacklevel=1)
			return DatabaseStatus.OK


	def _idx_components(self):
		"""Return index definitions.

		Each entry is a tuple of (index_name, on_clause) for the many-to-many
		tables.

		WARNING: this is hardcoded, so update if the underlying models change.
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
		"""(Re)Create `extra indices` listed in `_idx_components`.

		Returns
		-------
		status : DatabaseStatus
			Status of the operation:
				DatabaseStatus.OK - extra indices created.
		"""
		with self.session() as session:
			for idx_name, on_clause in self._idx_components():
				statement = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {on_clause}"
				session.execute(text(statement))
			session.commit()
			self.logger.success("extra indices created", stacklevel=1)
			return DatabaseStatus.OK


	def drop_index(self):
		"""Drop `all extra` indices listed in `_idx_components`..

		Returns
		-------
		status : DatabaseStatus
			Status of the operation:
				DatabaseStatus.OK - extra indices dropped.
		"""
		with self.session() as session:
			for idx_name, _ in self._idx_components():
				statement = f"DROP INDEX IF EXISTS {idx_name}"
				session.execute(text(statement))
			session.commit()
			self.logger.success("extra indices dropped", stacklevel=1)
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


	def _is_unique_violated(self, error, what_violated):
		# Specific to SQLite. Rewrite this when you change the underlying db.
		e_str = str(error)
		if "UNIQUE" in e_str and what_violated in e_str:
			return True
		return False


	def _insert_item(self, model, name):
		"""Insert a single item into the database.

		Use public methods whenever possible.

		Parameters
		----------
		model : Parody|Character|Tag|Artist|Group|Language
			Type of the item being inserted.

		name : str
			Name of the item to insert.

		Returns
		-------
		status : DatabaseStatus
			Status of the operation:
				DatabaseStatus.OK - item inserted.
				DatabaseStatus.ALREADY_EXISTS - item already exists.
				DatabaseStatus.EXCEPTION - other errors.
		"""
		with self.session() as session:
			tbl_name = model.__tablename__
			try:
				new_item = model(name=name)
				session.add(new_item)
				session.commit()
				self.logger.success(msg=f"{tbl_name} {name!r} inserted", stacklevel=2)
				return DatabaseStatus.OK
			except IntegrityError as e:
				if self._is_unique_violated(e, f"{tbl_name}.name"):
					self.logger.already_exists(what=f"{tbl_name} {name!r}", stacklevel=2)
					return DatabaseStatus.ALREADY_EXISTS

				self.logger.integrity_error(e, stacklevel=2, rollback=True)
				return DatabaseStatus.INTEGRITY_ERROR
			except Exception as e:
				print(e)
				self.logger.exception(e, stacklevel=2, rollback=True)
				return DatabaseStatus.EXCEPTION


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
		"""Insert a list of `items` into the database (except Page) (if not exist) and link them to a `doujinshi`.

		Notes
		-----
		This function does NOT commit the change, the caller is responsible for this.

		Parameters
		----------
		session : sqlalchemy.orm.Session
			The session handling this function.

		doujinshi_model : Doujinshi
			doujinshi to which items will be linked.

		relation_name : "parodies"|"characters"|"tags"|"artists"|"groups"|"languages"
			Name of the list-like relationship of `doujinshi_model`.

		Model : Parody|Character|Tag|Artist|Group|Language
			Model of the items to add.

		item_names : list of str
			Names of the items to add and link.
		"""
		if not item_names:
			# Save 1 db roundtrip if there is no item to insert.
			return

		tbl_name = Model.__tablename__
		items_in_doujinshi = getattr(doujinshi_model, relation_name)

		existing_models = {
			model.name: model
			for model in session.scalars(
				select(Model)
				.options(load_only(Model.id, Model.name))
				.where(Model.name.in_(item_names))
		)}

		# This is 2-4x faster than
		# for name in item_names:
			# model = existing_models.get(name, None)
		missing_models = item_names - existing_models.keys()
		new_models = [Model(name=name, count=0) for name in missing_models]
		session.add_all(new_models)

		for model in new_models:
			self.logger.success(msg=f"{tbl_name} {model.name!r} inserted", stacklevel=2)
			existing_models[model.name] = model

		for name in item_names:
			model = existing_models[name]
			items_in_doujinshi.append(model)
			msg = f"doujinshi #{doujinshi_model.id} <-> {tbl_name} {name!r}"
			self.logger.success(msg=msg, stacklevel=2)


	def insert_doujinshi(self, doujinshi, user_prompt=True, disable_validation=False):
		"""Insert a single doujinshi into the database.

		Performs these actions in order:
			validate the doujinshi,
			check for doujinshi duplicates by ID,
			add doujinshi bare info,
			call self._add_and_link_item(),
			link pages to the doujinshi.

		Parameters
		----------
		doujinshi : dict
			Contains doujinshi data. Expected fields:
				Single-valued:
					'id', 'path', 'note',
					'full_name', 'full_name_original',
					'pretty_name', 'pretty_name_original',
				List of str:
					'parodies', 'characters', 'tags',
					'artists', 'groups', 'languages',
					'pages' (ordered).

		user_prompt : bool, default=True
			Whether to prompt the user during doujinshi validation.
			If all doujinshi fields are already filled, no prompt is shown.
			If False, validation will not alert user about empty list-like fields or warnings.

		Returns
		-------
		status : DatabaseStatus
			Status of the operation:
				DatabaseStatus.OK - insertion succeeded.
				DatabaseStatus.VALIDATION_FAILED - validation failed.
				DatabaseStatus.ALREADY_EXISTS - doujinshi ID already exists.
				DatabaseStatus.INTEGRITY_ERROR - integrity errors (likely "path" uniqueness violation).
				DatabaseStatus.EXCEPTION - other errors.
		"""
		if not disable_validation:
			if not validate_doujinshi(doujinshi, user_prompt=user_prompt):
				self.logger.validation_failed(stacklevel=1)
				return DatabaseStatus.VALIDATION_FAILED

		d_data = SimpleNamespace(**doujinshi)

		with self.session() as session:
			try:
				statement = select(Doujinshi.id).where(Doujinshi.id == d_data.id)
				if session.scalar(statement):
					self.logger.already_exists(f"doujinshi #{d_data.id}", stacklevel=1)
					return DatabaseStatus.ALREADY_EXISTS

				# Add info to doujinshi table.
				d = Doujinshi(
					id=d_data.id,
					full_name=d_data.full_name, full_name_original=d_data.full_name_original,
					pretty_name=d_data.pretty_name, pretty_name_original=d_data.pretty_name_original,
					note=d_data.note,
					path=d_data.path,
				)
				session.add(d)

				# Add and link item by types.
				relations = [
					("parodies", Parody, d_data.parodies),
					("characters", Character, d_data.characters),
					("tags", Tag, d_data.tags),
					("artists", Artist, d_data.artists),
					("groups", Group, d_data.groups),
					("languages", Language, d_data.languages),
				]
				for rel_name, model, item_names in relations:
					self._add_and_link_item(session, d, rel_name, model, item_names)

				# Add pages.
				# validate_doujinshi() should catch duplicate filename.
				for i, filename in enumerate(d_data.pages, start=1):
					d.pages.append(Page(filename=filename, order_number=i))

				session.commit()

				self.logger.success(msg=f"doujinshi #{d_data.id} inserted", stacklevel=1)
				return DatabaseStatus.OK
			except IntegrityError as e:
				# doujinshi.id is catched above,
				# so this UNIQUE violation is on doujinshi.path.
				self.logger.integrity_error(e, stacklevel=1, rollback=True)
				return DatabaseStatus.INTEGRITY_ERROR
			except Exception as e:
				self.logger.exception(e, stacklevel=1, rollback=True)
				return DatabaseStatus.EXCEPTION


	def _add_item_to_doujinshi(self, doujinshi_id, model, relation_name, name, m2m_table):
		"""Add an existing `item` to an existing `Doujinshi` by name.

		The "existing" part is intentional to avoid inserting similar/typo'ed item.

		Use public methods whenever possible.

		Parameters
		----------
		doujinshi_id : int
			ID of the doujinshi to which the item should be added.

		model : Parody|Character|Tag|Artist|Group|Language
			The model of the items to add.

		relation_name : "parodies"|"characters"|"tags"|"artists"|"groups"|"languages"
			Name of the list-like relationship of `doujinshi_model`.

		name : str
			Name of the item to add.

		m2m_table : sqlalchemy.sql.schema.Table
			Many-to-many table into which the doujinshi.id and item.id will be inserted.

		Returns
		-------
		status: DatabaseStatus
			Status of the operation:
				DatabaseStatus.OK - item addeded.
				DatabaseStatus.ALREADY_EXISTS - item already linked to doujinshi.
				DatabaseStatus.NOT_FOUND - doujinshi or item not found.
				DatabaseStatus.EXCEPTION - other errors.
		"""
		with self.session() as session:
			try:
				# The number of item is (expected to be) way smaller than The number of doujinshi,
				# so check item duplication first?
				model_str = f"{model.__tablename__} {name!r}"
				doujinshi_str = f"doujinshi #{doujinshi_id}"

				model_id = session.scalar(select(model.id).where(model.name == name))
				if not model_id:
					self.logger.not_found(model_str, stacklevel=2)
					return DatabaseStatus.NOT_FOUND

				doujinshi =  session.scalar(select(Doujinshi.id).where(Doujinshi.id == doujinshi_id))
				if not doujinshi:
					self.logger.not_found(doujinshi_str, stacklevel=2)
					return DatabaseStatus.NOT_FOUND

				model_id_column = f"{model.__tablename__}_id"
				session.execute(
					insert(m2m_table)
					.values(
						doujinshi_id=doujinshi_id,
						**{model_id_column: model_id}
					)
				)
				session.commit()

				self.logger.success(msg=f"{doujinshi_str} <-> {model_str}", stacklevel=2)
				return DatabaseStatus.OK
			except IntegrityError as e:
				self.logger.already_exists(f"{doujinshi_str} <-> {model_str}", stacklevel=2, rollback=True)
				return DatabaseStatus.ALREADY_EXISTS
			except Exception as e:
				self.logger.exception(e, stacklevel=2, rollback=True)
				return DatabaseStatus.EXCEPTION


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
				DatabaseStatus.NOT_FOUND - doujinshi not found.
				DatabaseStatus.INTEGRITY_ERROR - integrity error (likely duplicate filenames).
				DatabaseStatus.EXCEPTION - other errors.
		"""
		with self.session() as session:
			doujinshi_str = f"doujinshi #{doujinshi_id}"

			try:
				doujinshi =  session.scalar(select(Doujinshi.id).where(Doujinshi.id == doujinshi_id))
				if not doujinshi:
					self.logger.not_found(doujinshi_str, stacklevel=2)
					return DatabaseStatus.NOT_FOUND

				# Remove old pages
				statement = delete(Page).where(Page.doujinshi_id == doujinshi_id)
				session.execute(statement)

				# Analogous to remove
				if not pages:
					session.commit()
					self.logger.success(msg=f"{doujinshi_str} removed all pages", stacklevel=2)
					return DatabaseStatus.OK

				# Add new pages.
				pages_to_insert = [
					{"doujinshi_id": doujinshi_id, "order_number": i, "filename": filename}
					for i, filename in enumerate(pages, start=1)
				]
				session.execute(insert(Page), pages_to_insert)

				session.commit()

				self.logger.success(msg=f"{doujinshi_str} added new pages", stacklevel=2)
				return DatabaseStatus.OK
			except IntegrityError as e:
				self.logger.integrity_error(e, stacklevel=2, rollback=True)
				return DatabaseStatus.INTEGRITY_ERROR
			except Exception as e:
				self.logger.exception(e, stacklevel=2, rollback=True)
				return DatabaseStatus.EXCEPTION


	def add_parody_to_doujinshi(self, doujinshi_id, name):
		"""Add a `Parody` to an existing `doujinshi`."""
		return self._add_item_to_doujinshi(doujinshi_id, Parody, "parodies", name, d_parody)
	def add_character_to_doujinshi(self, doujinshi_id, name):
		"""Add a `Character` to an existing `doujinshi`."""
		return self._add_item_to_doujinshi(doujinshi_id, Character, "characters", name, d_character)
	def add_tag_to_doujinshi(self, doujinshi_id, name):
		"""Add a `Tag` to an existing `doujinshi`."""
		return self._add_item_to_doujinshi(doujinshi_id, Tag, "tags", name, d_tag)
	def add_artist_to_doujinshi(self, doujinshi_id, name):
		"""Add an `Artist` to an existing `doujinshi`."""
		return self._add_item_to_doujinshi(doujinshi_id, Artist, "artists", name, d_artist)
	def add_group_to_doujinshi(self, doujinshi_id, name):
		"""Add a `Group` to an existing `doujinshi`."""
		return self._add_item_to_doujinshi(doujinshi_id, Group, "groups", name, d_circle)
	def add_language_to_doujinshi(self, doujinshi_id, name):
		"""Add a `Language` to an existing `doujinshi`."""
		return self._add_item_to_doujinshi(doujinshi_id, Language, "languages", name, d_language)
	def add_pages_to_doujinshi(self, doujinshi_id, pages):
		"""Remove old `pages` and add new pages for an existing `doujinshi`."""
		return self._set_pages_to_doujinshi(doujinshi_id, pages)


	def _remove_item_from_doujinshi(self, doujinshi_id, model, name, m2m_table, m2m_table_item_id_col):
		"""Remove an `item` from an existing `Doujinshi`.

		Use public methods whenever possible.

		Parameters
		----------
		doujinshi_id : int
			ID of the doujinshi from which the item should be removed.

		model : Parody|Character|Tag|Artist|Group|Language
			Model of the item to remove.

		name : str
			Name of the item to remove.

		m2m_table : sqlalchemy.sql.schema.Table
			Many-to-many table from which the doujinshi.id and item.id will be deleted.

		m2m_table_item_id_col : sqlalchemy.sql.schema.Column
			Many-to-many table column in which the item.id is in.

		Returns
		-------
		DatabaseStatus
			Status of the operation:
				DatabaseStatus.OK - item successfully removed.
				DatabaseStatus.NOT_FOUND - doujinshi or item not found, or item not associated with doujinshi.
				DatabaseStatus.EXCEPTION - other errors.
		"""
		with self.session() as session:
			model_str = f"{model.__tablename__} {name!r}"
			doujinshi_str = f"doujinshi #{doujinshi_id}"

			try:
				model_id_to_remove = session.scalar(select(model.id).where(model.name == name))
				if not model_id_to_remove:
					self.logger.not_found(model_str, stacklevel=2)
					return DatabaseStatus.NOT_FOUND

				doujinshi =  session.scalar(select(Doujinshi.id).where(Doujinshi.id == doujinshi_id))
				if not doujinshi:
					self.logger.not_found(doujinshi_str, stacklevel=2)
					return DatabaseStatus.NOT_FOUND

				doujinshi_item =  session.scalar(
					select(m2m_table)
					.where(m2m_table.c.doujinshi_id == doujinshi_id)
					.where(m2m_table_item_id_col == model_id_to_remove)
				)
				if not doujinshi_item:
					self.logger.not_found(f"{doujinshi_str} <-> {model_str}", stacklevel=2)
					return DatabaseStatus.NOT_FOUND

				session.execute(
					delete(m2m_table)
					.where(m2m_table.c.doujinshi_id == doujinshi_id)
					.where(m2m_table_item_id_col == model_id_to_remove)
				)
				session.commit()
				self.logger.success(msg=f"{doujinshi_str} removed {model_str}", stacklevel=2)
				return DatabaseStatus.OK
			except Exception as e:
				self.logger.exception(e, stacklevel=2, rollback=True)
				return DatabaseStatus.EXCEPTION


	def remove_parody_from_doujinshi(self, doujinshi_id, name):
		"""Remove a `Parody` from an existing `doujinshi`."""
		return self._remove_item_from_doujinshi(doujinshi_id, Parody, name, d_parody, d_parody.c.parody_id)
	def remove_character_from_doujinshi(self, doujinshi_id, name):
		"""Remove a `Character` from an existing `doujinshi`."""
		return self._remove_item_from_doujinshi(doujinshi_id, Character, name, d_character, d_character.c.character_id)
	def remove_tag_from_doujinshi(self, doujinshi_id, name):
		"""Remove a `Tag` from an existing `doujinshi`."""
		return self._remove_item_from_doujinshi(doujinshi_id, Tag, name, d_tag, d_tag.c.tag_id)
	def remove_artist_from_doujinshi(self, doujinshi_id, name):
		"""Remove a `Artist` from an existing `doujinshi`."""
		return self._remove_item_from_doujinshi(doujinshi_id, Artist, name, d_artist, d_artist.c.artist_id)
	def remove_group_from_doujinshi(self, doujinshi_id, name):
		"""Remove a `Group` from an existing `doujinshi`."""
		return self._remove_item_from_doujinshi(doujinshi_id, Group, name, d_circle, d_circle.c.circle_id)
	def remove_language_from_doujinshi(self, doujinshi_id, name):
		"""Remove a `Language` from an existing `doujinshi`."""
		return self._remove_item_from_doujinshi(doujinshi_id, Language, name, d_language, d_language.c.language_id)
	def remove_all_pages_from_doujinshi(self, doujinshi_id):
		"""Remove all `pages` from an existing `doujinshi`."""
		return self._set_pages_to_doujinshi(doujinshi_id, None)


	def remove_doujinshi(self, doujinshi_id):
		"""Remove a `doujinshi` from the database by ID.

		All of its related `items` (parodies, characters, tags,
		artists, groups, languages, pages) will be removed as well.

		Parameters
		----------
		doujinshi_id : int
			ID of the doujinshi to remove.

		Returns
		-------
		DatabaseStatus
			Status of the operation:
				DatabaseStatus.OK - doujinshi removed.
				DatabaseStatus.NOT_FOUND - doujinshi not found.
				DatabaseStatus.EXCEPTION - other errors.
		"""
		with self.session() as session:
			doujinshi_str = f"doujinshi #{doujinshi_id}"
			try:
				if not session.scalar(select(Doujinshi.id).where(Doujinshi.id == doujinshi_id)):
					self.logger.not_found(doujinshi_str, stacklevel=1)
					return DatabaseStatus.NOT_FOUND

				# ON DELETE CASCADE relationships will handle other deletions.
				session.execute(delete(Doujinshi).where(Doujinshi.id == doujinshi_id))
				session.commit()

				self.logger.success(msg=f"{doujinshi_str} removed", stacklevel=1)
				return DatabaseStatus.OK
			except Exception as e:
				self.logger.exception(e, stacklevel=1, rollback=True)
				return DatabaseStatus.EXCEPTION


	def _update_column_of_doujinshi(self, doujinshi_id, column, value):
		"""Update a single column of an existing `doujinshi`.

		Parameters
		----------
		doujinshi_id : int
			ID of the doujinshi to update.

		column : sqlalchemy.sql.schema.Column
			Name of the column to update.

		value : str
			New value to set for the column.

		Returns
		-------
		DatabaseStatus
			Status of the operation:
				DatabaseStatus.OK - update succeeded.
				DatabaseStatus.INTEGRITY_ERROR - integrity errors (likely "path" uniqueness violation).
				DatabaseStatus.NOT_FOUND - doujinshi not found.
				DatabaseStatus.EXCEPTION - other errors.
		"""
		with self.session() as session:
			doujinshi_str = f"doujinshi #{doujinshi_id}"
			column_name = column.name

			try:
				if not session.scalar(select(Doujinshi.id).where(Doujinshi.id == doujinshi_id)):
					self.logger.not_found(doujinshi_str, stacklevel=2)
					return DatabaseStatus.NOT_FOUND

				session.execute(
					update(Doujinshi)
					.where(Doujinshi.id == doujinshi_id)
					.values({f"{column.name}": value})
				)
				session.commit()

				self.logger.success(f"{doujinshi_str} updated new {column_name} {value!r}", stacklevel=2)
				return DatabaseStatus.OK
			except ValueError as e:
				if "must be a non-empty string" in str(e):
					# Refer to logger.DatabaseLogger.log_event
					msg = f"'{column_name} must be a non-empty string, got {value!r} instead"
					self.logger.log_event(logging.INFO, DatabaseStatus.INTEGRITY_ERROR, stacklevel=3, msg=msg)
					return DatabaseStatus.INTEGRITY_ERROR
				self.logger.exception(e, stacklevel=2, rollback=True)
				return DatabaseStatus.EXCEPTION
			except IntegrityError as e:
				# Only "path" column can trigger this.
				self.logger.integrity_error(e, stacklevel=2, rollback=True)
				return DatabaseStatus.INTEGRITY_ERROR
			except Exception as e:
				self.logger.exception(e, stacklevel=2, rollback=True)
				return DatabaseStatus.EXCEPTION


	def update_full_name_of_doujinshi(self, doujinshi_id, value):
		"""Update the full name of a `doujinshi`."""
		return self._update_column_of_doujinshi(doujinshi_id, Doujinshi.__table__.c.full_name, value)
	def update_full_name_original_of_doujinshi(self, doujinshi_id, value):
		"""Update the original full name of a `doujinshi`."""
		return self._update_column_of_doujinshi(doujinshi_id, Doujinshi.__table__.c.full_name_original, value)
	def update_pretty_name_of_doujinshi(self, doujinshi_id, value):
		"""Update the pretty name of a `doujinshi`."""
		return self._update_column_of_doujinshi(doujinshi_id, Doujinshi.__table__.c.pretty_name, value)
	def update_pretty_name_original_of_doujinshi(self, doujinshi_id, value):
		"""Update the original pretty name of a `doujinshi`."""
		return self._update_column_of_doujinshi(doujinshi_id, Doujinshi.__table__.c.pretty_name_original, value)
	def update_note_of_doujinshi(self, doujinshi_id, value):
		"""Update the note of a `doujinshi`."""
		return self._update_column_of_doujinshi(doujinshi_id, Doujinshi.__table__.c.note, value)
	def update_path_of_doujinshi(self, doujinshi_id, value):
		"""Update the path of a `doujinshi`, normalizing to POSIX style."""
		return self._update_column_of_doujinshi(doujinshi_id, Doujinshi.__table__.c.path, pathlib.Path(value).as_posix())


	def _get_count_by_name(self, model, names, session=None):
		"""Get the number of `doujinshi` associated with each `item`.

		Parameters
		----------
		model : Parody|Character|Tag|Artist|Group|Language
			Mdel to retrieve counts.

		names : list of str
			Names of the items to retrieve counts for.

		session : sqlalchemy.orm.Session, default=None
			SQLAlchemy session to use for the query.

		Returns
		-------
		count_dict : dict
			Dictionary mapping sorted item names to their counts.
			Items not found won't be included.
		"""
		if not names:
			return {}

		statement = (
			select(model.name, model.count)
			.where(model.name.in_(names))
			.order_by(model.name.asc())
		)

		if session:
			count_dict = dict(session.execute(statement).all())
			return count_dict

		with self.session() as another_session:
			try:
				count_dict = dict(another_session.execute(statement).all())
				return count_dict
			except Exception as e:
				self.logger.exception(e, stacklevel=2, rollback=True)
				return {}


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
		Retrieve a full-data doujinshi by ID.

		Notes
		-----
		Item-count dict fields are guaranteed to be sorted.

		Parameters
		----------
		doujinshi_id : int
			ID of the doujinshi to retrieve.

		Returns
		-------
		doujinshi : dict or None
			A dict if found, otherwise None, containing these fields:
				Single-valued:
					'id', 'path', 'note',
					'full_name', 'full_name_original',
					'pretty_name', 'pretty_name_original',
				`Item`-count dict: 'parodies', 'characters', 'tags', 'artists', 'groups', 'languages',
				List-like: 'pages'.
		"""
		with self.session() as session:
			# No try/except needed, route handler should catch non-int doujinshi_id values.
			statement = select(Doujinshi).where(Doujinshi.id == doujinshi_id)
			doujinshi = session.scalar(statement)
			if not doujinshi:
				self.logger.not_found(f"doujinshi #{doujinshi_id}", stacklevel=1)
				return None

			d_dict = {
				"id": doujinshi.id,
				"full_name": doujinshi.full_name,
				"full_name_original": doujinshi.full_name_original,
				"pretty_name": doujinshi.pretty_name,
				"pretty_name_original": doujinshi.pretty_name_original,
				"path": doujinshi.path,
				"note": doujinshi.note
			}
			d_dict["pages"] = list(session.scalars(
				select(Page.filename)
				.where(Page.doujinshi_id == doujinshi_id)
				.order_by(Page.order_number.asc())
			))

			relationships = {
				"parodies": (Parody, d_parody, d_parody.c.parody_id),
				"characters": (Character, d_character, d_character.c.character_id),
				"tags": (Tag, d_tag, d_tag.c.tag_id),
				"artists": (Artist, d_artist, d_artist.c.artist_id),
				"groups": (Group, d_circle, d_circle.c.circle_id),
				"languages": (Language, d_language, d_language.c.language_id)
			}

			for field, (model, m2m_table, m2m_table_c_model_id) in relationships.items():
				d_dict[field] = {}

				# Subquery to select IDs.
				subq = (
					select(m2m_table_c_model_id)
					.where(m2m_table.c.doujinshi_id == doujinshi_id)
				)
				statement = (
					select(model.name, model.count)
					.where(model.id.in_(subq))
					.order_by(model.name)
				)
				retrieved_item_and_count = session.execute(statement).all()

				for item, count in retrieved_item_and_count:
					d_dict[field][item] = count

			return d_dict


	def get_doujinshi_in_page(self, page_size, page_number, n_doujinshi=None):
		"""Retrieve a paginated list of latest (by ID) partial-data doujinshi.

		Parameters
		----------
		page_size : int
			Number of doujinshi per page.

		page_number : int
			Page number to retrieve (1-based).

		n_doujinshi : int, default=None
			Total number of doujinshi.
			If not None, this value is used to optimize retrieval speed of later pages.

		Returns
		-------
			doujinshi_list : list of dict
				Each dict contains: 'id', 'full_name', 'path', 'cover_filename' and 'language_id'.
				'language_id' is its 'primary' language ID, mapping is as follows:
					None-no language,
					1-english,
					2-japanese,
					3-chinese,
					4-textless.
		"""
		# NOTE: refer to self.create_database() to see the 'language_id' priority mapping.
		if page_number < 1:
			return []

		doujinshi_list = []

		# Calculate offset and limit.
		d_id_desc_order = True
		offset = (page_number - 1) * page_size
		limit = page_size

		if n_doujinshi:
			max_page_number = math.ceil(n_doujinshi / page_size)
			last_page_size = n_doujinshi % page_size or page_size

			# Page is in second half.
			if page_number > math.ceil(max_page_number / 2):
				d_id_desc_order = False

				# Special case: last page.
				if page_number == max_page_number:
					limit = last_page_size
					offset = (max_page_number - page_number) * page_size
				else:
					offset = last_page_size + (max_page_number - page_number - 1) * page_size

		with self.session() as session:
			# No try/except needed, same as in get_doujinshi.
			subq_cover_filename = (
				select(Page.filename)
				.where(Page.doujinshi_id == Doujinshi.id)
				.where(Page.order_number == 1)
				.scalar_subquery()
			)
			# Only retrieve language id since
			# it's faster and the set of languages is unlikely to change.
			subq_lang_id = (
				select(func.min(d_language.c.language_id))
				.where(d_language.c.doujinshi_id == Doujinshi.id)
				.scalar_subquery()
			)

			# Retrieve then reverse result in python if needed.
			order = Doujinshi.id.desc() if d_id_desc_order else Doujinshi.id.asc()
			statement = (
				select(
					Doujinshi.id, Doujinshi.full_name, Doujinshi.path,
					subq_cover_filename.label("cover_filename"),
					subq_lang_id.label("language_id")
				)
				.order_by(order)
				.limit(limit)
				.offset(offset)
			)
			# Generated sql:
			# 		SELECT
			# 			doujinshi.id, doujinshi.full_name, doujinshi.path,
			# 			(
			# 				SELECT page.filename
			# 				FROM page
			# 				WHERE page.doujinshi_id = doujinshi.id AND page.order_number = 1
			# 			) AS cover_filename,
			# 			(
			# 				SELECT min(doujinshi_language.language_id) AS min_1
			# 				FROM doujinshi_language
			# 				WHERE doujinshi_language.doujinshi_id = doujinshi.id
			# 			) AS language_id
			# 		FROM doujinshi
			# 		ORDER BY doujinshi.id DESC
			# 		LIMIT ? OFFSET ?
			# This is at least 10x faster than using join.
			result = session.execute(statement).all()
			result = result if d_id_desc_order else reversed(result)

			# Retrieve then reverse result in db instead of in python.
			# Performance is nearly identical to the above approach.
			# Keeping it here as a reference for potential future use.
			# if d_id_desc_order:
			# 	statement = select(Doujinshi.id, Doujinshi.full_name, Doujinshi.path,subq_cover_filename.label("cover_filename"),subq_lang_id.label("language_id")).order_by(Doujinshi.id.desc()).limit(limit).offset(offset)
			# else:
			# 	statement = (select(select(Doujinshi.id,Doujinshi.full_name,Doujinshi.path,subq_cover_filename.label("cover_filename"),subq_lang_id.label("language_id")).order_by(Doujinshi.id.asc()).limit(limit).offset(offset).subquery()).order_by(inner.c.id.desc()))
			# result = session.execute(statement).all()

			for doujinshi_id, full_name, path, cover_filename, language_id in result:
				doujinshi_list.append({
					"id": doujinshi_id,
					"full_name": full_name,
					"path": path,
					"cover_filename": cover_filename,
					"language_id": language_id
				})

			return doujinshi_list


	def get_doujinshi_in_range(self, id_start=1, id_end=None):
		"""Retrieve all doujinshi within an ID range.

		Use this when exporting data.

		Notes
		-----
		Doujinshi's list-like fields (except pages) may be in an arbitrary order.

		Parameters
		----------
		id_start : int, default=1
			Start ID of the range (inclusive).

		id_end : int, default=None
			End ID of the range (inclusive). If None, retrieves all doujinshi from *id_start*.

		Returns
		-------
		doujinshi_list : list of dict
			Each dict is the same as one returned by get_doujinshi().
		"""
		result = {}

		with self.session() as session:
			# Cache first.
			# Should use this with other get_doujinshi methods?
			item_id_to_name = self.get_item_id_to_name_mapping(session)

			single_value_fields = [
				"id", "path", "note",
				"full_name", "pretty_name", "full_name_original", "pretty_name_original"
			]
			list_like_fields = [
				("parodies", d_parody, d_parody.c.parody_id),
				("characters", d_character, d_character.c.character_id),
				("tags", d_tag, d_tag.c.tag_id),
				("artists", d_artist, d_artist.c.artist_id),
				("groups", d_circle, d_circle.c.circle_id),
				("languages", d_language, d_language.c.language_id)
			]

			statement = select(Doujinshi).where(Doujinshi.id >= id_start)
			if id_end:
				statement = statement.where(Doujinshi.id <= id_end)

			retrieved_bare_doujinshi_list = session.scalars(statement)

			# Get single value fields.
			for doujinshi in retrieved_bare_doujinshi_list:
				result[doujinshi.id] = {attr: getattr(doujinshi, attr) for attr in single_value_fields}

				for list_like_field, _, _ in list_like_fields:
					result[doujinshi.id][list_like_field] = []

			doujinshi_ids = list(result.keys())

			# Get list-like field item ids.
			for field, m2m_table, m2m_table_item_id in list_like_fields:
				statement = (
					select(m2m_table.c.doujinshi_id, m2m_table_item_id)
					.where(m2m_table.c.doujinshi_id.in_(doujinshi_ids))
				)
				retrieved_item_ids = session.execute(statement).all()
				
				for doujinshi_id, item_id in retrieved_item_ids:
					result[doujinshi_id][field].append(item_id_to_name[field][item_id])

			# Get pages.
			for doujinshi_id in doujinshi_ids:
				statement = (
					select(Page.filename)
					.where(Page.doujinshi_id == doujinshi_id)
					.order_by(Page.order_number.asc())
				)
				result[doujinshi_id]["pages"] = [filename for filename in session.scalars(statement)]

			return list(result.values())


	def get_item_id_to_name_mapping(self, session):
		"""As the name suggests.

		Returns
		-------
		mapping : dict[str, dict[int, str]]
			A dict mapping each item type to a dict mapping item IDs to names.
		"""
		items = [
			("parodies", Parody),
			("characters", Character),
			("tags", Tag),
			("artists", Artist),
			("groups", Group),
			("languages", Language)
		]
		mapping = {item: {} for item, _ in items}

		for item, model in items:
			for item_id, item_name in session.execute(select(model.id, model.name)).all():
				mapping[item][item_id] = item_name

		return mapping


	def _update_count(self, model, model_id_column, d_id_column, session):
		"""Update the 'count' column of a given `item`.

		Parameters
		----------
		model : Parody|Character|Tag|Artist|Group|Language
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
		model : Parody|Character|Tag|Artist|Group|Language
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
			DatabaseStatus.EXCEPTION - error occurred.
		"""
		if session:
			self._update_count(model, model_id_column, d_id_column, session)
		else:
			with self.session() as session:
				try:
					self._update_count(model, model_id_column, d_id_column, session)
					session.commit()
					return DatabaseStatus.OK
				except Exception as e:
					self.logger.exception(e, stacklevel=2)
					return DatabaseStatus.EXCEPTION


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
			DatabaseStatus.EXCEPTION - error occurred.
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
					self.logger.exception(e, stacklevel=1)
					return DatabaseStatus.EXCEPTION


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
	# TODO: add db schema description