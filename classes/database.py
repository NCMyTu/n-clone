from pathlib import Path
import sqlite3
from enum import Enum, auto
from doujinshi import Doujinshi

# conn.rollback() calls might be excessive, but if you can, be explicit as much as possible.
class Database_Status(Enum):
	OK = auto()
	FATAL = auto()
	NON_FATAL = auto()
	NON_FATAL_ITEM_NOT_FOUND = auto()
	NON_FATAL_NOT_LINKED = auto()
	NON_FATAL_DOUJINSHI_NOT_FOUND = auto()

class Database:
	def __init__(self, path):
		self.path = path


	def set_path(self, path):
		self.path = path


	def create_database(self):
		if Path(self.path).is_file():
			print("Database path already exists. Database creation skipped.")
			return Database_Status.NON_FATAL

		with sqlite3.connect(Path(self.path)) as conn:
			cursor = conn.cursor()
			cursor.execute("PRAGMA foreign_keys = ON;")

			cursor.executescript("""
				CREATE TABLE IF NOT EXISTS doujinshi (
					id INTEGER PRIMARY KEY,

					full_name TEXT NOT NULL CHECK(full_name <> ''),
					full_name_original TEXT,
					bold_name TEXT,
					bold_name_original TEXT,

					path TEXT NOT NULL UNIQUE CHECK(path <> ''),
					cover_page_id INTEGER,

					added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
					note TEXT,

					FOREIGN KEY (cover_page_id) REFERENCES page(id) ON DELETE SET NULL
				);

				CREATE TABLE IF NOT EXISTS parody (
					id INTEGER PRIMARY KEY,
					name TEXT NOT NULL UNIQUE CHECK(name <> '')
				);

				CREATE TABLE IF NOT EXISTS character (
					id INTEGER PRIMARY KEY,
					name TEXT NOT NULL UNIQUE CHECK(name <> '')
				);

				CREATE TABLE IF NOT EXISTS tag (
					id INTEGER PRIMARY KEY,
					name TEXT NOT NULL UNIQUE CHECK(name <> '')
				);

				CREATE TABLE IF NOT EXISTS artist (
					id INTEGER PRIMARY KEY,
					name TEXT NOT NULL UNIQUE CHECK(name <> '')
				);

				CREATE TABLE IF NOT EXISTS circle ( -- A.k.a group
					id INTEGER PRIMARY KEY,
					name TEXT NOT NULL UNIQUE CHECK(name <> '')
				);

				CREATE TABLE IF NOT EXISTS language (
					id INTEGER PRIMARY KEY,
					name TEXT NOT NULL UNIQUE CHECK(name <> '')
				);
				
				CREATE TABLE IF NOT EXISTS page (
					id INTEGER PRIMARY KEY,
					file_name TEXT NOT NULL CHECK(file_name <> ''),
					order_number INTEGER NOT NULL CHECK(order_number > 0),
					doujinshi_id INTEGER,
					FOREIGN KEY (doujinshi_id) REFERENCES doujinshi(id) ON DELETE CASCADE,
					UNIQUE (doujinshi_id, order_number)
				);

				-- many-to-many relationships
				CREATE TABLE IF NOT EXISTS doujinshi_parody (
					doujinshi_id INTEGER,
					parody_id INTEGER,
					PRIMARY KEY (doujinshi_id, parody_id),
					FOREIGN KEY (doujinshi_id) REFERENCES doujinshi(id) ON DELETE CASCADE,
					FOREIGN KEY (parody_id) REFERENCES parody(id) ON DELETE CASCADE
				);

				CREATE TABLE IF NOT EXISTS doujinshi_character (
					doujinshi_id INTEGER,
					character_id INTEGER,
					PRIMARY KEY (doujinshi_id, character_id),
					FOREIGN KEY (doujinshi_id) REFERENCES doujinshi(id) ON DELETE CASCADE,
					FOREIGN KEY (character_id) REFERENCES character(id) ON DELETE CASCADE
				);

				CREATE TABLE IF NOT EXISTS doujinshi_tag (
					doujinshi_id INTEGER,
					tag_id INTEGER,
					PRIMARY KEY (doujinshi_id, tag_id),
					FOREIGN KEY (doujinshi_id) REFERENCES doujinshi(id) ON DELETE CASCADE,
					FOREIGN KEY (tag_id) REFERENCES tag(id) ON DELETE CASCADE
				);

				CREATE TABLE IF NOT EXISTS doujinshi_artist (
					doujinshi_id INTEGER,
					artist_id INTEGER,
					PRIMARY KEY (doujinshi_id, artist_id),
					FOREIGN KEY (doujinshi_id) REFERENCES doujinshi(id) ON DELETE CASCADE,
					FOREIGN KEY (artist_id) REFERENCES artist(id) ON DELETE CASCADE
				);

				CREATE TABLE IF NOT EXISTS doujinshi_circle (
					doujinshi_id INTEGER,
					circle_id INTEGER,
					PRIMARY KEY (doujinshi_id, circle_id),
					FOREIGN KEY (doujinshi_id) REFERENCES doujinshi(id) ON DELETE CASCADE,
					FOREIGN KEY (circle_id) REFERENCES circle(id) ON DELETE CASCADE
				);

				CREATE TABLE IF NOT EXISTS doujinshi_language (
					doujinshi_id INTEGER,
					language_id INTEGER,
					PRIMARY KEY (doujinshi_id, language_id),
					FOREIGN KEY (doujinshi_id) REFERENCES doujinshi(id) ON DELETE CASCADE,
					FOREIGN KEY (language_id) REFERENCES language(id) ON DELETE CASCADE
				);

				INSERT INTO language (name) VALUES ('english');
				INSERT INTO language (name) VALUES ('japanese');
				INSERT INTO language (name) VALUES ('chinese');
				INSERT INTO language (name) VALUES ('textless');
			""")

			print(f"Database created at {Path(self.path).as_posix()}")

			conn.commit()

			return Database_Status.OK


	def _execute_insert(self, conn, cursor, table, column, value):
		# Helper function to insert a value into a single-column table
		# IMPORTANT: there is no commit and rollback in this function,
		#            only handle them at the top most function
		# IMPORTANT: remember to enable foreign_keys
		if not value:
			print(f"INSERT WHAT {table.upper()}?")
			return Database_Status.FATAL

		try:
			# Check if the record already exists
			cursor.execute(
				f"SELECT id FROM {table} WHERE {column} = ?;", 
				(value,)
			)
			row = cursor.fetchone()

			if row:
				print(f"Duplicate entry in table [{table}]: {value}. Insertion skipped")
				return Database_Status.OK

			# If not exists, insert
			cursor.execute(
				f"INSERT INTO {table} ({column}) VALUES (?);", 
				(value,)
			)

			print(f"Inserted into table [{table}]: {value}")
			return Database_Status.OK
		except sqlite3.Error as e:
			print(f"FATAL: Cannot insert into [{table}]. ERROR: {e}")
			return Database_Status.FATAL
		except Exception as e:
			# Who knows what can happens
			print(f"Unexpected exception from function [_execute_insert]. ERROR: {e}")
			print(f"\ttable: {table}, column: {column}, value: {value}")
			return Database_Status.FATAL


	def _insert_parody(self, conn, cursor, parody):
		return self._execute_insert(conn, cursor, table="parody", column="name", value=parody)


	def _insert_character(self, conn, cursor, character):
		return self._execute_insert(conn, cursor, table="character", column="name", value=character)


	def _insert_tag(self, conn, cursor, tag):
		return self._execute_insert(conn, cursor, table="tag", column="name", value=tag)


	def _insert_artist(self, conn, cursor, artist):
		return self._execute_insert(conn, cursor, table="artist", column="name", value=artist)


	def _insert_group(self, conn, cursor, group):
		return self._execute_insert(conn, cursor, table="circle", column="name", value=group)


	def _insert_language(self, conn, cursor, language):
		return self._execute_insert(conn, cursor, table="language", column="name", value=language)


	def _insert_page(self, conn, cursor, doujinshi_id, page_file_name, order_number):
		try:
			cursor.execute(
				"INSERT INTO page (doujinshi_id, file_name, order_number) VALUES (?, ?, ?);",
				(doujinshi_id, page_file_name, order_number)
			)
			print(f"Inserted page #{order_number},  for doujinshi #{doujinshi_id}")
			return Database_Status.OK
		except sqlite3.IntegrityError as e:
			conn.rollback()
			print(f"Integrity error while inserting page #{order_number} for doujinshi #{doujinshi_id}. ERROR: {e}")
			return Database_Status.FATAL
		except Exception as e:
			conn.rollback()
			print(f"Unexpected exception while inserting page for doujinshi #{doujinshi_id}. ERROR: {e}")
			return Database_Status.FATAL


	def execute_insert(self, table, column, value):
		if not value:
			print(f"INSERT WHAT {table.upper()}?")
			return Database_Status.FATAL

		with sqlite3.connect(Path(self.path)) as conn:
			cursor = conn.cursor()
			cursor.execute("PRAGMA foreign_keys = ON;")

			try:
				# Check if the record already exists
				cursor.execute(
					f"SELECT id FROM {table} WHERE {column} = ?;",
					(value,)
				)
				row = cursor.fetchone()

				if row:
					print(f"Duplicate entry in table [{table}]: {value}. Insertion skipped")
					return Database_Status.OK

				# If not exists, insert
				cursor.execute(
					f"INSERT INTO {table} ({column}) VALUES (?);",
					(value,)
				)

				conn.commit()
				print(f"Inserted into table [{table}]: {value}")
				return Database_Status.OK
			except sqlite3.Error as e:
				conn.rollback()
				print(f"FATAL: Cannot insert into [{table}]. ERROR: {e}")
				return Database_Status.FATAL
			except Exception as e:
				# Who knows what can happens
				conn.rollback()
				print(f"Unexpected exception from function [execute_insert]. ERROR: {e}")
				print(f"\ttable: {table}, column: {column}, value: {value}")
				return Database_Status.FATAL


	def insert_parody(self, parody):
		return self.execute_insert(table="parody", column="name", value=parody)


	def insert_character(self, character):
		return self.execute_insert(table="character", column="name", value=character)


	def insert_tag(self, tag):
		return self.execute_insert(table="tag", column="name", value=tag)


	def insert_artist(self, artist):
		return self.execute_insert(table="artist", column="name", value=artist)


	def insert_group(self, group):
		return self.execute_insert(table="circle", column="name", value=group)


	def insert_language(self, language):
		return self.execute_insert(table="language", column="name", value=language)


	def _link_doujinshi_with_many(self, conn, cursor, join_table, table_to_link, doujinshi_id, value):
		# IMPORTANT: there is no commit and rollback in this function,
		#            only handle them at the top most function
		# IMPORTANT: remember to enable foreign_keys
		cursor.execute(
			f"SELECT id FROM {table_to_link} WHERE name = ?",
			(value,)
		)
		row = cursor.fetchone()

		if not row:
			print(f"Table [{table_to_link}] has no entry with name: {value}.", end=" ")
			print(f"Linking [doujinshi] #{doujinshi_id} with {table_to_link} skipped.")
			return Database_Status.FATAL

		table_to_link_id = row[0]

		try:
			cursor.execute(
				f"INSERT INTO {join_table} (doujinshi_id, {table_to_link}_id) VALUES(?, ?);",
				(doujinshi_id, table_to_link_id)
			)
			print(f"Link into [doujinshi] #{doujinshi_id} with [{table_to_link}] {value}.")
			return Database_Status.OK
		except sqlite3.IntegrityError as e:
			print(f"ERROR: {e}.", end=" ")
			print(f"Duplicate entry in table [{join_table}]:", end=" ")
			print(f"[doujinshi] #{doujinshi_id} and [{table_to_link}] {value}", end=" ")
			print("Insertion skipped.")
			return Database_Status.NON_FATAL
		except Exception as e:
			# Who knows what can happens
			print(f"Unexpected exception from function [_link_doujinshi_with_many]. ERROR: {e}")
			return Database_Status.FATAL


	def _link_doujinshi_with_parody(self, conn, cursor, doujinshi_id, parody):
		return self._link_doujinshi_with_many(conn, cursor, "doujinshi_parody", "parody", doujinshi_id, parody)


	def _link_doujinshi_with_character(self, conn, cursor, doujinshi_id, character):
		return self._link_doujinshi_with_many(conn, cursor, "doujinshi_character", "character", doujinshi_id, character)


	def _link_doujinshi_with_tag(self, conn, cursor, doujinshi_id, tag):
		return self._link_doujinshi_with_many(conn, cursor, "doujinshi_tag", "tag", doujinshi_id, tag)


	def _link_doujinshi_with_artist(self, conn, cursor, doujinshi_id, artist):
		return self._link_doujinshi_with_many(conn, cursor, "doujinshi_artist", "artist", doujinshi_id, artist)


	def _link_doujinshi_with_group(self, conn, cursor, doujinshi_id, group):
		return self._link_doujinshi_with_many(conn, cursor, "doujinshi_circle", "circle", doujinshi_id, group)


	def _link_doujinshi_with_language(self, conn, cursor, doujinshi_id, language):
		return self._link_doujinshi_with_many(conn, cursor, "doujinshi_language", "language", doujinshi_id, language)


	def link_doujinshi_with_many(self, join_table, table_to_link, doujinshi_id, value):
		with sqlite3.connect(Path(self.path)) as conn:
			cursor = conn.cursor()
			cursor.execute("PRAGMA foreign_keys = ON;")

			return self._link_doujinshi_with_many(conn, cursor, join_table, table_to_link, doujinshi_id, value)


	def add_parody_to_doujinshi(self, doujinshi_id, parody):
		return self.link_doujinshi_with_many("doujinshi_parody", "parody", doujinshi_id, parody)


	def add_character_to_doujinshi(self, doujinshi_id, character):
		return self.link_doujinshi_with_many("doujinshi_character", "character", doujinshi_id, character)


	def add_tag_to_doujinshi(self, doujinshi_id, tag):
		return self.link_doujinshi_with_many("doujinshi_tag", "tag", doujinshi_id, tag)


	def add_artist_to_doujinshi(self, doujinshi_id, artist):
		return self.link_doujinshi_with_many("doujinshi_artist", "artist", doujinshi_id, artist)


	def add_group_to_doujinshi(self, doujinshi_id, group):
		return self.link_doujinshi_with_many("doujinshi_circle", "circle", doujinshi_id, group)


	def add_language_to_doujinshi(self, doujinshi_id, language):
		return self.link_doujinshi_with_many("doujinshi_language", "language", doujinshi_id, language)


	def add_pages_to_doujinshi(self, doujinshi_id, page_order_list):
		if not page_order_list:
			print(f"INSERT WHAT PAGES?")
			return Database_Status.NON_FATAL

		with sqlite3.connect(Path(self.path)) as conn:
			cursor = conn.cursor()
			cursor.execute("PRAGMA foreign_keys = ON;")

			try:
				# Verify doujinshi exists
				cursor.execute(
					"SELECT 1 FROM doujinshi WHERE id = ? LIMIT 1;",
					(doujinshi_id,)
				)
				if not cursor.fetchone():
					print(f"Doujinshi #{doujinshi_id} not found. Cannot add pages.")
					return Database_Status.NON_FATAL_DOUJINSHI_NOT_FOUND

				# Remove existing pages first
				cursor.execute(
					"DELETE FROM page WHERE doujinshi_id = ?;",
					(doujinshi_id,)
				)

				for order_number, file_name in enumerate(page_order_list, start=1):
					if not file_name:
						print(f"Empty file name for page #{order_number} of doujinshi #{doujinshi_id}.")
						conn.rollback()
						return Database_Status.FATAL

					cursor.execute(
						"INSERT INTO page (doujinshi_id, file_name, order_number) VALUES (?, ?, ?);",
						(doujinshi_id, file_name, order_number)
					)
					print(f"Inserted page #{order_number} ({file_name}) for doujinshi #{doujinshi_id}")

				conn.commit()
				return Database_Status.OK
			except sqlite3.IntegrityError as e:
				conn.rollback()
				print(f"Integrity error while inserting pages for doujinshi #{doujinshi_id}. ERROR: {e}")
				return Database_Status.NON_FATAL
			except Exception as e:
				conn.rollback()
				print(f"Unexpected exception from function [add_pages_to_doujinshi]. ERROR: {e}")
				return Database_Status.FATAL


	def insert_doujinshi(self, doujinshi):
		if not doujinshi.strict_mode():
			return Database_Status.NON_FATAL

		def insert_then_link(items, insert_fn, link_fn):
			for item in items:
				if insert_fn(conn, cursor, item) == Database_Status.FATAL \
					or link_fn(conn, cursor, doujinshi.id, item) == Database_Status.FATAL:
					return False
			return True

		# utterly shitty spaghetti pepperoni ahead
		with sqlite3.connect(Path(self.path)) as conn:
			cursor = conn.cursor()
			cursor.execute("PRAGMA foreign_keys = ON;")

			try:
				cursor.execute(
					"SELECT 1 FROM doujinshi WHERE id = ? LIMIT 1;", 
					(doujinshi.id,)
				)
				if cursor.fetchone() is not None:
					print(f"Doujinshi id {doujinshi.id} already exists. Insertion skipped.")
					return Database_Status.NON_FATAL

				insert_query = """
					INSERT INTO doujinshi (
						id, 
						full_name, full_name_original,
						bold_name, bold_name_original, 
						path,
						note
					) VALUES (?, ?, ?, ?, ?, ?, ?);
				"""
				values = (
					doujinshi.id,
					doujinshi.full_name, doujinshi.full_name_original,
					doujinshi.bold_name, doujinshi.bold_name_original,
					doujinshi.path,
					doujinshi.note
				)

				cursor.execute(insert_query, values)

				# atomic, baby
				relations = [
					(doujinshi.parodies,    self._insert_parody,    self._link_doujinshi_with_parody),
					(doujinshi.characters,  self._insert_character, self._link_doujinshi_with_character),
					(doujinshi.tags,        self._insert_tag,       self._link_doujinshi_with_tag),
					(doujinshi.artists,     self._insert_artist,    self._link_doujinshi_with_artist),
					(doujinshi.groups,      self._insert_group,     self._link_doujinshi_with_group),
					(doujinshi.languages,   self._insert_language,  self._link_doujinshi_with_language)
				]

				# Run through each category and stop on FATAL
				for items, insert_fn, link_fn in relations:
					if not insert_then_link(items, insert_fn, link_fn):
						conn.rollback()
						return Database_Status.FATAL

				# Insert pages
				page_cover_id = None
				for order_number, page_file_name in enumerate(doujinshi.page_order, start=1):
					status = self._insert_page(conn, cursor, doujinshi.id, page_file_name, order_number)
					if status == Database_Status.FATAL:
						conn.rollback()
						return Database_Status.FATAL

					# Get the ID of the first inserted page (cover)
					if order_number == 1:
						cursor.execute(
							"SELECT id FROM page WHERE doujinshi_id = ? AND order_number = 1 LIMIT 1;",
							(doujinshi.id,)
						)
						row = cursor.fetchone()
						if row:
							page_cover_id = row[0]

				# Set cover_page_id if found
				if page_cover_id is not None:
					cursor.execute(
						"UPDATE doujinshi SET cover_page_id = ? WHERE id = ?;",
						(page_cover_id, doujinshi.id)
					)
					print(f"Set cover_page_id = {page_cover_id} for doujinshi #{doujinshi.id}")

				conn.commit()
				return Database_Status.OK
			except sqlite3.IntegrityError as e:
				# extremely atomic, baby
				conn.rollback()
				print(f"Integrity error while inserting doujinshi #{doujinshi.id}. ERROR: {e}")
				return Database_Status.NON_FATAL
			except Exception as e:
				# a lot of atomic, baby
				conn.rollback()
				print(f"Unexpected exception from function [insert_doujinshi]. ERROR: {e}")
				return Database_Status.FATAL
		# connection is still opening although using context manager. But it should be destroyed here. 
		# Dumb design.


	def remove_item_from_doujinshi_by_name(self, doujinshi_id, link_table, 
		item_table, item_name, func_name="remove_item_from_doujinshi_by_name"):
		# Remove a linked item from a doujinshi by the item's name.
		with sqlite3.connect(Path(self.path)) as conn:
			cursor = conn.cursor()
			cursor.execute("PRAGMA foreign_keys = ON;")
			
			try:
				# Get the item's ID
				cursor.execute(
					f"SELECT id FROM {item_table} WHERE name = ?;",
					(item_name,)
				)
				row = cursor.fetchone()

				if not row:
					print(f"Attempted to remove [{item_table}] {item_name} from doujinshi #{doujinshi_id} ", end="")
					print(f"but it is not in table [{item_table}].")
					return Database_Status.NON_FATAL_ITEM_NOT_FOUND
				item_id = row[0]

				# Step 2: Remove the link
				cursor.execute(
					f"DELETE FROM {link_table} WHERE doujinshi_id = ? AND {item_table}_id = ?;",
					(doujinshi_id, item_id)
				)
				conn.commit()

				if cursor.rowcount == 0:
					print(f"Attempted to remove [{item_table}] {item_name} from doujinshi #{doujinshi_id} ", end="")
					print(f"but they are not linked together.")
					return Database_Status.NON_FATAL_NOT_LINKED

				print(f"Removed [{item_table}] {item_name} from doujinshi #{doujinshi_id}.")
				return Database_Status.OK

			except sqlite3.Error as e:
				conn.rollback()
				print(f"FATAL: Could not remove [{item_table}] {item_name} from doujinshi #{doujinshi_id}. ERROR: {e}")
				return Database_Status.FATAL
			except Exception as e:
				conn.rollback()
				print(f"Unexpected exception from function [{func_name}]. ERROR: {e}")
				return Database_Status.FATAL


	def remove_parody_from_doujinshi(self, doujinshi_id, parody):
		return self.remove_item_from_doujinshi_by_name(
			doujinshi_id, "doujinshi_parody", "parody", parody, "remove_parody_from_doujinshi"
		)


	def remove_character_from_doujinshi(self, doujinshi_id, character):
		return self.remove_item_from_doujinshi_by_name(
			doujinshi_id, "doujinshi_character", "character", character, "remove_character_from_doujinshi"
		)


	def remove_tag_from_doujinshi(self, doujinshi_id, tag):
		return self.remove_item_from_doujinshi_by_name(
			doujinshi_id, "doujinshi_tag", "tag", tag, "remove_tag_from_doujinshi"
		)


	def remove_artist_from_doujinshi(self, doujinshi_id, artist):
		return self.remove_item_from_doujinshi_by_name(
			doujinshi_id, "doujinshi_artist", "artist", artist, "remove_artist_from_doujinshi"
		)


	def remove_group_from_doujinshi(self, doujinshi_id, group):
		return self.remove_item_from_doujinshi_by_name(
			doujinshi_id, "doujinshi_circle", "circle", group, "remove_group_from_doujinshi"
		)


	def remove_language_from_doujinshi(self, doujinshi_id, language):
		return self.remove_item_from_doujinshi_by_name(
			doujinshi_id, "doujinshi_language", "language", language, "remove_language_from_doujinshi"
		)


	def remove_all_pages_from_doujinshi(self, doujinshi_id):
		with sqlite3.connect(Path(self.path)) as conn:
			cursor = conn.cursor()
			cursor.execute("PRAGMA foreign_keys = ON;")

			try:
				# Verify doujinshi exists
				cursor.execute(
					"SELECT 1 FROM doujinshi WHERE id = ? LIMIT 1;",
					(doujinshi_id,)
				)
				if not cursor.fetchone():
					print(f"Doujinshi #{doujinshi_id} not found. Cannot add pages.")
					return Database_Status.NON_FATAL_DOUJINSHI_NOT_FOUND

				# Remove existing pages first
				cursor.execute(
					"DELETE FROM page WHERE doujinshi_id = ?;",
					(doujinshi_id,)
				)
				print(f"Removed all pages for doujinshi #{doujinshi_id}.")

				conn.commit()
				return Database_Status.OK
			except sqlite3.IntegrityError as e:
				conn.rollback()
				print(f"Integrity error while remove all pages for doujinshi #{doujinshi_id}. ERROR: {e}")
				return Database_Status.NON_FATAL
			except Exception as e:
				conn.rollback()
				print(f"Unexpected exception from function [remove_all_pages_from_doujinshi]. ERROR: {e}")
				return Database_Status.FATAL


	def remove_doujinshi(self, doujinshi_id):
		confirm = input("You want to REMOVE a doujinshi. Do you want to continue? (Y/n)\n\t>>> ")
		if confirm != "Y":
			return Database_Status.NON_FATAL

		with sqlite3.connect(Path(self.path)) as conn:
			cursor = conn.cursor()
			cursor.execute("PRAGMA foreign_keys = ON;")
			
			try:
				cursor.execute(
					"DELETE FROM doujinshi WHERE id = ?;",
					(doujinshi_id,)
				)
				conn.commit()

				if cursor.rowcount == 0:
					print(f"Attempting to remove doujinshi #{doujinshi_id} but it does not exist.")
					return Database_Status.NON_FATAL_DOUJINSHI_NOT_FOUND

				print(f"Removed doujinshi #{doujinshi_id}.")
				return Database_Status.OK
			except sqlite3.Error as e:
				conn.rollback()
				print(f"Integrity error while removing all pages from doujinshi #{doujinshi_id}. ERROR: {e}")
				return Database_Status.FATAL
			except Exception as e:
				conn.rollback()
				print(f"Unexpected exception from function [remove_doujinshi]. ERROR: {e}")
				return Database_Status.FATAL


	def update_note_of_doujinshi(self, doujinshi_id, note):
		with sqlite3.connect(Path(self.path)) as conn:
			cursor = conn.cursor()
			cursor.execute("PRAGMA foreign_keys = ON;")

			try:
				cursor.execute(
					"UPDATE doujinshi SET note = ? WHERE id = ?",
					(note, doujinshi_id)
				)

				if cursor.rowcount > 0:
					conn.commit()
					return Database_Status.OK

				return Database_Status.NON_FATAL_DOUJINSHI_NOT_FOUND

			except sqlite3.Error as e:
				conn.rollback()
				print(f"SQLite error occurred in update_note_of_doujinshi. ERROR: {e}")
				return Database_Status.FATAL
			except Exception as e:
				conn.rollback()
				print(f"Unexpected error from update_note_of_doujinshi. ERROR: {e}")
				return Database_Status.FATAL


	def get_doujinshi(self, doujinshi_id, partial=False):
		def get_related(table, join_table):
			cursor.execute(f"""
				SELECT t.name
				FROM {table} t
				JOIN {join_table} jt ON jt.{table}_id = t.id
				WHERE jt.doujinshi_id = ?
				ORDER BY t.name;
			""", (doujinshi_id,))
			return [r[0] for r in cursor.fetchall()]

		with sqlite3.connect(Path(self.path)) as conn:
			cursor = conn.cursor()
			cursor.execute("PRAGMA foreign_keys = ON;")

			cursor.execute(
				"""
				SELECT
					path,
					full_name, bold_name,
					full_name_original, bold_name_original,
					cover_page_id,
					added_at, note
				FROM doujinshi
				WHERE id = ?;
				""",
				(doujinshi_id,)
			)
			row = cursor.fetchone()

			if not row:
				return None

			data = {
				"path": row[0],
				"full_name": row[1],
				"bold_name": row[2],
				"full_name_original": row[3],
				"bold_name_original": row[4],
				"cover_page_file_name": None,
				"added_at": row[6],
				"note": row[7],
			}

			if row[5] is not None:  # cover_page_id
				cursor.execute(
					"SELECT file_name FROM page WHERE id = ? LIMIT 1;",
					(row[5],)
				)
				cover_row = cursor.fetchone()
				data["cover_page_file_name"] = cover_row[0] if cover_row else None

			data["languages"]  = get_related("language", "doujinshi_language")

			if partial:
				return Doujinshi().from_partial_data(
					doujinshi_id,
					data["path"],
					data["full_name"],
					data["cover_page_file_name"],
					data["languages"]
				)

			data["parodies"]   = get_related("parody", "doujinshi_parody")
			data["characters"] = get_related("character", "doujinshi_character")
			data["tags"]       = get_related("tag", "doujinshi_tag")
			data["artists"]    = get_related("artist", "doujinshi_artist")
			data["groups"]     = get_related("circle", "doujinshi_circle")

			cursor.execute(
				"SELECT file_name FROM page WHERE doujinshi_id = ? ORDER BY order_number;",
				(doujinshi_id,)
			)
			page_order = [r[0] for r in cursor.fetchall()]

			return Doujinshi().from_data(
				doujinshi_id, data["path"],
				data["full_name"], data["bold_name"],
				data["full_name_original"], data["bold_name_original"],
				data["cover_page_file_name"],
				data["parodies"], data["characters"], data["tags"],
				data["artists"], data["groups"],
				data["languages"],
				page_order, data["added_at"], data["note"]
			)


if __name__ == "__main__":
	db = Database(path="../../collection.db.sqlite")
	db.create_database()

	db.insert_parody("parody_dummy1")
	db.insert_character("character_dummy1")
	db.insert_tag("BB")
	db.insert_artist("artist_dummy")
	db.insert_group("group_dummy")
	db.insert_language("language_dummy")

	d = Doujinshi().load_from_json("../../doujin_data.json")
	d.print_info()

	is_fatal = db.insert_doujinshi(d)
	if is_fatal == Database_Status.FATAL:
		print("FATAL")
	elif is_fatal == Database_Status.NON_FATAL:
		print("Insertion denied.")
	else:
		print("Insertion succeeded.")

	# db.remove_doujinshi(123)
	d = db.get_doujinshi(123, True)
	if d:
		d.print_info()
	else:
		print("no doujinshi was found")
