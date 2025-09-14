from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase, validates
from pathlib import Path


class Base(DeclarativeBase):
	@validates(
		"full_name", "full_name_original",
		"pretty_name", "pretty_name_original",
		"path", "note",
		"name"
	)
	def validate_and_normalize_string(self, key, value):
		"""Validate and normalize string fields.

		Reject blank or all-whitespace values.
		Normalize:
			Strip leading/trailing whitespace,
			Collapse multiple spaces into one,
			For 'name', to lowercase,
			For 'path', enforce POSIX-style separators (no '\\').

		Example:
			"   New  \t\n  String   " -> "new string"
		"""
		if not isinstance(value, str):
			raise ValueError(f"{key} must be a non-empty string. Got {type(value)} instead.")
		if not value or not value.strip():
			raise ValueError(f"{key} must be a non-empty string. Got {type(value)} instead.")

		normalized = " ".join(value.strip().split())

		if key == "name":
			normalized = normalized.lower()

		if key == "path":
			normalized = Path(normalized).as_posix()

		return normalized