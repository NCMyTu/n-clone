import pytest
from src import DatabaseStatus
import random


@pytest.mark.parametrize("add_method_name, insert_method_name, field", [
	("add_parody_to_doujinshi", "insert_parody", "parodies"),
	("add_character_to_doujinshi", "insert_character", "characters"),
	("add_tag_to_doujinshi", "insert_tag", "tags"),
	("add_artist_to_doujinshi", "insert_artist", "artists"),
	("add_group_to_doujinshi", "insert_group", "groups"),
	("add_language_to_doujinshi", "insert_language", "languages"),
])
def test_add_item_to_doujinshi(dbm, sample_doujinshi, add_method_name, insert_method_name, field):
	dbm.insert_doujinshi(sample_doujinshi, False)
	d_id = sample_doujinshi["id"]

	add_item_to_doujinshi = getattr(dbm, add_method_name)
	insert_item_into_db = getattr(dbm, insert_method_name)

	new_items = ["new_item_1", "new_item_2", "new_item_3"]

	# Check return statuses.
	# Yes, those for loops need to be seperated like that to test "batch" operation.
	for item in new_items:
		assert add_item_to_doujinshi(d_id, item) == DatabaseStatus.NOT_FOUND

	for item in new_items:
		insert_item_into_db(item)

	for item in new_items:
		assert add_item_to_doujinshi(d_id, item) == DatabaseStatus.OK
	for item in new_items:
		assert add_item_to_doujinshi(d_id, item) == DatabaseStatus.ALREADY_EXISTS

	for item in new_items:
		assert add_item_to_doujinshi(-9999999, item) == DatabaseStatus.NOT_FOUND

	# Verify again in the actual doujinshi
	retrieved_doujinshi = dbm.get_doujinshi(d_id)
	for item in new_items:
		assert item in retrieved_doujinshi[field].keys()


def test_add_pages_to_doujinshi(dbm, sample_doujinshi):
	dbm.insert_doujinshi(sample_doujinshi, False)
	d_id = sample_doujinshi["id"]

	new_pages = [f"new_page_{i}" for i in range(1, 200)]
	assert dbm.add_pages_to_doujinshi(d_id, new_pages) == DatabaseStatus.OK

	retrieved_doujinshi = dbm.get_doujinshi(d_id)
	assert retrieved_doujinshi["pages"] == new_pages, "Old and new pages have different order."

	random.seed(2)
	random.shuffle(new_pages)

	assert dbm.add_pages_to_doujinshi(d_id, new_pages) == DatabaseStatus.OK

	retrieved_doujinshi = dbm.get_doujinshi(d_id)
	assert retrieved_doujinshi["pages"] == new_pages, "Old and new pages have different order."

	assert dbm.add_pages_to_doujinshi(d_id, []) == DatabaseStatus.OK


@pytest.mark.parametrize("remove_method_name, insert_method_name, field", [
	("remove_parody_from_doujinshi", "insert_parody", "parodies"),
	("remove_character_from_doujinshi", "insert_character", "characters"),
	("remove_tag_from_doujinshi", "insert_tag", "tags"),
	("remove_artist_from_doujinshi", "insert_artist", "artists"),
	("remove_group_from_doujinshi", "insert_group", "groups"),
	("remove_language_from_doujinshi", "insert_language", "languages"),
])
def test_remove_item_from_doujinshi(dbm, sample_doujinshi, remove_method_name, insert_method_name, field):
	dbm.insert_doujinshi(sample_doujinshi, False)
	d_id = sample_doujinshi["id"]

	remove_method = getattr(dbm, remove_method_name)
	insert_method = getattr(dbm, insert_method_name)

	n_items_to_remove = 3
	items_to_remove = sample_doujinshi[field][:n_items_to_remove]

	# Remove non-existent items
	for item in ["non-existent-1", "non_existent_2", "non existent 3"]:
		assert remove_method(d_id, item) == DatabaseStatus.NOT_FOUND

	# Remove items linked with doujinshi
	for item in items_to_remove:
		assert remove_method(d_id, item) == DatabaseStatus.OK

	# Remove items from a non-existent doujinshi
	for item in items_to_remove:
		assert remove_method(-999999, item) == DatabaseStatus.NOT_FOUND

	# Remove an item that isn't linked to doujinshi.
	assert insert_method("new_item") == DatabaseStatus.OK
	assert remove_method(d_id, "new_item") == DatabaseStatus.NOT_FOUND

	# Verify again in the actual doujinshi
	retrieved_doujinshi = dbm.get_doujinshi(d_id)
	for item in items_to_remove:
		assert item not in retrieved_doujinshi[field].keys()
	assert len(retrieved_doujinshi[field]) == len(sample_doujinshi[field]) - n_items_to_remove


def test_remove_all_pages_from_doujinshi(dbm, sample_doujinshi):
	dbm.insert_doujinshi(sample_doujinshi, False)
	d_id = sample_doujinshi["id"]

	assert dbm.remove_all_pages_from_doujinshi(d_id) == DatabaseStatus.OK

	# Verify in the actual doujinshi
	retrieved_doujinshi = dbm.get_doujinshi(d_id)
	assert not retrieved_doujinshi["pages"]

	# Remove empty `pages` should be OK
	assert dbm.remove_all_pages_from_doujinshi(d_id) == DatabaseStatus.OK


@pytest.mark.parametrize("update_method_name, column_name", [
	("update_full_name_of_doujinshi", "full_name"),
	("update_full_name_original_of_doujinshi", "full_name_original"),
	("update_pretty_name_of_doujinshi", "pretty_name"),
	("update_pretty_name_original_of_doujinshi", "pretty_name_original"),
	("update_note_of_doujinshi", "note"),
])
@pytest.mark.parametrize("value, expected_status", [
    ("new_column", DatabaseStatus.OK),
    ("", DatabaseStatus.INTEGRITY_ERROR),
    (" ", DatabaseStatus.INTEGRITY_ERROR),
    (" \n\t  ", DatabaseStatus.INTEGRITY_ERROR),
    ([], DatabaseStatus.EXCEPTION),
    ((), DatabaseStatus.EXCEPTION),
    (set(), DatabaseStatus.EXCEPTION),
    ({}, DatabaseStatus.EXCEPTION),
    (object(), DatabaseStatus.EXCEPTION),
])
def test_update_doujinshi_column(dbm, sample_doujinshi, update_method_name, column_name, value, expected_status):
	dbm.insert_doujinshi(sample_doujinshi, False)
	d_id = sample_doujinshi["id"]

	update_method = getattr(dbm, update_method_name)

	assert update_method(d_id, value) == expected_status

	if expected_status == DatabaseStatus.OK:
		# Verify again in the actual doujinshi
		retrieved_doujinshi = dbm.get_doujinshi(d_id)
		assert retrieved_doujinshi[column_name] == value

		# Update a non-existent doujinshi
		assert update_method(-999999, value) == DatabaseStatus.NOT_FOUND


def test_update_doujinshi_path(dbm, sample_n_random_doujinshi):
	doujinshi_list, _ = sample_n_random_doujinshi(30)

	for doujinshi in doujinshi_list:
		dbm.insert_doujinshi(doujinshi)

	doujinshi_path_list = [d["path"] for d in doujinshi_list]

	for i, doujinshi in enumerate(doujinshi_list):
		# Update to its own path
		assert dbm.update_path_of_doujinshi(doujinshi["id"], doujinshi["path"]) == DatabaseStatus.OK
		# Update to other doujinshi's path
		duplicate_path = doujinshi_path_list[(i + 1) % len(doujinshi_path_list)]
		assert dbm.update_path_of_doujinshi(doujinshi["id"], duplicate_path) == DatabaseStatus.INTEGRITY_ERROR

	for doujinshi in doujinshi_list:
		# Update to a completely new path
		new_path = f"new_path_{doujinshi['id']}"
		assert dbm.update_path_of_doujinshi(doujinshi["id"], new_path) == DatabaseStatus.OK

		# Verify again in the actual doujinshi.
		retrieved_doujinshi = dbm.get_doujinshi(doujinshi["id"])
		assert retrieved_doujinshi["path"] == new_path

	# Update path of a non-existent doujinshi
	assert dbm.update_path_of_doujinshi(-999999, "new_path") == DatabaseStatus.NOT_FOUND