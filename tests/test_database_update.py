import pytest
from src import DatabaseStatus
from .utils import _sample_doujinshi
import random


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


@pytest.mark.parametrize("item_type, update_count_method, use_bulk_update",
[
	("parodies", "update_count_of_parody", False),
	("characters", "update_count_of_character", False),
	("tags", "update_count_of_tag", False),
	("artists", "update_count_of_artist", False),
	("groups", "update_count_of_group", False),
	("languages", "update_count_of_language", False),
	# same as above but using update_count_of_all() instead
	("parodies", None, True),
	("characters", None, True),
	("tags", None, True),
	("artists", None, True),
	("groups", None, True),
	("languages", None, True),
])
def test_get_count_of_items_in_category(dbm, item_type, update_count_method, use_bulk_update):
	items = [f"item_{i}" for i in range(50)]
	item_count = {item: 0 for item in items}

	get_count_of = f"get_count_of_{item_type}"
	get_count_of = getattr(dbm, get_count_of)

	for d_id in range(1, 151):
		doujinshi = _sample_doujinshi(d_id)

		n_items = random.randint(0, len(items)//2)
		selected_items = random.sample(items, n_items)
		doujinshi[item_type] = selected_items

		for item in selected_items:
			item_count[item] += 1

		assert dbm.insert_doujinshi(doujinshi, False) == DatabaseStatus.OK

	if use_bulk_update:
		dbm.update_count_of_all()
	else:
		getattr(dbm, update_count_method)()

	return_status, retrieved_item_count = get_count_of(items)
	assert return_status == DatabaseStatus.OK
	assert retrieved_item_count == item_count

	return_status, empty_item_count = get_count_of([])
	assert return_status == DatabaseStatus.OK
	assert empty_item_count == {}

	return_status, no_exist_item_count = get_count_of(["no_exist"])
	assert return_status == DatabaseStatus.OK
	assert no_exist_item_count == {"no_exist": 0}


def test_get_count_of_items_when_getting_and_removing_doujinshi(dbm):
	def is_subdict(small, big):
		return all(k in big and big[k] == v for k, v in small.items())

	n_items_per_type = 50
	parody_count, character_count, tag_count, artist_count, group_count, language_count = [
		{f"item_{i}": 0 for i in range(n_items_per_type)} for _ in range(6)
	]

	mapping = {
		"parodies": parody_count,
		"characters": character_count,
		"tags": tag_count,
		"artists": artist_count,
		"groups": group_count,
		"languages": language_count,
	}

	n_doujinshis = 150
	n_doujinshis_to_remove = 50

	# Insert new doujinshis
	for i in range(n_doujinshis):
		doujinshi = _sample_doujinshi(i)

		for field, item_count in mapping.items():
			n_items = random.randint(0, n_items_per_type)

			doujinshi[field] = random.sample(list(item_count.keys()), n_items)

			for item in doujinshi[field]:
				item_count[item] += 1

		dbm.insert_doujinshi(doujinshi, False)

	dbm.update_count_of_all()

	# Verify counts after insertion
	for i in range(n_doujinshis):
		return_status, doujinshi = dbm.get_doujinshi(i)
		assert return_status == DatabaseStatus.OK

		for field, item_count in mapping.items():
			assert is_subdict(doujinshi[field], item_count)

	# Manually update counts after removal
	for i in range(n_doujinshis_to_remove):
		return_status, doujinshi = dbm.get_doujinshi(i)
		assert return_status == DatabaseStatus.OK

		# Remove first n_doujinshis_to_remove doujinshis
		if i < n_doujinshis_to_remove:
			for field, item_count in mapping.items():
				for item in doujinshi[field]:
					item_count[item] -= 1

			return_status = dbm.remove_doujinshi(i)
			assert return_status == DatabaseStatus.OK

	dbm.update_count_of_all()

	# Verify again
	for i in range(n_doujinshis_to_remove, n_doujinshis):
		return_status, doujinshi = dbm.get_doujinshi(i)
		assert return_status == DatabaseStatus.OK

		for field, item_count in mapping.items():
			assert is_subdict(doujinshi[field], item_count)