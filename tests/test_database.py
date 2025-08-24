from src import DatabaseManager, DatabaseStatus, extract_all_numbers as numerically
from datetime import date, datetime
from pathlib import Path
import pytest
import random


@pytest.fixture
def dbm():
	dbm = DatabaseManager(url=f"sqlite:///:memory:", test=True)
	dbm.logger.disable()
	status = dbm.create_database()
	assert status == DatabaseStatus.OK
	return dbm


def _sample_doujinshi():
	return {
		"id": 1,
		
		"full_name": "Test Doujinshi", "pretty_name": "st Dou",
		"full_name_original": "元の名前", "pretty_name_original": "の名", # Must be japanese
		"path": "inter/path",
		"note": "Test note",

		"parodies": [f"parody_{i}" for i in range(1, 4)],
		"characters": [f"character_{i}" for i in range(5)],
		"tags": [f"tag_{i}" for i in range(1, 4)],
		"artists": [f"artist_{i}" for i in range(1, 5)],
		"groups": [f"group_{i}" for i in range(1, 6)],
		"languages": [f"language_{i}" for i in range(1, 6)],
		"pages": [f"f_{i}.jpg" for i in range(1, 31)],
	}


@pytest.fixture
def sample_doujinshi():
	return _sample_doujinshi()


INVALID_VALUES = [
	None,
	"", " \n\t  ",
	[], (), set(), {},
	1.23, True, object(),
]


@pytest.mark.parametrize("invalid_value", INVALID_VALUES + ["123"])
def test_insert_invalid_id(dbm, sample_doujinshi, invalid_value):
	sample_doujinshi["id"] = invalid_value
	assert dbm.insert_doujinshi(sample_doujinshi, False) != DatabaseStatus.OK


@pytest.mark.parametrize("invalid_value", INVALID_VALUES)
def test_insert_invalid_full_name(dbm, sample_doujinshi, invalid_value):
	sample_doujinshi["full_name"] = invalid_value
	assert dbm.insert_doujinshi(sample_doujinshi, False) != DatabaseStatus.OK


@pytest.mark.parametrize("invalid_value", INVALID_VALUES)
def test_insert_invalid_path(dbm, sample_doujinshi, invalid_value):
	sample_doujinshi["path"] = invalid_value
	assert dbm.insert_doujinshi(sample_doujinshi, False) != DatabaseStatus.OK


def test_insert_and_get_doujinshi(dbm, sample_doujinshi):
	assert dbm.insert_doujinshi(sample_doujinshi, False) == DatabaseStatus.OK
	assert dbm.insert_doujinshi(sample_doujinshi, False) == DatabaseStatus.NON_FATAL_ITEM_DUPLICATE

	return_status, d = dbm.get_doujinshi(sample_doujinshi["id"])

	assert return_status == DatabaseStatus.OK
	assert d["id"] == sample_doujinshi["id"]
	assert d["full_name"] == sample_doujinshi["full_name"]
	assert d["pretty_name"] == sample_doujinshi["pretty_name"]
	assert d["full_name_original"] == sample_doujinshi["full_name_original"]
	assert d["pretty_name_original"] == sample_doujinshi["pretty_name_original"]
	assert d["path"] == Path(sample_doujinshi["path"]).as_posix()
	assert d["note"] == sample_doujinshi["note"]

	assert set(d["parodies"].keys()) == set(sample_doujinshi["parodies"])
	assert set(d["characters"].keys()) == set(sample_doujinshi["characters"])
	assert set(d["tags"].keys()) == set(sample_doujinshi["tags"])
	assert set(d["artists"].keys()) == set(sample_doujinshi["artists"])
	assert set(d["groups"].keys()) == set(sample_doujinshi["groups"])
	assert set(d["languages"].keys()) == set(sample_doujinshi["languages"])

	assert d["pages"] == sample_doujinshi["pages"], "pages are not in the same order."

	return_status, d = dbm.get_doujinshi(-99999999)

	assert return_status == DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND
	assert d is None


@pytest.mark.parametrize("insert_method_name", [
	"insert_parody",
	"insert_character",
	"insert_tag",
	"insert_artist",
	"insert_group",
	"insert_language",
])
def test_insert_item(dbm, insert_method_name):
	method = getattr(dbm, insert_method_name)

	assert method("NEW_VALUE") == DatabaseStatus.OK
	assert method("new value again") == DatabaseStatus.OK
	assert method("パロディ") == DatabaseStatus.OK
	assert method("with 'apostrophe ") == DatabaseStatus.OK

	assert method("NEW_VALUE") == DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
	assert method("new_value    ") == DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
	assert method("DROP TABLE artist;") == DatabaseStatus.OK

	assert method("") == DatabaseStatus.FATAL
	assert method(" ") == DatabaseStatus.FATAL
	assert method("\n\t") == DatabaseStatus.FATAL
	assert method(None) == DatabaseStatus.FATAL
	assert method(123) == DatabaseStatus.FATAL
	assert method(3.14159) == DatabaseStatus.FATAL
	assert method(True) == DatabaseStatus.FATAL
	assert method([]) == DatabaseStatus.FATAL
	assert method({}) == DatabaseStatus.FATAL
	assert method(()) == DatabaseStatus.FATAL
	assert method(b"bytes") == DatabaseStatus.FATAL
	assert method(bytearray(b"data")) == DatabaseStatus.FATAL


@pytest.mark.parametrize("add_method_name, insert_method_name, properti", [ # "property" is reserved...
	("add_parody_to_doujinshi", "insert_parody", "parodies"),
	("add_character_to_doujinshi", "insert_character", "characters"),
	("add_tag_to_doujinshi", "insert_tag", "tags"),
	("add_artist_to_doujinshi", "insert_artist", "artists"),
	("add_group_to_doujinshi", "insert_group", "groups"),
	("add_language_to_doujinshi", "insert_language", "languages"),
])
def test_add_item_to_doujinshi(dbm, sample_doujinshi, add_method_name, insert_method_name, properti):
	assert dbm.insert_doujinshi(sample_doujinshi, False) == DatabaseStatus.OK

	d_id = sample_doujinshi["id"]
	add_to_doujinshi = getattr(dbm, add_method_name)
	insert_into_db = getattr(dbm, insert_method_name)

	new_items = ["new_item_1", "new_item_2", "new_item_3"]

	# Check return statuses.
	# Yes, those for loops need to be seperated like that to test "batch" operation.
	for item in new_items:
		assert add_to_doujinshi(d_id, item) == DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

	for item in new_items:
		assert insert_into_db(item) == DatabaseStatus.OK

	for item in new_items:
		assert add_to_doujinshi(d_id, item) == DatabaseStatus.OK
	for item in new_items:
		assert add_to_doujinshi(d_id, item) == DatabaseStatus.NON_FATAL_ITEM_DUPLICATE

	for item in new_items:
		assert add_to_doujinshi(-9999999, item) == DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

	# Verify again in the actual doujinshi
	return_status, d = dbm.get_doujinshi(d_id)
	assert return_status == DatabaseStatus.OK
	for item in new_items:
		assert item in d[properti].keys()


def test_add_pages_to_doujinshi(dbm, sample_doujinshi):
	assert dbm.insert_doujinshi(sample_doujinshi, False) == DatabaseStatus.OK

	d_id = sample_doujinshi["id"]
	new_pages = [f"new_page_{i}" for i in range(1, 200)]
	assert dbm.add_pages_to_doujinshi(d_id, new_pages) == DatabaseStatus.OK
	return_status, new_d = dbm.get_doujinshi(d_id)
	assert return_status == DatabaseStatus.OK
	assert new_d["pages"] == new_pages, "Old and new pages have different order."

	random.shuffle(new_pages)
	assert dbm.add_pages_to_doujinshi(d_id, new_pages) == DatabaseStatus.OK
	return_status, new_d = dbm.get_doujinshi(d_id)
	assert return_status == DatabaseStatus.OK
	assert new_d["pages"] == new_pages, "Old and new pages have different order."


@pytest.mark.parametrize("remove_method_name, insert_method_name, properti", [
	("remove_parody_from_doujinshi", "insert_parody", "parodies"),
	("remove_character_from_doujinshi", "insert_character", "characters"),
	("remove_tag_from_doujinshi", "insert_tag", "tags"),
	("remove_artist_from_doujinshi", "insert_artist", "artists"),
	("remove_group_from_doujinshi", "insert_group", "groups"),
	("remove_language_from_doujinshi", "insert_language", "languages"),
])
def test_remove_item_from_doujinshi(dbm, sample_doujinshi, remove_method_name, insert_method_name, properti):
	assert dbm.insert_doujinshi(sample_doujinshi, False) == DatabaseStatus.OK

	remove_method = getattr(dbm, remove_method_name)
	insert_method = getattr(dbm, insert_method_name)

	n_items_to_remove = 3
	items_to_remove = sample_doujinshi[properti][:n_items_to_remove]

	d_id = sample_doujinshi["id"]
	# Check return statuses
	for item in ["non-existent-1", "non_existent_2"]:
		assert remove_method(d_id, item) == DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND
	for item in items_to_remove:
		assert remove_method(d_id, item) == DatabaseStatus.OK
	for item in items_to_remove:
		assert remove_method(-999999, item) == DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND
	# Remove an item that doesn't belong to the doujinshi.
	assert insert_method("new_item") == DatabaseStatus.OK
	assert remove_method(d_id, "new_item") == DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND

	# Verify again in the actual doujinshi
	return_status, d = dbm.get_doujinshi(d_id)
	assert return_status == DatabaseStatus.OK
	for item in items_to_remove:
		assert item not in d[properti].keys()
	assert len(d[properti]) == len(sample_doujinshi[properti]) - n_items_to_remove


def test_remove_all_pages_from_doujinshi(dbm, sample_doujinshi):
	assert dbm.insert_doujinshi(sample_doujinshi, False) == DatabaseStatus.OK

	d_id = sample_doujinshi["id"]
	assert dbm.remove_all_pages_from_doujinshi(d_id) == DatabaseStatus.OK

	# Verify again in the actual doujinshi
	return_status, d = dbm.get_doujinshi(d_id)
	assert return_status == DatabaseStatus.OK
	assert not d["pages"]


def test_remove_doujinshi(dbm, sample_doujinshi):
	assert dbm.insert_doujinshi(sample_doujinshi, False) == DatabaseStatus.OK

	assert dbm.remove_doujinshi(sample_doujinshi["id"]) == DatabaseStatus.OK
	assert dbm.remove_doujinshi(-9999999) == DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND


@pytest.mark.parametrize("update_method_name, field", [
	("update_full_name_of_doujinshi", "full_name"),
	("update_full_name_original_of_doujinshi", "full_name_original"),
	("update_pretty_name_of_doujinshi", "pretty_name"),
	("update_pretty_name_original_of_doujinshi", "pretty_name_original"),
	("update_note_of_doujinshi", "note"),
	("update_path_of_doujinshi", "path"),
])
def test_update_doujinshi_fields(dbm, sample_doujinshi, update_method_name, field):
	assert dbm.insert_doujinshi(sample_doujinshi, False) == DatabaseStatus.OK

	d_id = sample_doujinshi["id"]

	update_method = getattr(dbm, update_method_name)

	new_value = f"updated_{field}"
	assert update_method(d_id, new_value) == DatabaseStatus.OK

	# Verify again
	return_status, d = dbm.get_doujinshi(d_id)
	assert return_status == DatabaseStatus.OK
	assert d is not None
	assert d[field] == new_value

	assert update_method(-999999, new_value) == DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND


@pytest.mark.parametrize("item_type", [
	"parodies", "characters", "tags", "artists", "groups", "languages"
])
def test_get_count_of_items_in_category(dbm, item_type):
	items = [f"item_{i}" for i in range(100)]
	item_count = {item: 0 for item in items}

	get_count_of = f"get_count_of_{item_type}"
	get_count_of = getattr(dbm, get_count_of)

	for i in range(200):
		doujinshi = _sample_doujinshi()

		n_items = random.randint(0, len(items)//2)
		selected_items = random.sample(items, n_items)

		doujinshi["id"] = i
		doujinshi["path"] = f"path_{i}"
		doujinshi[item_type] = selected_items

		for item in selected_items:
			item_count[item] += 1

		assert dbm.insert_doujinshi(doujinshi, False) == DatabaseStatus.OK

	return_status, retrieved_item_count = get_count_of(items)
	assert return_status == DatabaseStatus.OK
	assert retrieved_item_count == item_count

	return_status, empty_item_count = get_count_of([])
	assert return_status == DatabaseStatus.OK
	assert empty_item_count == {}

	return_status, no_exist_item_count = get_count_of(["no_exist"])
	assert return_status == DatabaseStatus.OK
	assert no_exist_item_count == {"no_exist": 0}


def test_get_count_of_items_when_getting_doujinshi(dbm):
	def is_subdict(small, big):
		return all(k in big and big[k] == v for k, v in small.items())

	parody_count, character_count, tag_count = [{f"item_{i}": 0 for i in range(100)} for _ in range(3)]
	artist_count, group_count, language_count = [{f"item_{i}": 0 for i in range(100)} for _ in range(3)]

	mapping = {
		"parodies": parody_count,
		"characters": character_count,
		"tags": tag_count,
		"artists": artist_count,
		"groups": group_count,
		"languages": language_count,
	}

	for i in range(200):
		doujinshi = _sample_doujinshi()
		doujinshi["id"] = i
		doujinshi["path"] = f"path_{i}"

		for field, item_count in mapping.items():
			n_items = random.randint(0, 50)

			doujinshi[field] = random.sample(list(item_count.keys()), n_items)

			for item in doujinshi[field]:
				item_count[item] += 1

		dbm.insert_doujinshi(doujinshi, False)

	for i in range(200):
		return_status, doujinshi = dbm.get_doujinshi(i)
		assert return_status == DatabaseStatus.OK

		for field, item_count in mapping.items():
			assert is_subdict(doujinshi[field], item_count)