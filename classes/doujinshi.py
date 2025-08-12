import json
from pathlib import Path
from typing import Optional

class Doujinshi:
	# To concatenate with self.path (read from database)
	PATH_PREFIX = '' 

	
	@classmethod
	def set_path_prefix(cls, prefix):
		cls.PATH_PREFIX = prefix


	def __init__(self):
		self.id: int = -1
		self.path = ''

		self.full_name = None
		self.bold_name = None
		self.full_name_original = None
		self.bold_name_original = None
		self.cover_page_file_name = None # intended none
		self.added_at = None # pull from db
		self.note = None

		self.parodies = []
		self.characters = []
		self.tags = []

		self.artists = []
		self.groups = []
		self.languages = []

		self.page_order = []


	def from_data(self, 
		doujinshi_id, path, 
		full_name, bold_name,
		full_name_original, bold_name_original,
		cover_page_file_name,
		parodies, characters, tags,
		artists, groups,
		languages,
		page_order, added_at, note
	):
		self.id = doujinshi_id
		self.path = Path(path).as_posix()

		self.full_name = full_name
		self.bold_name = bold_name
		self.full_name_original = full_name_original
		self.bold_name_original = bold_name_original
		self.note = note

		self.parodies = parodies
		self.characters = characters
		self.tags = tags

		self.artists = artists
		self.groups = groups
		self.languages = languages

		self.page_order = page_order
		self.cover_page_file_name = cover_page_file_name
		self.added_at = added_at

		return self


	def from_partial_data(self, doujinshi_id, path, full_name, cover_page_file_name, languages):
		self.id = doujinshi_id
		self.path = Path(path).as_posix()
		self.full_name = full_name
		self.languages = languages
		self.cover_page_file_name = cover_page_file_name
		return self


	def reset(self):
		self.__init__()


	def construct_full_path_of_pages(self):
		self.page_order = [Path(self.PATH_PREFIX, p).as_posix() for p in self.page_order]
		self.cover_page_file_name = Path(self.PATH_PREFIX, self.page_order[0]).as_posix()


	def load_from_json(self, json_path):
		try:
			with open(Path(json_path), "r", encoding="utf-8") as f:
				data = json.load(f)
		except FileNotFoundError:
			print(f"File not found: {json_path}")
			return self
		except json.JSONDecodeError as e:
			print(f"JSON decode error: {e}")
			return self

		try:
			self.id = data["id"]
			self.path = data["path"]

			self.full_name = data["full_name"]
			self.bold_name = data["bold_name"]
			self.full_name_original = data["full_name_original"]
			self.bold_name_original = data["bold_name_original"]
			self.note = data["note"]

			self.parodies = data["parodies"]
			self.characters = data["characters"]
			self.tags = data["tags"]

			self.artists = data["artists"]
			self.groups = data["groups"]
			self.languages = data["languages"]

			self.page_order = data["page_order"]
			self.cover_page_file_name = data["page_order"][0]
		except KeyError as e:
			self.reset()
			print(f"Key doesnt exist. ERROR: {e}")

		return self


	def validate(self, user_warning=True):
		warnings = []
		errors = []

		# Critical checks (no exceptions)
		if not isinstance(self.id, int):
			errors.append(f"Doujinshi id must be an int. Got {self.id!r} instead.")
		if not isinstance(self.full_name, str) or not self.full_name.strip():
			errors.append(f"full_name must be a non-empty string.")
		if not isinstance(self.path, str) or not self.path.strip():
			errors.append(f"path must be a non-empty string.")

		if errors:
			print(f"Doujinshi #{getattr(self, 'id', '?')} ERRORS:")
			for e in errors:
				print(f"\t{e}")
			return False

		required_fields = [
			("bold_name", False),
			("full_name_original", False),
			("bold_name_original", False),
			("parodies", True),
			("characters", True),
			("tags", True),
			("artists", True),
			("groups", True),
			("languages", True),
			("page_order", True),
			("path", False),
			("cover_page_file_name", False)
		]

		for attr, can_be_a_list in required_fields:
			value = getattr(self, attr)
			if not value:
				warnings.append(f"{attr} is missing or empty.")
			else:
				if can_be_a_list and isinstance(value, list):
					for v in value:
						if isinstance(v, str) and v != v.strip():
							warnings.append(f"{attr}: {v!r} has leading/trailing spaces.")
				else:
					if isinstance(value, str) and value != value.strip():
						warnings.append(f"{attr} has leading/trailing spaces.")

		if "textless" in self.tags:
			warnings.append("Consider moving \"textless\" from tags to languages.")

		VALID_LANGUAGES = {"english", "japanese", "chinese", "textless"}
		for lang in self.languages:
			if lang.strip() not in VALID_LANGUAGES:
				warnings.append(f"Unknown language '{lang}'.")

		if not warnings:
			return True

		print(f"Doujinshi #{self.id} WARNINGS:")
		for w in warnings:
			print(f"\t{w}")

		if not user_warning:
			return False

		while True:
			answer = input("Do you really want to continue despite warnings? Y/n\n\t> ")
			if answer in ("Y", "n"):
				return answer == "Y"
			print("Please enter exactly 'Y' or 'n'.")


	def print_info(self):
		print("----------------------------------")
		print(f"id: {self.id}")
		print(f"path: {Path(self.path).as_posix()}\n")
		print(f"full_name: {self.full_name}")
		print(f"bold_name: {self.bold_name}")
		print(f"full_name_original: {self.full_name_original}")
		print(f"bold_name_original: {self.bold_name_original}\n")
		print(f"parodies: {'\n\t' + '\n\t'.join(self.parodies) if self.parodies else ''}")
		print(f"characters: {'\n\t' + '\n\t'.join(self.characters) if self.characters else ''}")
		print(f"tags: {'\n\t' + '\n\t'.join(self.tags) if self.tags else ''}")
		print(f"artists: {'\n\t' + '\n\t'.join(self.artists) if self.artists else ''}")
		print(f"groups: {'\n\t' + '\n\t'.join(self.groups) if self.groups else ''}")
		print(f"languages: {'\n\t' + '\n\t'.join(self.languages) if self.languages else ''}")
		print(f"page_order: {'\n\t' + '\n\t'.join(self.page_order) if self.page_order else ''}")
		print(f"added_at: {self.added_at}")
		print(f"note: {self.note}")
		print("----------------------------------")


	def to_json(self, path):
		with open(Path(path), "w", encoding="utf-8") as file:
			json.dump({
				"id": self.id,
				"path": Path(self.path).as_posix(), # defensive at its best
				"full_name": self.full_name,
				"bold_name": self.bold_name,
				"full_name_original": self.full_name_original,
				"bold_name_original": self.bold_name_original,
				"parodies": self.parodies,
				"characters": self.characters,
				"tags": self.tags,
				"artists": self.artists,
				"groups": self.groups,
				"languages": self.languages,
				"page_order": self.page_order,
				"note": self.note
			}, file, ensure_ascii=False, indent=4)


if __name__ == "__main__":
	doujinshi = [Doujinshi().load_from_json(f"../test/doujin_{i}.json") for i in range(1, 4)]
	
	for d in doujinshi:
		d.print_info()

	print(doujinshi[0].validate(False))