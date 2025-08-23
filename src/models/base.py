from __future__ import annotations
import re

from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase, validates
from pathlib import Path


class Base(DeclarativeBase):
	@validates("full_name", "name", "path")
	def validate_and_normalize_string(self, key, value):
		"""
		Validate and normalize string fields.

		- Reject blank or all-whitespace values.
		- Normalize:
			Strip leading/trailing whitespace,
			Collapse multiple spaces into one,
			For 'name', to lowercase,
			For 'path', enforce POSIX-style separators (no '\\').

		Example:
			"   New  \t\n  String   " -> "new string"
		"""
		if not value or not value.strip():
			raise ValueError(f"{key} can't be blank or whitespace.")

		normalized = re.sub(r"\s+", " ", value.strip())

		if key == "name":
			normalized = normalized.lower()

		if key == "path":
			normalized = Path(normalized).as_posix()

		return normalized