from pathlib import Path
import filetype
import re
import sys
import json

def convert_to_dict(obj):
	if isinstance(obj, dict):
		return {k: convert_to_dict(v) for k, v in obj.items()}
	elif isinstance(obj, list):
		return [convert_to_dict(i) for i in obj]
	elif isinstance(obj, Path):
		return str(obj)
	elif hasattr(obj, '__dict__'):
		return convert_to_dict(vars(obj))
	else:
		return obj

def deep_getsizeof(obj, seen=None):
	if seen is None:
		seen = set()
	obj_id = id(obj)
	if obj_id in seen:
		return 0
	seen.add(obj_id)

	size = sys.getsizeof(obj)

	if isinstance(obj, dict):
		size += sum(deep_getsizeof(k, seen) + deep_getsizeof(v, seen) for k, v in obj.items())
	elif hasattr(obj, '__dict__'):
		size += deep_getsizeof(obj.__dict__, seen)
	elif isinstance(obj, (list, tuple, set, frozenset)):
		size += sum(deep_getsizeof(i, seen) for i in obj)
	
	return size

def extract_all_numbers(s):
	return [int(num) for num in re.findall(r'\d+', s)]

class Doujin:
	def __init__(self, path):
		lang = Path(path).name.split()[-1]
		if lang == "JP":
			lang = "japanese"
		elif lang == "CN":
			lang = "chinese"
		else:
			lang = "english"

		metadata = self.parse_metadata(Path(path), Path(path).name)

		self.id = metadata["idx"]
		self.full_name = metadata["full_name"]
		self.bold_name = ""
		self.full_name_original = metadata["full_name_org"]
		self.bold_name_original = ""
		self.path = Path(*Path(path).parts[-4:]).as_posix()
		self.cover_page_id = None
		self.parodies = metadata["parodies"]
		self.characters = metadata["characters"]
		self.tags = metadata["tags"]
		self.artists = []
		self.groups = []
		self.languages = [lang]
		self.page_order = []

	def print(self):
		print(f"--------doujin info--------")
		print(f"path: {self.path.as_posix()}")
		print(f"id: {self.id}")
		print(f"full_name: {self.full_name}")
		print(f"full_name_org: {self.full_name_org}")
		print(f"parodies: {self.parodies}")
		print(f"characters: {self.characters}")
		print(f"tags: {self.tags}")
		print(f"artist: {self.artist}")
		print(f"group: {self.group}")
		print(f"num_pages: {self.num_pages}")
		print(f"img_list: {self.page_order}")
		print("----------------------------")

	def parse_metadata(self, path, name):
		metadata = {
			"parodies": [],
			"characters": [],
			"tags": [],
		}
		
		metadata_file_path = Path(path) / f"{name}.txt"
		lines = metadata_file_path.read_text(encoding="utf-8").split("\n")

		pointer = 0

		metadata["full_name"] = lines[pointer]
		pointer += 1
		metadata["full_name_org"] = lines[pointer] if lines[pointer].strip() != "" else None
		pointer += 1

		current_bin = None
		while pointer < len(lines):
			line = lines[pointer].strip()

			if line.startswith("#"):
				metadata["idx"] = int(line[1:])
			elif line == "Parodies:":
				current_bin = "parodies"
			elif line == "Characters:":
				current_bin = "characters"
			elif line == "Tags:":
				current_bin = "tags"

			if current_bin and line != "" and line.lower()[:-1] != current_bin:
				metadata[current_bin].append(line)

			pointer += 1

		metadata["parodies"].sort()
		metadata["characters"].sort()
		metadata["tags"].sort()

		return metadata

	def read_img_info(self, path, numerically=True):
		img_names = []

		for child in path.iterdir():
			if filetype.is_image(child.as_posix()):
				img_names.append(child.name)

		if numerically == True:
			return sorted(img_names, key=extract_all_numbers)
		elif numerically == False:
			return sorted(img_names)


if __name__ == "__main__":
	path = ""

	doujinshi_paths = sorted([p for p in Path(path).iterdir() if p.is_dir()])
	
	current_index = 1

	with open("../doujin_data.json", "w", encoding="utf-8") as f:
		d = Doujin(doujinshi_paths[current_index].as_posix())
		data = convert_to_dict(d)
		print(f"total doujinshis: {len(doujinshi_paths)}")
		print(f"current index: {current_index}")
		json.dump(data, f, indent=4, ensure_ascii=False)

	# ALWAYS CHECK:
	# 	BOLD NAME
	# 	BOLD NAME ORIGINAL
	# 	ARTISTS
	#	GROUPS
	#	LANGUAGES