import pytest
from pathlib import Path
from src import DatabaseStatus


@pytest.mark.parametrize("invalid_field",[
	"id",
	"full_name", "full_name_original", "pretty_name", "pretty_name_original",
	"path", "note"
])
@pytest.mark.parametrize("invalid_value",[
	None,
	"", " ", " \n\t  ",
	[], (), set(), {},
	1.23, True, object(),
])
def test_insert_doujinshi_invalid_field(dbm, sample_doujinshi, invalid_field, invalid_value):
	sample_doujinshi[invalid_field] = invalid_value
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
	assert method("with \"apostrophe' ") == DatabaseStatus.OK

	assert method("NEW_VALUE") == DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
	assert method("new_value    ") == DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
	assert method("new         value          again") == DatabaseStatus.NON_FATAL_ITEM_DUPLICATE
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


# TODO: check count of items