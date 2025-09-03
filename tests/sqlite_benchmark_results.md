# SQLite Benchmark Results
Summarize database performance benchmarks. As the title suggests, this is specific to SQLite. Benchmark again when you change the underlying database.

---

## Some definitions
* `Doujinshi`: You know.
* `Item type`: One of these: `Parody`, `Character`, `Tag`, `Artist`, `Group`, `Language`, `Page`.
* `Item`: An instance of an item type.
* `Extra index`: A manually created index (`{item_type_id}, doujinshi_id`) on many-to-many table (`doujinshi_{item_type}`) as opposed to the automatically created index (`doujinshi_id, {item_type_id}`).
* **Note**: the underlying name of `Item type` `Group` is `circle` to avoid reserved keyword in SQLite.

---

## 1. Insert doujinshi
* Insert 1,000,000 randomly generated (with fixed seed) `doujinshi` in batches of 10,000.
* Number of items by type:  
  * `Parody`, `Tag`, `Character`, `Artist`, and `Group`: 500 each.
  * `Language`: 4.
  * `Page`: up to 250 per `doujinshi`.
* Item distribution by type:  
  * Each `item type` (except `Page`) has a **97%** chance to sample without replacement a random number of items from **base_min** up to **base_max**, and a **3%** chance to sample without replacement a random number of items from **rare_max** up to the total number of items.
  * `Page` has an **85%** chance to sample the number of pages from a Gaussian distribution with **mean 25** and **stddev 7**, and a **15%** chance with **mean 200** and **stddev 50**. The number of pages is **clamped** between **1** and **250**.
* Run with these flags: {UPDATE HERE}

| Item type | base_min | base_max | rare_max |
|-----------|---------:|---------:|---------:|
| Parody    | 0 | 2  | 10  |
| Character | 0 | 4  | 20  |
| Tag       | 0 | 15 | 100 |
| Artist    | 0 | 2  | 30  |
| Group     | 0 | 1  | 3   |
| Language  | 1 | 1  | 2   |

* Results:
  * **Note**: `Doujinshi` and `items` are inserted directly into the database using IDs (so no duplicate or violation checks are performed). Therefore, insert time is faster than when using the actual insert method provided by `DatabaseManager`, which will be slower due to validation overhead.
  * File size is calculated after running the command `VACUUM`.
  * Insert time is not shown for configurations with `extra index`, since indices can just be created after insertion (definitely not because I don't have the patience to wait another 1000+ seconds).

| Configuration                 | File size (gb) | Insert time (s) |
|-------------------------------|----------:|--------:|
| With ROWID, no extra index    | 4.9111 | 1099.15 |
| With ROWID, extra index       | 5.6435 |         |
| Without ROWID, no extra index | 2.7552 | 1046.06 |
| Without ROWID, extra index    | 3.2811 |         |

* Number of rows inserted:

| Table               |       Rows |
|---------------------|-----------:|
| doujinshi_parody    | 8,554,800  |
| doujinshi_character | 9,813,695  |
| doujinshi_tag       | 16,264,622 |
| doujinshi_artist    | 8,994,647  |
| doujinshi_circle    | 8,029,873  |
| doujinshi_language  | 1,060,181  |
| page                | 50,089,160 |
| **Total**           | **102,157,978** |

> **TLDR**: ROWID tables are ~2 GB larger than WITHOUT ROWID, but insertion times are comparable.

---

## 2. update_count_of_all
* Measure in **seconds** how long it takes to count how many `doujinshi` each `item type` has.
* Run **n_times** times.
* Results:

| Configuration                 | n_times | min | max | avg |
|-------------------------------|--------:|----:|----:|----:|
| With ROWID, no extra index    | 10  | 18.48 | 19.89 | 19.50 |
| With ROWID, extra index       | 100 | 3.02  | 3.73  | 3.18  |
| Without ROWID, no extra index | 10  | 16.55 | 20.44 | 18.25 |
| Without ROWID, extra index    | 100 | 2.67  | 6.60  | 3.05  |

> **TLDR**: Extra index is critical.

---

## 3. get_doujinshi
* Measure in **milliseconds** how long it takes to retrieve 1 `doujinshi` from database.
* Report metrics: average (**avg**), 95th percentile (**p95**), 99th percentile (**p99**).
* Each run has a warm-up: fetch **20** `doujinshi` at evenly spaced IDs from 1 to 1,000,000, then run **Predictable Access** or **Random Access**.

### Predictable access
* Fetch **1,000** `doujinshi` starting from **id_start**, with step size **step**.
* Results:

| Configuration | id_start | step | avg | p50 | p95 | p99 |
|---------------|---------:|-----:|----:|----:|----:|----:|
| With ROWID, no extra index | 3,000   | 2 | 6.87 | 6.29 | 10.68 | 13.56 |
|                            | 499,799 | 4 | 6.75 | 6.19 | 10.66 | 13.28 |
|                            | 975,172 | 7 | 6.83 | 6.22 | 11.17 | 13.91 |
| |  | **Overall**                         | **6.82** | **6.24** | **10.79** | **13.91** |
| With ROWID, extra index | 3,000   | 2 | 6.47 | 5.84 | 10.50 | 13.54 |
|                         | 499,799 | 4 | 6.57 | 5.98 | 10.69 | 13.89 |
|                         | 975,172 | 7 | 6.85 | 6.16 | 11.03 | 13.89 |
|  |  | **Overall**                     | **6.63** | **6.01** | **10.76** | **13.54** |
| Without ROWID, no extra index | 3,000   | 2 | 6.76 | 5.85 | 10.77 | 14.74 |
|                               | 499,799 | 4 | 6.70 | 5.92 | 10.57 | 14.16 |
|                               | 975,172 | 7 | 6.97 | 6.13 | 11.01 | 14.59 |
|  |  | **Overall**                           | **6.81** | **5.96** | **10.88** | **14.70** |
| Without ROWID, extra index | 3,000   | 2 | 6.99 | 6.11 | 10.88 | 16.21 |
|                            | 499,799 | 4 | 6.99 | 6.14 | 11.04 | 14.71 |
|                            | 975,172 | 7 | 6.81 | 6.00 | 10.75 | 14.03 |
|  |  | **Overall**                        | **6.93** | **6.09** | **10.90** | **15.14** |

### Random access
* Fetch **1,000** random `doujinshi` between **id_start** and **id_end**.
* Results:

| Configuration | id_start | id_end | avg | p50 | p95 | p99 |
|---------------|---------:|-------:|----:|----:|----:|----:|
| With ROWID, no extra index | 100     | 50,000    | 6.47 | 5.93 | 10.37 | 13.13 |
|                            | 470,011 | 610,010   | 6.55 | 5.98 | 10.48 | 13.10 |
|                            | 700,001 | 1,000,000 | 6.77 | 6.21 | 10.69 | 13.58 |
|  |  | **Overall**                                | **6.60** | **6.02** | **10.50** | **13.34** |
| With ROWID, extra index | 100     | 50,000    | 6.76 | 6.10 | 10.87 | 14.68 |
|                         | 470,011 | 610,010   | 6.69 | 6.07 | 10.64 | 14.93 |
|                         | 700,001 | 1,000,000 | 6.55 | 6.09 | 10.15 | 12.49 |
|  |  | **Overall**                             | **6.67** | **6.09** | **10.62** | **14.10** |
| Without ROWID, no extra index | 100     | 50,000    | 7.09 | 6.19 | 10.91 | 13.83 |
|                               | 470,011 | 610,010   | 7.59 | 6.46 | 12.33 | 18.49 |
|                               | 700,001 | 1,000,000 | 7.27 | 6.42 | 11.00 | 15.83 |
|  |  | **Overall**                                   | **7.32** | **6.36** | **11.47** | **15.98** |
| Without ROWID, extra index | 100     | 50,000    | 6.97 | 6.03 | 10.98 | 13.94 |
|                            | 470,011 | 610,010   | 7.23 | 6.31 | 11.35 | 16.20 |
|                            | 700,001 | 1,000,000 | 7.56 | 6.57 | 12.01 | 16.39 |
|  |  | **Overall**                                | **7.25** | **6.33** | **11.51** | **15.52** |

* **Note**: Results vary significantly between runs. Measurements with **1,000** iterations differ from those with **10,000**, and even repeated **1,000**-run tests produce inconsistent results. This kind of benchmark is not reliable.

> **TLDR**: Differences between configs are small.

---

## 4. get_doujinshi_in_batch
* Measure in **milliseconds** how long it takes to fetch 1 page.
* Each page has 25 doujinshi (`id`, `full_name`, `path`, `cover_filename`). Note that page here is different from the item type `page`.
* Use WITHOUT ROWID.
* Fetch from **page_start** to **page_end**, shuffled.
* The first iteration has this (ORM translated to) SQL:
```sql
SELECT
    doujinshi.id,
    doujinshi.full_name,
    doujinshi.path,
    page.filename
FROM doujinshi JOIN page ON doujinshi.id = page.doujinshi_id
WHERE page.order_number = 1
ORDER BY doujinshi.id DESC
LIMIT 25
OFFSET :page_number
```
(commit fc7abf8e7541e303c72cc621be7b7770975da36f has a redundant WHERE clause)

I only fetch **10** pages, the reason why is explained below:

| page_start | page_end | avg | p50 | p95 | p99 |
|-----------:|---------:|----:|----:|----:|----:|
| 1      | 11     | 371.56 | 344.04 | 507.29  | 561.17  |
| 19,995 | 20,005 | 806.72 | 813.55 | 856.24  | 865.09  |
| 39,990 | 40,000 | 858.97 | 823.44 | 1001.40 | 1004.65 |

Nearly **0.5** seconds to fetch a random first 10 pages and **1** second to fetch a random last 10 pages. My short-attention-span brain can't wait this long. Unacceptable!!!

* Rewrite the SQL to only fetch `page.filename` after getting `doujinishi.id`:
```sql
SELECT
    doujinshi.id,
    doujinshi.full_name,
    doujinshi.path,
    (
        SELECT page.filename
        FROM page
        WHERE page.doujinshi_id = doujinshi.id AND page.order_number = 1
    ) AS filename
FROM doujinshi
ORDER BY doujinshi.id DESC
LIMIT 25
OFFSET :page_number
```

Now I can confidently fetch **500** pages.

| page_start | page_end | avg | p50 | p95 | p99 |
|-----------:|---------:|----:|----:|----:|----:|
| 1      | 501    | 0.54  | 0.52  | 0.64  | 0.91  |
| 19,750 | 20,250 | 10.22 | 10.08 | 11.22 | 11.98 |
| 39,500 | 40,000 | 20.71 | 20.47 | 22.32 | 24.98 |

~**700**x faster when fetching newest pages and **40**x for later pages. Now I'm satisfied. Or am I?

* Fetching the last pages is slow because SQLite has to scan top-down. But why scan top-down when I can scan bottom-up? I can cache `total_page`, and if `page_number > total_page / 2`, I can just reverse the scan order. After pulling my hair finding the correct `LIMIT` and `OFFSET` and wrestling with test cases, here’s the result:

| page_start | page_end | avg | p50 | p95 | p99 |
|-----------:|---------:|----:|----:|----:|----:|
| 1      | 501    | 0.56  | 0.53  | 0.71  | 1.02  |
| 19,750 | 20,250 | 10.35 | 10.04 | 11.87 | 16.61 |
| 39,500 | 40,000 | 0.54  | 0.53  | 0.62  | 0.69  |

Much better (I even had music playing in the background during benchmarking — except for the painfully slow first run).

> **TLDR**: FAST. First pages FAST. Last pages FAST. ALL FAST.

---

## 5. Insert 1 doujinshi
* Result: avg: 21.88ms, p50: 15.04ms, p95: 47.21ms, p99: 69.16ms