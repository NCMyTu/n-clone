import json
from pathlib import Path
from typing import Optional

class Doujinshi:
	path_prefix = ''

	def __init__(self):
		self.id = None
		self.path = ''

		self.full_name: Optional[str] = None
		self.bold_name: Optional[str] = None
		self.full_name_original: Optional[str] = None
		self.bold_name_original: Optional[str] = None
		self.cover_page_file_name: Optional[str] = None # intended none
		self.added_at = None # pull from db
		self.note: Optional[str] = None

		self.parodies = []
		self.characters = []
		self.tags = []

		self.artists = []
		self.groups = []
		self.languages = []

		self.page_order = []


	def from_data(self, doujinshi_id, path, 
		full_name, bold_name,
		full_name_original, bold_name_original,
		note,
		parodies,
		characters,
		tags,
		artists, groups,
		languages,
		page_order
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


	@classmethod
	def set_path_prefix(cls, prefix):
		cls.path_prefix = prefix


	def reset(self):
		self.__init__()


	def load_from_json(self, json_path):
		try:
			with open(Path(json_path), "r", encoding="utf-8") as f:
				data = json.load(f)
		except FileNotFoundError:
			print(f"File not found: {json_path}")
			return
		except json.JSONDecodeError as e:
			print(f"JSON decode error: {e}")
			return

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
		except KeyError as e:
			self.reset()
			print(f"Key doesnt exist. ERROR: {e}")


	def strict_mode(self):
		required_fields = {
			"bold_name": "bold_name is missing",
			"full_name_original": "full_name_original is missing",
			"bold_name_original": "bold_name_original is missing",
			"artists": "artists is missing or empty",
			"groups": "groups is missing or empty",
			"languages": "languages is missing or empty",
			"page_order": "page_order is missing or empty",
		}

		is_ok = True
		for attr, warning in required_fields.items():
			if not getattr(self, attr):
				print(f"Doujinshi id #{self.id}, WARNING: {warning}")
				is_ok = False

		if is_ok:
			return True

		# Ask user to continue only if not ok
		answer = input("Do you want to continue? Y/n\n\t>>> ").strip()
		return answer.upper() == "Y"


	def print_info(self):
		print("----------------------------------")
		print(f"id: {self.id}")
		print(f"path: {self.path}\n")
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
		print(f"note: {self.note}")
		print("----------------------------------")


	def to_json(self, path):
		with open(Path(path), "w", encoding="utf-8") as file:
			json.dump({
				"id": self.id,
				"path": self.path,
				"full": self.full_name,
				"bold_name": self.bold_name,
				"full_name_original": self.full_name_original,
				"bold_name_original": self.bold_name_original,
				"note": self.note,
				"parodies": self.parodies,
				"characters": self.characters,
				"tags": self.tags,
				"artists": self.artists,
				"groups": self.groups,
				"languages": self.languages,
				"page_order": self.page_order,
			}, file, ensure_ascii=False, indent=4)

if __name__ == "__main__":
	d = Doujinshi()
	d.load_from_json("../../doujin_data.json")
	d.print_info()