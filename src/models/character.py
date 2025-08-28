from __future__ import annotations
from typing import List

from .base import Base
from .many_to_many_tables import doujinshi_character
from sqlalchemy import CheckConstraint, Column
from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class Character(Base):
	__tablename__ = "character"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

	doujinshis: Mapped[list["Doujinshi"]] = relationship(
		"Doujinshi",
		secondary=doujinshi_character,
		back_populates="characters"
	)

	__table_args__ = (
		CheckConstraint("name <> ''"),
	)