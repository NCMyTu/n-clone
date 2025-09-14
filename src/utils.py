import re
from pathlib import Path


VALID_LANGUAGES = ["english", "japanese", "textless", "chinese"]


def extract_all_numbers(s):
	return [int(num) for num in re.findall(r'\d+', s)]


def is_non_empty_str(s):
	if not (isinstance(s, str)):
		return False
	if not s.strip():
		return False
	return True


def validate_doujinshi(doujinshi, user_prompt=True):
	errors = []
	warnings = []

	if not isinstance(doujinshi, dict):
		print(f"ERRORS:\n\tdoujinshi must be a dict. Got {type(doujinshi)} instead.")
		return False
	if isinstance(doujinshi["id"], bool):
		errors.append(f"id must be an int. Got {doujinshi["id"]!r} instead.")
	if not isinstance(doujinshi["id"], int):
		errors.append(f"id must be an int. Got {doujinshi["id"]!r} instead.")
	if not is_non_empty_str(doujinshi["full_name"]):
		errors.append("full_name must be a non-empty string.")

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
				if len(value) != len(set(value)):
					errors.append(f"{attr} has duplicate elements.")

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

		if attr in ["parodies", "characters", "tags", "artists", "groups", "languages"]:
			if value != [v.lower() for v in value]:
				errors.append(f"{attr} has uppercase character.")

	# Put this here to pass the test
	if not is_non_empty_str(doujinshi["path"]):
		errors.append(f"path must be a non-empty string.")
	elif doujinshi["path"] and doujinshi["path"] != Path(doujinshi["path"]).as_posix():
		warnings.append("path should use POSIX-style separator (no \\)")

	if doujinshi["tags"] and "textless" in doujinshi["tags"]:
		warnings.append("Consider moving \"textless\" from tags to languages.")
	
	if doujinshi["languages"]:
		for lang in doujinshi["languages"]:
			if lang.strip() not in VALID_LANGUAGES:
				warnings.append(f"Unknown language '{lang}'.")

	if (len(set(doujinshi["pages"])) != len(doujinshi["pages"])): 
		errors.append("pages has duplicate file names.")

	if (not warnings) and (not errors):
		# print("-" * 50)
		return True

	print(f"{"-" * 50}\nDoujinshi #{doujinshi['id']}")

	if errors:
		print(f"ERRORS:")
		for e in errors:
			print(f"\t{e}")
	if warnings:
		print(f"WARNINGS:")
		for w in warnings:
			print(f"\t{w}")

	if errors:
		print("-" * 50)
		return False

	if not user_prompt:
		print("-" * 50)
		return True

	while True:
		answer = input("Do you really want to continue despite warnings? Y/n\n\t> ")
		if answer in ("Y", "n"):
			print("-" * 50)
			return answer == "Y"
		print("Please enter exactly 'Y' or 'n'.")