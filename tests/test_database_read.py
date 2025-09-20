import pytest
import random
import math


# NOTE:
# This test only tests items retrieval correctness.
# For item count tests, go to test_database_item_count.py.


def split_list(list_to_split, k):
	# Split a list into a list of smaller lists, each has at most k elements.
	return [list_to_split[i:i+k] for i in range(0, len(list_to_split), k)]


def compare_retrieved_and_expected_doujinshi(retrieved, expected, has_count):
	# Only works with doujinshi retrieved from dbm.get_doujinshi().
	single_valued_fields = [
		"id", "path", "note",
		"full_name", "full_name_original", "pretty_name", "pretty_name_original"
	]
	for field in single_valued_fields:
		assert retrieved[field] == expected[field], f"Mismatch on field {field}"

	list_like_fields = ["parodies", "characters", "tags", "artists", "groups", "languages"]
	for field in list_like_fields:
		if has_count:
			assert sorted(retrieved[field].keys()) == sorted(expected[field])
		else:
			assert sorted(retrieved[field]) == sorted(expected[field])

	assert retrieved["pages"] == expected["pages"]


def test_get_one_doujinshi(dbm, sample_n_random_doujinshi):
	doujinshi_list, _ = sample_n_random_doujinshi(30)

	for doujinshi in doujinshi_list:
		dbm.insert_doujinshi(doujinshi)

	for expected_doujinshi in doujinshi_list:
		retrieved_doujinshi = dbm.get_doujinshi(expected_doujinshi["id"])
		assert retrieved_doujinshi
		compare_retrieved_and_expected_doujinshi(retrieved_doujinshi, expected_doujinshi, has_count=True)


@pytest.mark.parametrize("n_doujinshi, page_size", [
	# n_doujinshi divisible by page_size
	(9, 9), # 1 pages
	(9*2, 9), # 2 pages
	(9*3, 9), # 3 pages
	(9*6, 9), # even number of pages
	(9*7, 9), # odd number of pages
	# n_doujinshi not divisible by page_size
	(7, 9), # 1 pages
	(9+5, 9), # 2 pages
	(9*2+3, 9), # 3 pages
	(9*5+5, 9), # even number of pages
	(9*6+6, 11), # odd number of pages
])
@pytest.mark.parametrize("use_cache", [True, False])
def test_get_doujinshi_in_page_valid_page_number(dbm, n_doujinshi, page_size, use_cache, sample_n_random_doujinshi):
	def compare_partial_doujinshi(retrieved, expected):
		fields_to_check = ["id", "full_name", "path"]
		for field in fields_to_check:
			assert retrieved[field] == expected[field], f"Mismatch on field {field}"

		assert retrieved["cover_filename"] == expected["pages"][0], "Mismatch cover_filename"

		if not expected["languages"]:
			assert retrieved["language_id"] == None
		elif "english" in expected["languages"]:
			assert retrieved["language_id"] == 1
		elif "japanese" in expected["languages"]:
			assert retrieved["language_id"] == 2
		elif "chinese" in expected["languages"]:
			assert retrieved["language_id"] == 3
		elif "textless" in expected["languages"]:
			assert retrieved["language_id"] == 4

	doujinshi_list, _ = sample_n_random_doujinshi(n_doujinshi)
	doujinshi_list.sort(key=lambda d: d["id"], reverse=True)

	for doujinshi in doujinshi_list:
		dbm.insert_doujinshi(doujinshi)

	retrieved_pages = []
	for page_no in range(1, math.ceil(n_doujinshi / page_size) + 1):
		if use_cache:
			doujinshi_batch = dbm.get_doujinshi_in_page(page_size, page_no, n_doujinshi)
		else:
			doujinshi_batch = dbm.get_doujinshi_in_page(page_size, page_no)
		assert doujinshi_batch
		retrieved_pages.append(doujinshi_batch)

	expected_pages = split_list(doujinshi_list, page_size)
	for i, (retrieved_page, expected_page) in enumerate(zip(retrieved_pages, expected_pages)):
		msg = f"Mismatch number of doujinshis on page {i+1}. Expect {len(expected_page)}, got {len(retrieved_page)} instead."
		assert len(retrieved_page) == len(expected_page), msg
		retrieved_id = [d["id"] for d in retrieved_page]
		expected_id = [d["id"] for d in expected_page]
		assert retrieved_id == expected_id, f"Mismatch id, expected: {expected_id}, got {retrieved_id}."
		for retrieved_doujinshi, expected_doujinshi in zip(retrieved_page, expected_page):
			compare_partial_doujinshi(retrieved_doujinshi, expected_doujinshi)


@pytest.mark.parametrize("illegal_page_number", [-1, 0, 10**6])
def test_get_doujinshi_in_page_illegal_page_number(dbm, sample_n_random_doujinshi, illegal_page_number):
	n_doujinshi_to_test = 23
	page_size = 4

	doujinshi_list, _ = sample_n_random_doujinshi(n_doujinshi_to_test)

	for doujinshi in doujinshi_list:
		dbm.insert_doujinshi(doujinshi)

	should_be_empty = dbm.get_doujinshi_in_page(page_size, illegal_page_number)
	assert should_be_empty == []


@pytest.mark.parametrize("n_doujinshi, expected_n_doujinshi, id_start, id_end", [
	(8, 1, 5, 5),
	(8, 8, 1, 8),
	(8, 7, 1, 7),
	(8, 6, 2, 7),
	(8, 0, 9, 9),
	(8, 7, 2, 19),
	(8, 8, 1, 29),
	(8, 6, -1, 6),
	(8, 8, -1, 18),
	(8, 8, -1, 100),
	(8, 0, 2, 1),
	(8, 0, -7, -5),
	(8, 0, 100, 101)
])
def test_get_doujinshi_in_range(dbm, n_doujinshi, sample_n_random_doujinshi, id_start, id_end, expected_n_doujinshi):
	doujinshi_list, _ = sample_n_random_doujinshi(n_doujinshi)

	for doujinshi in doujinshi_list:
		dbm.insert_doujinshi(doujinshi)

	expected_doujinshi_list = [d for d in doujinshi_list if d["id"] >= id_start and d["id"] <= id_end]
	expected_doujinshi_list.sort(key=lambda d: d["id"])
	retrieved_doujinshi_list = dbm.get_doujinshi_in_range(id_start, id_end)

	len_retrieved = len(retrieved_doujinshi_list)
	assert len_retrieved == expected_n_doujinshi

	for retrieved_doujinshi, expected_doujinshi in zip(retrieved_doujinshi_list, expected_doujinshi_list):
		compare_retrieved_and_expected_doujinshi(retrieved_doujinshi, expected_doujinshi, has_count=False)