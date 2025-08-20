from __future__ import annotations
from typing import List

from .base import Base
from sqlalchemy import CheckConstraint, Column, ForeignKey, UniqueConstraint
from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class Page(Base):
	__tablename__ = "page"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	filename: Mapped[str] = mapped_column(Text, nullable=False)
	order_number: Mapped[int] = mapped_column(Integer, nullable=False)
	
	doujinshi_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("doujinshi.id", ondelete="CASCADE"),
		nullable=False
	)
	doujinshi = relationship(
		"Doujinshi",
		foreign_keys=[doujinshi_id],
		back_populates="pages")

	__table_args__ = (
		CheckConstraint("filename <> ''"),
		CheckConstraint("order_number > 0"),
		UniqueConstraint("doujinshi_id", "filename"),
		UniqueConstraint("doujinshi_id", "order_number")
	)