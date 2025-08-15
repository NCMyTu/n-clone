from classes.database import Database, Database_Status
from classes.doujinshi import Doujinshi
from util import extract_all_numbers as numerically
from datetime import date, datetime
from pathlib import Path
import pytest


@pytest.fixture
def db(tmp_path):
	db_file = tmp_path / "db.sqlite"
	db = Database(path=db_file)
	status = db.create_database()
	assert status == Database_Status.OK
	return db


@pytest.fixture
def sample_data():
	Doujinshi.set_path_prefix("PREFIX")
	return {
		"doujinshi_id": 1,
		"path": "inter\\path",
		"full_name": "Test Doujinshi",
		"bold_name": "st Dou",
		"full_name_original": "元の名前", # Must be japanese
		"bold_name_original": "の名", # Must be japanese
		"note": "Test note",
		"parodies": ["parody_1", "parody_2", "parody_3", "parody_4"],
		"characters": ["character_1", "character_2", "character_3"],
		"tags": [f"tag_{i}" for i in range(15)],
		"artists": ["artist_1", "artist_2", "artist_3", "artist_4"],
		"groups": ["group_1"],
		"languages": ["english", "textless"],
		"_page_order": [f"1_{i}.jpg" for i in range(1, 31)],
		"added_at": None,
	}


@pytest.fixture
def sample_doujinshi(sample_data):
	return Doujinshi().from_data(**sample_data)


def test_insert_and_retrieve_doujinshi(db, sample_doujinshi):
	assert db.insert_doujinshi(sample_doujinshi.ready(), False) == Database_Status.OK
	assert db.insert_doujinshi(sample_doujinshi.ready(), False) == Database_Status.NON_FATAL_DUPLICATE

	d = db.get_doujinshi(sample_doujinshi.id, partial=False)

	assert d is not None
	assert d.id == sample_doujinshi.id
	assert d.full_name == sample_doujinshi.full_name
	assert d.bold_name == sample_doujinshi.bold_name
	assert d.full_name_original == sample_doujinshi.full_name_original
	assert d.bold_name_original == sample_doujinshi.bold_name_original
	assert d.path == Path(sample_doujinshi.path).as_posix()
	assert set(d.parodies) == set(sample_doujinshi.parodies)
	assert set(d.characters) == set(sample_doujinshi.characters)
	assert set(d.tags) == set(sample_doujinshi.tags)
	assert set(d.artists) == set(sample_doujinshi.artists)
	assert set(d.groups) == set(sample_doujinshi.groups)
	assert set(d.languages) == set(sample_doujinshi.languages)
	assert set(d._page_order) == set(sample_doujinshi._page_order)
	assert d.note == sample_doujinshi.note
	assert datetime.strptime(d.added_at, "%Y-%m-%d %H:%M:%S").date() == date.today()
	assert d.cover_path == sample_doujinshi.cover_path

	d = db.get_doujinshi(sample_doujinshi.id, partial=True)

	assert d is not None
	assert d.id == sample_doujinshi.id
	assert d.full_name == sample_doujinshi.full_name
	assert not d.bold_name
	assert not d.full_name_original
	assert not d.bold_name_original
	assert d.path == Path(sample_doujinshi.path).as_posix()
	assert not d.parodies
	assert not d.characters
	assert not d.tags
	assert not d.artists
	assert not  d.groups
	assert set(d.languages) == set(sample_doujinshi.languages)
	assert not d._page_order
	assert not d.note
	assert not d.added_at
	assert d.cover_path == sample_doujinshi.cover_path


@pytest.mark.parametrize("insert_method_name", [
	"insert_parody",
	"insert_character",
	"insert_tag",
	"insert_artist",
	"insert_group",
	"insert_language",
])
def test_insert_item(db, insert_method_name):
	def _test_insert_item(db, insert_method_name):
		method = getattr(db, insert_method_name)

		assert method("NEW_VALUE") == Database_Status.OK
		assert method("new value again") == Database_Status.OK
		assert method("パロディ") == Database_Status.OK

		assert method("NEW_VALUE") == Database_Status.NON_FATAL_DUPLICATE

		assert method("") == Database_Status.FATAL
		assert method(" ") == Database_Status.FATAL
		assert method("\n") == Database_Status.FATAL
		assert method("\t") == Database_Status.FATAL
		assert method(None) == Database_Status.FATAL
		assert method(123) == Database_Status.FATAL
		assert method(3.14159) == Database_Status.FATAL
		assert method(True) == Database_Status.FATAL
		assert method([]) == Database_Status.FATAL
		assert method({}) == Database_Status.FATAL
		assert method(()) == Database_Status.FATAL
		assert method(b"bytes") == Database_Status.FATAL

	_test_insert_item(db, insert_method_name)


@pytest.mark.parametrize("add_method_name, insert_method_name, properti", [ # "property" is reserved...
	("add_parody_to_doujinshi", "insert_parody", "parodies"),
	("add_character_to_doujinshi", "insert_character", "characters"),
	("add_tag_to_doujinshi", "insert_tag", "tags"),
	("add_artist_to_doujinshi", "insert_artist", "artists"),
	("add_group_to_doujinshi", "insert_group", "groups"),
	("add_language_to_doujinshi", "insert_language", "languages"),
])
def test_add_to_doujinshi(db, sample_doujinshi, add_method_name, insert_method_name, properti):
	assert db.insert_doujinshi(sample_doujinshi.ready(), user_prompt=False) == Database_Status.OK

	add_method = getattr(db, add_method_name)
	insert_method = getattr(db, insert_method_name)

	# Check return statuses
	assert add_method(sample_doujinshi.id, "new_item") == Database_Status.NON_FATAL_ITEM_NOT_FOUND
	assert insert_method("new_item") == Database_Status.OK
	assert add_method(sample_doujinshi.id, "new_item") == Database_Status.OK
	assert add_method(sample_doujinshi.id, "new_item") == Database_Status.NON_FATAL_DUPLICATE
	assert add_method(-1, "new_item") == Database_Status.NON_FATAL_DOUJINSHI_NOT_FOUND

	# Verify in actual doujinshi
	d = db.get_doujinshi(sample_doujinshi.id, partial=False)
	assert "new_item" in getattr(d, properti)



@pytest.mark.parametrize("remove_method_name, insert_method_name, properti", [
	("remove_parody_from_doujinshi", "insert_parody", "parodies"),
	("remove_character_from_doujinshi", "insert_character", "characters"),
	("remove_tag_from_doujinshi", "insert_tag", "tags"),
	("remove_artist_from_doujinshi", "insert_artist", "artists"),
	("remove_group_from_doujinshi", "insert_group", "groups"),
	("remove_language_from_doujinshi", "insert_language", "languages"),
])
def test_remove_from_doujinshi(db, sample_doujinshi, remove_method_name, insert_method_name, properti):
	assert db.insert_doujinshi(sample_doujinshi.ready(), user_prompt=False) == Database_Status.OK

	remove_method = getattr(db, remove_method_name)
	insert_method = getattr(db, insert_method_name)

	item_to_remove = getattr(sample_doujinshi, properti)[0]

	# Check return statuses
	assert remove_method(sample_doujinshi.id, item_to_remove) == Database_Status.OK
	assert remove_method(sample_doujinshi.id, "non-existent") == Database_Status.NON_FATAL_ITEM_NOT_FOUND
	assert remove_method(-1, item_to_remove) == Database_Status.NON_FATAL_DOUJINSHI_NOT_FOUND
	# Remove an item that doesn't belong to the doujinshi.
	assert insert_method("new_item") == Database_Status.OK
	assert remove_method(sample_doujinshi.id, "new_item") == Database_Status.NON_FATAL_NOT_LINKED

	# Verify in actual doujinshi
	d = db.get_doujinshi(sample_doujinshi.id, partial=False)
	assert item_to_remove not in getattr(d, properti)