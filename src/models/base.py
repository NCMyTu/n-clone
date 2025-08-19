from __future__ import annotations
import re

from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase, validates


class Base(DeclarativeBase):
    @validates("full_name", "name", "path")
    def validate_and_normalize_string(self, key, value):
        """
        Validate and normalize string fields.

        - Reject blank or all-whitespace values.
        - Collapse multiple spaces into one.
        - Strip leading/trailing whitespace.

        Example:
            "   New  \t\n  String   " -> "New String"
        """
        if not value or not value.strip():
            raise ValueError(f"{key} can't be blank or whitespace.")
        if value != value.lower():
            raise ValueError(f"{key} has uppercase letter.")
        normalized = re.sub(r"\s+", " ", value.strip())
        return normalized