import random


def _sample_n_random_doujinshi(n_doujinshi, random_state=2):
	random.seed(random_state)

	parodies = [f"parody_{i}" for i in range(0, 100)]
	characters = [f"character_{i}" for i in range(0, 100)]
	tags = [f"tag_{i}" for i in range(0, 100)]
	artists = [f"artist_{i}" for i in range(0, 100)]
	groups = [f"group_{i}" for i in range(0, 100)]
	languages = ["english", "japanese", "textless", "chinese"]
	pages = [f"page_{i}.jpg" for i in range(0, 500)]

	item_counts = {
		"parodies": {p: 0 for p in parodies},
		"characters": {c: 0 for c in characters},
		"tags": {t: 0 for t in tags},
		"artists": {a: 0 for a in artists},
		"groups": {g: 0 for g in groups},
		"languages": {l: 0 for l in languages}
	}

	doujinshi_list = []

	for d_id in range(1, n_doujinshi+1):
		doujinshi = {
			"id": d_id,
			"full_name": f"Test Doujinshi {d_id}", "pretty_name": "st Dou",
			"full_name_original": "元の名前", "pretty_name_original": "の名", # Must be japanese
			"path": f"inter/path/{d_id}", "note": "Test note",

			"parodies": random.sample(parodies, random.randint(1, len(parodies))),
			"characters": random.sample(characters, random.randint(1, len(characters))),
			"tags": random.sample(tags, random.randint(1, len(tags))),
			"artists": random.sample(artists, random.randint(1, len(artists))),
			"groups": random.sample(groups, random.randint(1, len(groups))),
			"languages": random.sample(languages, random.randint(1, len(languages))),
			"pages": random.sample(pages, random.randint(1, len(pages))),
		}

		for item_type in ["parodies", "characters", "tags", "artists", "groups", "languages"]:
			for item in doujinshi[item_type]:
				item_counts[item_type][item] += 1

		doujinshi_list.append(doujinshi)

	return doujinshi_list, item_counts