import pytest
from pathlib import Path
from src import DatabaseStatus


@pytest.mark.parametrize("invalid_field", ["id", "full_name", "path"])
@pytest.mark.parametrize("invalid_value",[
	None,
	"", " ", " \n\t  ",
	[], (), set(), {},
	1.23, True, object(),
])
def test_insert_doujinshi_invalid_non_null_field(dbm, sample_doujinshi, invalid_field, invalid_value):
	sample_doujinshi[invalid_field] = invalid_value
	assert dbm.insert_doujinshi(sample_doujinshi, False) != DatabaseStatus.OK


@pytest.mark.parametrize("invalid_field", ["full_name_original", "pretty_name", "pretty_name_original", "note"])
@pytest.mark.parametrize("invalid_value",[
	"", " ", " \n\t  ",
	[], (), set(), {}, object(),
])
def test_insert_doujinshi_invalid_nullable_field(dbm, sample_doujinshi, invalid_field, invalid_value):
	sample_doujinshi[invalid_field] = invalid_value
	assert dbm.insert_doujinshi(sample_doujinshi, False) != DatabaseStatus.OK


@pytest.mark.parametrize("insert_function_name", [
	"insert_parody", "insert_character", "insert_tag",
	"insert_artist", "insert_group", "insert_language",
])
def test_insert_item(dbm, insert_function_name):
	insert_function = getattr(dbm, insert_function_name)

	assert insert_function("NEW_VALUE") == DatabaseStatus.OK
	assert insert_function("new value again") == DatabaseStatus.OK
	assert insert_function("パロディ") == DatabaseStatus.OK
	assert insert_function("with \"apostrophe' ") == DatabaseStatus.OK

	assert insert_function("NEW_VALUE") == DatabaseStatus.ALREADY_EXISTS
	assert insert_function("new_value    ") == DatabaseStatus.ALREADY_EXISTS
	assert insert_function("new      value     again") == DatabaseStatus.ALREADY_EXISTS
	assert insert_function("DROP TABLE artist;") == DatabaseStatus.OK

	assert insert_function("") == DatabaseStatus.EXCEPTION
	assert insert_function(" ") == DatabaseStatus.EXCEPTION
	assert insert_function(" \n\t ") == DatabaseStatus.EXCEPTION
	assert insert_function(None) == DatabaseStatus.EXCEPTION
	assert insert_function(123) == DatabaseStatus.EXCEPTION
	assert insert_function(3.14159) == DatabaseStatus.EXCEPTION
	assert insert_function(True) == DatabaseStatus.EXCEPTION
	assert insert_function([]) == DatabaseStatus.EXCEPTION
	assert insert_function({}) == DatabaseStatus.EXCEPTION
	assert insert_function(()) == DatabaseStatus.EXCEPTION
	assert insert_function(b"bytes") == DatabaseStatus.EXCEPTION
	assert insert_function(bytearray(b"data")) == DatabaseStatus.EXCEPTION


@pytest.mark.parametrize("n", [1, 5, 17, 31])
def test_insert_n_random_doujinshi(dbm, sample_n_random_doujinshi, n):
	doujinshi_list, _ = sample_n_random_doujinshi(n)
	for doujinshi in doujinshi_list:
		assert dbm.insert_doujinshi(doujinshi, False) == DatabaseStatus.OK
	for doujinshi in doujinshi_list:
		assert dbm.insert_doujinshi(doujinshi, False) == DatabaseStatus.ALREADY_EXISTS


@pytest.mark.parametrize("n", [1, 5, 17, 31])
def test_counts_after_insert(dbm, sample_n_random_doujinshi, n):
	doujinshi_list, expected_item_counts = sample_n_random_doujinshi(n)

	for doujinshi in doujinshi_list:
		dbm.insert_doujinshi(doujinshi, False)

	for item_type, expected_counts in expected_item_counts.items():
		dbm_get_count_of = getattr(dbm, f"get_count_of_{item_type}")
		actual_count = dbm_get_count_of(expected_counts.keys())
		for item_name in actual_count.keys():
			assert actual_count[item_name] == expected_counts[item_name]