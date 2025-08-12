# TODO:  
- [x] Add `Database.update_note_of_doujinshi`
- [x] Add `Database.add_pages_to_doujinshi` (delete old entries from page table and add new ones)
- [x] Add `Database.remove_all_pages_from_doujinshi`
- [x] Implement `Database.get_doujinshi`
- [x] Implement `Database.get_doujinshi_in_batch`
- [x] Implement `update_{column_name_in_doujinshi_table}_of_doujinshi`
- [x] Implement `get_count_of_{parodies/characters/tags/artists/groups/languages}`
- [ ] ~~Update `Database.add_{item}_to_doujinshi` to accept a list of items instead of a single item~~  
    **Not needed** - items are either fully provided at initialization or only slightly modified during review, so bulk insertion is rarely necessary.
- [ ] ~~Update `Database.insert_{item}` to accept a list of items instead of a single item~~  
    **Not needed** - same as above
- [ ] ~~Update `Database.remove_{item}_from_doujinshi` to accept a list of items instead of a single item~~  
    **Not needed** - same as above
- [ ] Add a search function in Database
- [ ] Add `Database.check_health`: check if there are any stray doujinshi in joint tables
- [ ] Add page confirmation in `Doujinshi.strict_mode`
- [ ] Add a final confirmation to `Doujinshi.strict_mode`
- [ ] Use `logging` instead of printing
- [ ] Db design
- [ ] Docs
- [ ] Example
- [ ] Tests