def _sample_doujinshi(doujinshi_id):
	return {
		"id": doujinshi_id,

		"full_name": f"Test Doujinshi {doujinshi_id}", "pretty_name": "st Dou",
		"full_name_original": "元の名前", "pretty_name_original": "の名", # Must be japanese
		"path": f"inter/path/{doujinshi_id}",
		"note": "Test note",

		"parodies": [f"parody_{i}" for i in range(1, 4)],
		"characters": [f"character_{i}" for i in range(5)],
		"tags": [f"tag_{i}" for i in range(1, 4)],
		"artists": [f"artist_{i}" for i in range(1, 5)],
		"groups": [f"group_{i}" for i in range(1, 6)],
		"languages": [f"language_{i}" for i in range(1, 6)],
		"pages": [f"f_{i}.jpg" for i in range(1, 31)]
	}