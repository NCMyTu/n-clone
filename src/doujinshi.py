import json
from pathlib import Path


class Doujinshi:
	# To concatenate with self.path (read from database)
	PATH_PREFIX = ''
	VALID_LANGUAGES = ("english", "japanese", "chinese", "textless")


	@classmethod
	def set_path_prefix(cls, prefix):
		cls.PATH_PREFIX = prefix


	def __init__(self):
		self.id = -1
		self.path = None

		self.full_name = None
		self.bold_name = None
		self.full_name_original = None
		self.bold_name_original = None
		self.added_at = None # pull this from db.
		self.note = None

		self.parodies = []
		self.characters = []
		self.tags = []

		self.artists = []
		self.groups = []
		self.languages = []

		self._page_order = []
		self.page_order = []
		self.cover_path = None


	def reset(self):
		self.__init__()


	def ready(self):
		self.page_order = [Path(self.PATH_PREFIX, self.path, p).as_posix() for p in self._page_order]
		if self.page_order:
			self.cover_path = Path(self.page_order[0]).as_posix()
		return self


	def from_data(self, 
		doujinshi_id, path, 
		full_name, bold_name,
		full_name_original, bold_name_original,
		parodies, characters, tags,
		artists, groups,
		languages,
		_page_order, added_at, note
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
		self._page_order = _page_order
		self.cover_path = Path(self.PATH_PREFIX, self.path, _page_order[0]).as_posix()
		self.added_at = added_at
		return self


	def from_partial_data(self, doujinshi_id, path, full_name, cover_file_name, languages):
		self.id = doujinshi_id
		self.path = Path(path).as_posix()
		self.full_name = full_name
		self.languages = languages
		self.cover_path = Path(self.PATH_PREFIX, self.path, cover_file_name).as_posix()
		return self


	def load_from_json(self, json_path):
		# IMPORTANT: reset if an exception occurs.
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
			self.path = Path(data["path"]).as_posix()

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

			self._page_order = data["_page_order"]
			self.cover_path = Path(self.PATH_PREFIX, self.path, self._page_order[0]).as_posix()
		except KeyError as e:
			self.reset()
			print(f"Key doesnt exist. ERROR: {e}")
		except Exception as e:
			self.reset()
			print(f"Unexpected exception. ERROR: {e}")

		return self


	def validate(self, user_prompt=True):
		warnings = []
		errors = []

		if not isinstance(self.id, int):
			errors.append(f"Doujinshi id must be an int. Got {self.id!r} instead.")
		if not isinstance(self.full_name, str) or not self.full_name.strip():
			errors.append(f"full_name must be a non-empty string.")
		if not isinstance(self.path, str) or not self.path.strip():
			errors.append(f"path must be a non-empty string.")
		if not isinstance(self.PATH_PREFIX, str) or not self.PATH_PREFIX.strip():
			warnings.append(f"PATH_PREFIX must be a non-empty string.")

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
			("_page_order", True),
			("path", False),
			("cover_path", False)
		]

		for attr, is_a_list in required_fields:
			# Ughh...
			value = getattr(self, attr)

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

		if self.tags and "textless" in self.tags:
			warnings.append("Consider moving \"textless\" from tags to languages.")
		
		if self.languages:
			for lang in self.languages:
				if lang.strip() not in Doujinshi.VALID_LANGUAGES:
					warnings.append(f"Unknown language '{lang}'.")

		# Database can recognize other duplicate elemnent in other properties but not page order,
		# also put it here will make it meet user eyes first.
		if (len(set(self.page_order)) != len(self.page_order)) or (len(set(self._page_order)) != len(self._page_order)):
			errors.append("_page_order or page_order has duplicate file names.")

		if (not warnings) and (not errors):
			return True

		if errors:
			print(f"Doujinshi #{getattr(self, 'id', '?')} ERRORS:")
			for e in errors:
				print(f"\t{e}")
		if warnings:
			print(f"Doujinshi #{getattr(self, 'id', '?')} WARNINGS:")
			for w in warnings:
				print(f"\t{w}")

		print("FINAL WARNING: Always check if the paths are correct.")
		
		if not user_prompt:
			return False

		while True:
			answer = input("Do you really want to continue despite warnings? Y/n\n\t> ")
			if answer in ("Y", "n"):
				return answer == "Y"
			print("Please enter exactly 'Y' or 'n'.")


	def print_info(self):
		print("----------------------------------")
		print(f"id: {self.id}")
		print(f"path: {Path(self.path).as_posix() if (self.path and self.path.strip()) else "______NOT FOUND______"}\n")
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
		print(f"cover_path: {self.cover_path}")
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
				"_page_order": self._page_order,
				"note": self.note
			}, file, ensure_ascii=False, indent=4)


if __name__ == "__main__":
	Doujinshi.set_path_prefix("path_prefix")
	doujinshi = [Doujinshi().load_from_json(f"../tests/fake_data/doujinshi_{i}.json").ready() for i in range(3)]
	
	# for d in doujinshi:
	# 	d.print_info()

	# doujinshi[0].path = None
	doujinshi[0].print_info()
	print(doujinshi[0].validate(True))
