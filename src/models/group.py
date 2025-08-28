from __future__ import annotations
from typing import List

from .base import Base
from .many_to_many_tables import doujinshi_circle
from sqlalchemy import CheckConstraint, Column
from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class Group(Base):
	__tablename__ = "circle"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
	count: Mapped[int] = mapped_column(Integer, default=0)

	doujinshis: Mapped[list["Doujinshi"]] = relationship(
		"Doujinshi",
		secondary=doujinshi_circle,
		back_populates="groups"
	)

	__table_args__ = (
		CheckConstraint("name <> ''"),
	)