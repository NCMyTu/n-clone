import re
from pathlib import Path


def extract_all_numbers(s):
	return [int(num) for num in re.findall(r'\d+', s)]


def is_non_empty_str(s):
    if not (isinstance(s, str) and s.strip()):
        return False
    return True


def create_empty_doujinshi():
	return {
		"id": None,
		"full_name": "",
		"full_name_original": "",
		"pretty_name": "",
		"pretty_name_original": "",
		"path": "",
		"pages": [],
		"note": "",

		"parodies": [],
		"characters": [],
		"tags": [],
		"artists": [],
		"groups": [],
		"languages": []
	}


def validate_doujinshi(doujinshi, user_prompt=True):
	# TODO: path must be in posix format
	errors = []
	warnings = []

	if not isinstance(doujinshi["id"], int):
		errors.append(f"id must be an int. Got {doujinshi["id"]!r} instead.")
	if not is_non_empty_str(doujinshi["full_name"]):
		errors.append("full_name must be a non-empty string.")
	if not is_non_empty_str(doujinshi["path"]):
		errors.append(f"path must be a non-empty string.")

	# cover_filename = doujinshi["cover_filename"]
	# if (isinstance(cover_filename, str) and (not cover_filename)) or isinstance(cover_filename, str):
	# 	errors.append(f"cover_filename must be a non-empty string.")

	# if not Path(doujinshi["cover_filename"]).as_posix().startswith(Path(doujinshi["path"]).as_posix()):
	# 	errors.append("cover_filename and path are mismatched.")

	required_fields = [
		("pretty_name", False),
		("full_name_original", False),
		("pretty_name_original", False),
		("path", False),

		("parodies", True),
		("characters", True),
		("tags", True),
		("artists", True),
		("groups", True),
		("languages", True),
		("pages", True),
	]

	for attr, is_a_list in required_fields:
		# Ughh...
		if attr not in doujinshi:
			errors.append(f"Missing required field: {attr}")
			continue
		
		value = doujinshi[attr]

		if is_a_list:
			if not isinstance(value, list):
				warnings.append(f"{attr} must be a list.")
				continue

			if not value:
				warnings.append(f"{attr} is empty.")
			else:
				for v in value:
					if isinstance(v, str) and v != v.strip():
						warnings.append(f"{attr}: {v!r} has leading/trailing spaces.")
		else:
			if not isinstance(value, str):
				warnings.append(f"{attr} must be a string.")
				continue

			if not value:
				warnings.append(f"{attr} is missing or empty.")
			else:
				if value != value.strip():
					warnings.append(f"{attr} has leading/trailing spaces.")

	if doujinshi["tags"] and "textless" in doujinshi["tags"]:
		warnings.append("Consider moving \"textless\" from tags to languages.")
	
	if doujinshi["languages"]:
		for lang in doujinshi["languages"]:
			if lang.strip() not in Doujinshi.VALID_LANGUAGES:
				warnings.append(f"Unknown language '{lang}'.")

	if (len(set(doujinshi["pages"])) != len(doujinshi["pages"])): 
		errors.append("pages has duplicate file names.")

	if (not warnings) and (not errors):
		return True

	if errors:
		print(f"Doujinshi #{doujinshi['id']} ERRORS:")
		for e in errors:
			print(f"\t{e}")
	if warnings:
		print(f"Doujinshi #{doujinshi['id']} WARNINGS:")
		for w in warnings:
			print(f"\t{w}")

	if not user_prompt:
		return False

	while True:
		answer = input("Do you really want to continue despite warnings? Y/n\n\t> ")
		if answer in ("Y", "n"):
			return answer == "Y"
		print("Please enter exactly 'Y' or 'n'.")


# d = create_empty_doujinshi()
# # d["id"] = 1
# d["path"] = "path"
# d["full_name"] = "full_name"

# validate_doujinshi(d, user_prompt=True)