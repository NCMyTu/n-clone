from __future__ import annotations
from typing import List

from .base import Base
from sqlalchemy import CheckConstraint, Column, ForeignKey, UniqueConstraint
from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


PAGE_SQLITE_WITH_ROWID = False


class Page(Base):
	__tablename__ = "page"

	doujinshi_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("doujinshi.id", ondelete="CASCADE"),
		primary_key=True
	)
	order_number: Mapped[int] = mapped_column(Integer, primary_key=True)
	filename: Mapped[str] = mapped_column(Text, nullable=False)

	doujinshi = relationship(
		"Doujinshi",
		foreign_keys=[doujinshi_id],
		back_populates="pages")

	__table_args__ = (
		CheckConstraint("length(trim(filename, ' \n\t\r\b\v\f')) > 0"),
		CheckConstraint("order_number > 0"),
		UniqueConstraint("doujinshi_id", "filename"),
		{"sqlite_with_rowid": PAGE_SQLITE_WITH_ROWID}
	)