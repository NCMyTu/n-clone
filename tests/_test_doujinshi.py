import pytest
import json
from pathlib import Path
from classes.doujinshi import Doujinshi


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
		"added_at": "2025-01-01",
	}


@pytest.fixture
def doujinshi(sample_data):
	return Doujinshi().from_data(**sample_data)


def test_from_data_and_ready(doujinshi, sample_data):
	assert doujinshi.id == 1
	assert doujinshi.path == "inter/path"
	assert doujinshi.cover_path.endswith("PREFIX/inter/path/1_1.jpg")
	
	doujinshi.ready()
	expected_page_order = [f"PREFIX/inter/path/{p}" for p in sample_data["_page_order"]]
	assert doujinshi.page_order == expected_page_order
	assert doujinshi.cover_path.endswith("PREFIX/inter/path/1_1.jpg")


def test_from_partial_data_and_ready():
	doujinshi = Doujinshi().from_partial_data(2, "inter2\\path", "Partial Name", "cover.jpg", ["japanese"])
	assert doujinshi.id == 2
	assert doujinshi.path == "inter2/path"
	assert doujinshi.cover_path.endswith("PREFIX/inter2/path/cover.jpg")
	assert doujinshi.languages == ["japanese"]

	doujinshi.ready()
	assert not doujinshi.page_order
	assert doujinshi.cover_path.endswith("PREFIX/inter2/path/cover.jpg")


def test_reset(doujinshi, sample_data):
	doujinshi = Doujinshi().from_data(**sample_data)
	doujinshi.reset()
	assert doujinshi.id == -1
	assert not doujinshi.path
	assert doujinshi.full_name is None


def test_to_json_and_load_from_json(doujinshi, sample_data, tmp_path):
	json_path = tmp_path / "test.json"
	doujinshi.to_json(json_path)

	# Load back
	doujinshi_json = Doujinshi().load_from_json(json_path)
	assert doujinshi_json.id == sample_data["doujinshi_id"]
	assert doujinshi_json.full_name_original == sample_data["full_name_original"]
	assert doujinshi_json.bold_name_original == sample_data["bold_name_original"]
	assert doujinshi_json._page_order == sample_data["_page_order"]
	doujinshi_json.ready()
	assert doujinshi_json.page_order == [f"PREFIX/inter/path/{p}" for p in sample_data["_page_order"]]


def test_load_from_json_file_not_found():
	d = Doujinshi().load_from_json("no_path.json")
	assert d.id == -1  # unchanged from default


def test_load_from_json_invalid_json(tmp_path):
	bad_json_path = tmp_path / "bad.json"
	bad_json_path.write_text("{invalid json}", encoding="utf-8")
	d = Doujinshi().load_from_json(bad_json_path)
	assert d.id == -1


def test_print_info_output(doujinshi, sample_data, capsys):
	doujinshi.ready()
	doujinshi.print_info()
	captured = capsys.readouterr()
	assert str(sample_data["doujinshi_id"]) in captured.out
	assert sample_data["full_name"] in captured.out
	assert sample_data["bold_name"] in captured.out
	assert sample_data["full_name_original"] in captured.out
	assert sample_data["bold_name_original"] in captured.out
	assert "\n\t".join(sample_data["parodies"]) in captured.out
	assert "\n\t".join(sample_data["characters"]) in captured.out
	assert "\n\t".join(sample_data["tags"]) in captured.out
	assert "\n\t".join(sample_data["artists"]) in captured.out
	assert "\n\t".join(sample_data["groups"]) in captured.out
	assert "\n\t".join(sample_data["languages"]) in captured.out
	assert sample_data["note"] in captured.out

	expected_page_order = [f"PREFIX/inter/path/{p}" for p in sample_data["_page_order"]]
	assert "\n\t".join(expected_page_order) in captured.out


def test_validate_success(doujinshi):
	doujinshi.ready()
	assert doujinshi.validate(user_prompt=False) is True


def run_all_prompt_cases(d, monkeypatch):
	# Case 1: Direct "Y"
	monkeypatch.setattr("builtins.input", lambda _: "Y")
	assert d.validate(user_prompt=True) is True

	# Case 2: Direct "n"
	monkeypatch.setattr("builtins.input", lambda _: "n")
	assert d.validate(user_prompt=True) is False

	# Case 3: Invalid first, then "Y"
	inputs = iter(["bad", "Y"])
	monkeypatch.setattr("builtins.input", lambda _: next(inputs))
	assert d.validate(user_prompt=True) is True

	# Case 4: Invalid first, then "n"
	inputs = iter(["wrong", "n"])
	monkeypatch.setattr("builtins.input", lambda _: next(inputs))
	assert d.validate(user_prompt=True) is False


def run_test_with_and_without_prompt(d, capsys, monkeypatch, error_or_warning):
	is_valid = d.validate(user_prompt=False)
	captured = capsys.readouterr()
	assert is_valid is False
	assert error_or_warning in captured.out
	run_all_prompt_cases(d, monkeypatch)


def test_validate_id(doujinshi, capsys, monkeypatch):
	doujinshi.id = "a"
	doujinshi.ready()
	run_test_with_and_without_prompt(doujinshi, capsys, monkeypatch, "ERRORS")


@pytest.mark.parametrize("prefix", [1, "", " ", None])
def test_validate_path_prefix(doujinshi, prefix, capsys, monkeypatch):
	Doujinshi.set_path_prefix(prefix)
	run_test_with_and_without_prompt(doujinshi, capsys, monkeypatch, "WARNINGS")


@pytest.mark.parametrize("path", [1, "", " ", None])
def test_validate_path(doujinshi, path, capsys, monkeypatch):
	doujinshi.path = path
	run_test_with_and_without_prompt(doujinshi, capsys, monkeypatch, "ERRORS")


@pytest.mark.parametrize("full_name", [1, "", " ", None])
def test_validate_full_name(doujinshi, full_name, capsys, monkeypatch):
	doujinshi.full_name = full_name
	run_test_with_and_without_prompt(doujinshi, capsys, monkeypatch, "ERRORS")


@pytest.mark.parametrize("full_name_original", ["", " ", None])
def test_validate_full_name_original(doujinshi, full_name_original, capsys, monkeypatch):
	doujinshi.full_name_original = full_name_original
	run_test_with_and_without_prompt(doujinshi, capsys, monkeypatch, "WARNINGS")


@pytest.mark.parametrize("bold_name", ["", " ", None])
def test_validate_bold_name(doujinshi, bold_name, capsys, monkeypatch):
	doujinshi.bold_name = bold_name
	run_test_with_and_without_prompt(doujinshi, capsys, monkeypatch, "WARNINGS")


@pytest.mark.parametrize("bold_name_original", ["", " ", None])
def test_validate_bold_name_original(doujinshi, bold_name_original, capsys, monkeypatch):
	doujinshi.bold_name_original = bold_name_original
	run_test_with_and_without_prompt(doujinshi, capsys, monkeypatch, "WARNINGS")


@pytest.mark.parametrize("cover_path", ["", " ", None])
def test_validate_cover_path(doujinshi, cover_path, capsys, monkeypatch):
	doujinshi.cover_path = cover_path
	run_test_with_and_without_prompt(doujinshi, capsys, monkeypatch, "WARNINGS")


@pytest.mark.parametrize("parodies", ["", " ", None, "temp", []])
def test_validate_parodies(doujinshi, parodies, capsys, monkeypatch):
	doujinshi.parodies = parodies
	run_test_with_and_without_prompt(doujinshi, capsys, monkeypatch, "WARNINGS")


@pytest.mark.parametrize("characters", ["", " ", None, "temp", []])
def test_validate_characters(doujinshi, characters, capsys, monkeypatch):
	doujinshi.characters = characters
	run_test_with_and_without_prompt(doujinshi, capsys, monkeypatch, "WARNINGS")


@pytest.mark.parametrize("tags", ["", " ", None, "textless", [], ["textless"]])
def test_validate_tags(doujinshi, tags, capsys, monkeypatch):
	doujinshi.tags = tags
	run_test_with_and_without_prompt(doujinshi, capsys, monkeypatch, "WARNINGS")


@pytest.mark.parametrize("artists", ["", " ", None, "temp", []])
def test_validate_artists(doujinshi, artists, capsys, monkeypatch):
	doujinshi.artists = artists
	run_test_with_and_without_prompt(doujinshi, capsys, monkeypatch, "WARNINGS")


@pytest.mark.parametrize("groups", ["", " ", None, "temp", []])
def test_validate_groups(doujinshi, groups, capsys, monkeypatch):
	doujinshi.groups = groups
	run_test_with_and_without_prompt(doujinshi, capsys, monkeypatch, "WARNINGS")


@pytest.mark.parametrize("languages", ["", " ", None, "temp", [], ["unknown lang"]])
def test_validate_languages(doujinshi, languages, capsys, monkeypatch):
	doujinshi.languages = languages
	run_test_with_and_without_prompt(doujinshi, capsys, monkeypatch, "WARNINGS")

@pytest.mark.parametrize("page_order", ["", " ", "temp", []])
def test_validate_page_order(doujinshi, page_order, capsys, monkeypatch):
	doujinshi.page_order = page_order
	run_test_with_and_without_prompt(doujinshi, capsys, monkeypatch, "WARNINGS")


def test_validate_page_order_duplicate(doujinshi, capsys):
	doujinshi._page_order = ["duplicate.jpg", "duplicate.jpg"]
	is_valid = doujinshi.validate(user_prompt=False)
	captured = capsys.readouterr()
	assert is_valid is False
	assert "duplicate file names." in captured.out
	doujinshi.ready()
	is_valid = doujinshi.validate(user_prompt=False)
	captured = capsys.readouterr()
	assert is_valid is False
	assert "duplicate file names." in captured.out