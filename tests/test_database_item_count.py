import pytest
import random
import math


# d_list, item_counts = sample_n_random_doujinshi(n)
# item_counts = {
	# "parodies": {"parody_1": 0, "parody_2": 1, ...},
	# "characters": {"character_1": 0, "character_2": 1, ...},
	# same with "tags", "artists", "groups", "languages"
# }


ITEM_TYPES = ["parodies", "characters", "tags", "artists", "groups", "languages"]
PLURAL_TO_SINGULAR = {
	"parodies": "parody",
	"characters": "character",
	"tags": "tag",
	"artists": "artist",
	"groups": "group",
	"languages": "language",
}


def compare_count_of_d_eic(doujinshi, expected_item_counts):
	for item_type in ITEM_TYPES:
		for item, count in doujinshi[item_type].items():
			assert count == expected_item_counts[item_type][item]


def verify_count_using_get_count_of(dbm, expected_item_counts):
	# Verify all item type counts in case dbm somehow mutates the wrong item type count.
	for item_type in ITEM_TYPES:
		get_count_of_ = getattr(dbm, f"get_count_of_{item_type}")
		item_count = get_count_of_(list(expected_item_counts[item_type].keys()))
		assert item_count == expected_item_counts[item_type]


def verify_count_in_retrieved_doujinshi(dbm, doujinshi_list, expected_item_counts):
	for doujinshi in doujinshi_list:
		retrieved_doujinshi = dbm.get_doujinshi(doujinshi["id"])
		compare_count_of_d_eic(retrieved_doujinshi, expected_item_counts)


@pytest.mark.parametrize("insert_method, get_count_of_item_method", [
	("insert_parody", "get_count_of_parodies"),
	("insert_character", "get_count_of_characters"),
	("insert_tag", "get_count_of_tags"),
	("insert_artist", "get_count_of_artists"),
	("insert_group", "get_count_of_groups"),
	("insert_language", "get_count_of_languages")
])
def test_insert_item(dbm, insert_method, get_count_of_item_method):
	# Verify that item count is 0 right after being inserted.
	new_items = [f"new_item_{i}" for i in range(20)]

	insert = getattr(dbm, insert_method)

	for new_item in new_items:
		insert(new_item)

	get_count_of = getattr(dbm, get_count_of_item_method)
	item_count = get_count_of(new_items)

	assert len(item_count) == len(new_items)
	assert all(v == 0 for v in item_count.values()), "Newly inserted items should have count of 0."


@pytest.mark.parametrize("n_doujinshi", [1, 7, 22])
def test_insert_doujinshi(dbm, sample_n_random_doujinshi, n_doujinshi):
	# Verify that items are counted correctly after inserting doujinshi.
	doujinshi_list, expected_item_counts = sample_n_random_doujinshi(n_doujinshi)

	for doujinshi in doujinshi_list:
		dbm.insert_doujinshi(doujinshi, False)

	# Insert duplicate doujinshi
	for doujinshi in doujinshi_list:
		dbm.insert_doujinshi(doujinshi, False)

	verify_count_using_get_count_of(dbm, expected_item_counts)
	verify_count_in_retrieved_doujinshi(dbm, doujinshi_list, expected_item_counts)


@pytest.mark.parametrize("n_doujinshi", [1, 7, 22])
@pytest.mark.parametrize("field, add_item_to_doujinshi", [
	("parodies", "add_parody_to_doujinshi"),
	("characters", "add_character_to_doujinshi"),
	("tags", "add_tag_to_doujinshi"),
	("artists", "add_artist_to_doujinshi"),
	("groups", "add_group_to_doujinshi"),
	("languages", "add_language_to_doujinshi")
])
def test_add_item_to_doujinshi_existing_item(dbm, sample_n_random_doujinshi, n_doujinshi, field, add_item_to_doujinshi):
	# Verify that items are counted correctly after inserting existing items from the db into doujinshi.
	doujinshi_list, expected_item_counts = sample_n_random_doujinshi(n_doujinshi)

	for doujinshi in doujinshi_list:
		dbm.insert_doujinshi(doujinshi, False)

	# Insert random existing items to doujinshi.
	random.seed(2)
	full_items = [item for item, count in expected_item_counts[field].items() if count > 0]
	insert_into_doujinshi_ = getattr(dbm, add_item_to_doujinshi)

	for doujinshi in doujinshi_list:
		items_not_in_this_doujinshi = list(set(full_items) - set(doujinshi[field]))
		n_items_to_insert = random.randint(0, len(items_not_in_this_doujinshi))
		items_to_insert = random.sample(items_not_in_this_doujinshi, n_items_to_insert)

		for item in items_to_insert:
			insert_into_doujinshi_(doujinshi["id"], item)
			expected_item_counts[field][item] += 1

	verify_count_using_get_count_of(dbm, expected_item_counts)
	verify_count_in_retrieved_doujinshi(dbm, doujinshi_list, expected_item_counts)

	# Insert again. Counts shouldn't increase.
	random.seed(2)
	for doujinshi in doujinshi_list:
		items_not_in_this_doujinshi = list(set(full_items) - set(doujinshi[field]))
		n_items_to_insert = random.randint(0, len(items_not_in_this_doujinshi))
		items_to_insert = random.sample(items_not_in_this_doujinshi, n_items_to_insert)

		for item in items_to_insert:
			insert_into_doujinshi_(doujinshi["id"], item)

	verify_count_using_get_count_of(dbm, expected_item_counts)
	verify_count_in_retrieved_doujinshi(dbm, doujinshi_list, expected_item_counts)


@pytest.mark.parametrize("n_doujinshi", [1, 7, 22])
@pytest.mark.parametrize("field, add_item_to_doujinshi, insert_item", [
	("parodies", "add_parody_to_doujinshi", "insert_parody"),
	("characters", "add_character_to_doujinshi", "insert_character"),
	("tags", "add_tag_to_doujinshi", "insert_tag"),
	("artists", "add_artist_to_doujinshi", "insert_artist"),
	("groups", "add_group_to_doujinshi", "insert_group"),
	("languages", "add_language_to_doujinshi", "insert_language")
])
def test_add_item_to_doujinshi_new_item(dbm, sample_n_random_doujinshi, n_doujinshi, field, add_item_to_doujinshi, insert_item):
	# Verify that items are counted correctly after inserting new items into doujinshi.
	doujinshi_list, expected_item_counts = sample_n_random_doujinshi(n_doujinshi)

	for doujinshi in doujinshi_list:
		dbm.insert_doujinshi(doujinshi, False)

	# Insert new items.
	new_items = [f"new_item_{i}" for i in range(50)]
	insert_item_ = getattr(dbm, insert_item)
	for new_item in new_items:
		insert_item_(new_item)
		expected_item_counts[field][new_item] = 0

	# Insert those new items to doujinshi.
	random.seed(2)
	insert_into_doujinshi_ = getattr(dbm, add_item_to_doujinshi)

	for doujinshi in doujinshi_list:
		n_items_to_insert = random.randint(0, len(new_items))
		items_to_insert = random.sample(new_items, n_items_to_insert)

		for item in items_to_insert:
			insert_into_doujinshi_(doujinshi["id"], item)
			expected_item_counts[field][item] += 1

	verify_count_using_get_count_of(dbm, expected_item_counts)
	verify_count_in_retrieved_doujinshi(dbm, doujinshi_list, expected_item_counts)

	# Insert again. Counts shouldn't increase.
	random.seed(2)
	for doujinshi in doujinshi_list:
		n_items_to_insert = random.randint(0, len(new_items))
		items_to_insert = random.sample(new_items, n_items_to_insert)

		for item in items_to_insert:
			insert_into_doujinshi_(doujinshi["id"], item)

	verify_count_using_get_count_of(dbm, expected_item_counts)
	verify_count_in_retrieved_doujinshi(dbm, doujinshi_list, expected_item_counts)


@pytest.mark.parametrize("n_doujinshi", [1, 7, 22])
@pytest.mark.parametrize("field, remove_item_from_doujinshi", [
	("parodies", "remove_parody_from_doujinshi"),
	("characters", "remove_character_from_doujinshi"),
	("tags", "remove_tag_from_doujinshi"),
	("artists", "remove_artist_from_doujinshi"),
	("groups", "remove_group_from_doujinshi"),
	("languages", "remove_language_from_doujinshi")
])
def test_remove_item_from_doujinshi(dbm, sample_n_random_doujinshi, n_doujinshi, field, remove_item_from_doujinshi):
	# Verify that items are counted correctly after removing existing items from doujinshi.
	doujinshi_list, expected_item_counts = sample_n_random_doujinshi(n_doujinshi)

	for doujinshi in doujinshi_list:
		dbm.insert_doujinshi(doujinshi, False)

	# Remove items from doujinshi.
	remove_from_doujinshi_ = getattr(dbm, remove_item_from_doujinshi)

	for doujinshi in doujinshi_list:
		n_items_to_remove = random.randint(0, len(doujinshi[field]))
		items_to_remove = random.sample(doujinshi[field], n_items_to_remove)

		for item in items_to_remove:
			remove_from_doujinshi_(doujinshi["id"], item)
			expected_item_counts[field][item] -= 1

	verify_count_using_get_count_of(dbm, expected_item_counts)
	verify_count_in_retrieved_doujinshi(dbm, doujinshi_list, expected_item_counts)

	# Remove an item that isn't linked to doujinshi.
	new_item = "new_item"
	item_type = PLURAL_TO_SINGULAR[field]
	getattr(dbm, f"insert_{item_type}")(new_item)

	for doujinshi in doujinshi_list:
		remove_from_doujinshi_(doujinshi["id"], new_item)

	verify_count_using_get_count_of(dbm, expected_item_counts)
	verify_count_in_retrieved_doujinshi(dbm, doujinshi_list, expected_item_counts)


@pytest.mark.parametrize("n_doujinshi", [1, 7, 22])
def test_remove_doujinshi(dbm, sample_n_random_doujinshi, n_doujinshi):
	# Verify that items are counted correctly after removing doujinshi.
	doujinshi_list, expected_item_counts = sample_n_random_doujinshi(n_doujinshi)

	for doujinshi in doujinshi_list:
		dbm.insert_doujinshi(doujinshi, False)

	n_doujinshi_to_remove = math.ceil(n_doujinshi / 2)

	for i in range(n_doujinshi_to_remove):
		doujinshi = doujinshi_list[i]
		dbm.remove_doujinshi(doujinshi["id"])

		for item_type in ITEM_TYPES:
			for item in doujinshi[item_type]:
				expected_item_counts[item_type][item] -= 1

	verify_count_using_get_count_of(dbm, expected_item_counts)
	verify_count_in_retrieved_doujinshi(dbm, doujinshi_list[n_doujinshi_to_remove:], expected_item_counts)


@pytest.mark.parametrize("n_doujinshi", [1, 7, 22])
def test_all_operations(dbm, sample_n_random_doujinshi, n_doujinshi):
	# Verify items count after doing all operations.
	doujinshi_list, expected_item_counts = sample_n_random_doujinshi(n_doujinshi)

	for doujinshi in doujinshi_list:
		dbm.insert_doujinshi(doujinshi, False)

	random.seed(2)
	n_doujinshi_half = math.ceil(n_doujinshi / 2)

	for field in ITEM_TYPES:
		item_type = PLURAL_TO_SINGULAR[field]

		insert_into_db_ = getattr(dbm, f"insert_{item_type}")
		add_to_doujinshi_ = getattr(dbm, f"add_{item_type}_to_doujinshi")
		remove_from_doujinshi_ = getattr(dbm, f"remove_{item_type}_from_doujinshi")

		new_items = [f"{field}_{i}" for i in range(15)]

		# Insert new items.
		for item in new_items:
			insert_into_db_(item)
			expected_item_counts[field][item] = 0

		# Add items to doujinshi.
		n_new_items_half = math.ceil(len(new_items) / 2)
		for item in random.sample(new_items, n_new_items_half):
			for doujinshi in random.sample(doujinshi_list, n_doujinshi_half):
				add_to_doujinshi_(doujinshi["id"], item)
				doujinshi[field].append(item)
				expected_item_counts[field][item] += 1

		# Remove items
		for doujinshi in random.sample(doujinshi_list, n_doujinshi_half):
			n_items_half = math.ceil(len(doujinshi[field]) / 2)
			for item in random.sample(doujinshi[field], n_items_half):
				remove_from_doujinshi_(doujinshi["id"], item)
				expected_item_counts[field][item] -= 1

	verify_count_using_get_count_of(dbm, expected_item_counts)
	verify_count_in_retrieved_doujinshi(dbm, doujinshi_list, expected_item_counts)