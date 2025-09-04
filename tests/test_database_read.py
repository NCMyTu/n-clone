import pytest
from src import DatabaseStatus
import random
import math
from .utils import _sample_doujinshi


def split_list(list_to_split, k):
	return [list_to_split[i:i+k] for i in range(0, len(list_to_split), k)]


def insert_n_doujinshis_into_db(dbm, n_doujinshis):
	to_compare = []

	for d_id in range(n_doujinshis, 0, -1):
		doujinshi = _sample_doujinshi(d_id)

		random.shuffle(doujinshi["pages"])

		to_compare.append({
			"id": doujinshi["id"],
			"full_name": doujinshi["full_name"],
			"path": doujinshi["path"],
			"cover_filename": doujinshi["pages"][0]
		})

		return_status = dbm.insert_doujinshi(doujinshi, False)
		assert return_status == DatabaseStatus.OK

	return to_compare


@pytest.mark.parametrize("n_doujinshis, page_size",
[
	# n_doujinshis divisible by page_size
	(11, 11), # 1 pages
	(22, 11), # 2 pages
	(33, 11), # 3 pages
	(110, 11), # even number of pages
	(121, 11), # odd number of pages
	# n_doujinshis not divisible by page_size
	(9, 11), # 1 pages
	(14, 11), # 2 pages
	(32, 11), # 3 pages
	(109, 11), # even number of pages
	(122, 11), # odd number of pages
])
@pytest.mark.parametrize("use_cache", [True, False])
def test_get_doujinshi_in_page_valid_page_number(dbm, n_doujinshis, page_size, use_cache):
	to_compare = insert_n_doujinshis_into_db(dbm, n_doujinshis)
	to_compare = split_list(to_compare, page_size)

	retrieved_doujinshis = []
	for page_no in range(1, math.ceil(n_doujinshis / page_size) + 1):
		if use_cache:
			return_status, doujinshi_batch = dbm.get_doujinshi_in_page(page_size, page_no, n_doujinshis)
		else:
			return_status, doujinshi_batch = dbm.get_doujinshi_in_page(page_size, page_no)
		assert return_status == DatabaseStatus.OK
		retrieved_doujinshis.append(doujinshi_batch)

	for batch in retrieved_doujinshis:
		for d in batch:
			print(f"id: {d['id']}", end=", ")
		print()

	for i, (retrieved, expected) in enumerate(zip(retrieved_doujinshis, to_compare), start=1):
		assert len(retrieved) == len(expected), f"Mismatch number of doujinshis on page {i}."
		for d_retrieved, d_expected in zip(retrieved, expected):
			assert d_retrieved == d_expected, f"Mismatch on page {i}, retrieved: {d_retrieved}, expected: {d_expected}."

	n_doujinshis_last_page = n_doujinshis % page_size
	if n_doujinshis_last_page == 0:
		n_doujinshis_last_page = page_size
	assert len(retrieved_doujinshis[-1]) == n_doujinshis_last_page, "n_doujinshis in last pages doesn't match."


def test_get_doujinshi_in_page_illegal_page_number(dbm):
	n_doujinshis_to_test = 217
	page_size = 25
	illegal_page_numbers = [-1, 0, 10**6]

	insert_n_doujinshis_into_db(dbm, n_doujinshis_to_test)

	for illegal_page_number in illegal_page_numbers:
		return_status, should_be_empty = dbm.get_doujinshi_in_page(page_size, illegal_page_number)
		assert return_status == DatabaseStatus.OK
		assert should_be_empty == []


@pytest.mark.parametrize("n_doujinshi_to_test, expected_n_doujinshi, id_start, id_end",
[
	(28, 1, 5, 5),
	(28, 10, 1, 10),
	(28, 28, 1, 28),
	(28, 9, 2, 10),
	(28, 27, 2, 49),
	(28, 28, 1, 49),
	(28, 10, -1, 10),
	(28, 28, -1, 28),
	(28, 28, -1, 100),
	(28, 0, 2, 1),
	(28, 0, -7, -5),
	(28, 0, 100, 101)
])
def test_get_doujinshi_in_range(dbm, n_doujinshi_to_test, expected_n_doujinshi, id_start, id_end):
	to_compare = []

	fields_to_shuflfe = [
		"parodies", "characters", "tags",
		"artists", "groups", "languages",
		"pages"
	]

	for d_id in range(1, n_doujinshi_to_test+1):
		doujinshi = _sample_doujinshi(d_id)

		for field in fields_to_shuflfe:
			random.shuffle(doujinshi[field])

		to_compare.append(doujinshi)
		return_status = dbm.insert_doujinshi(doujinshi, False)
		assert return_status == DatabaseStatus.OK

	return_status, retrieved_doujinshi = dbm.get_doujinshi_in_range(id_start, id_end)

	assert return_status == DatabaseStatus.OK
	assert len(retrieved_doujinshi) == expected_n_doujinshi

	expected_doujinshi = [
		d for d in to_compare
		if d["id"] >= id_start and d["id"] <= (id_end if id_end else n_doujinshi_to_test)
	]
	for retrieved, expected in zip(retrieved_doujinshi, expected_doujinshi):
		for item_name, expected_items in expected.items():
			if item_name == "pages":
				assert retrieved[item_name] == expected_items
			elif isinstance(expected_items, list):
				assert sorted(retrieved[item_name]) == sorted(expected_items)
			else:
				assert retrieved[item_name] == expected_items