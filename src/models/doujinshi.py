from __future__ import annotations
from typing import List

from .base import Base
from . import many_to_many_tables
from sqlalchemy import CheckConstraint, Column, ForeignKey
from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class Doujinshi(Base):
	__tablename__ = "doujinshi"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False, nullable=False)
	full_name: Mapped[str] = mapped_column(Text, nullable=False)
	full_name_original: Mapped[str] = mapped_column(Text, nullable=True)
	pretty_name: Mapped[str] = mapped_column(Text, nullable=True)
	pretty_name_original: Mapped[str] = mapped_column(Text, nullable=True)
	path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
	note: Mapped[str] = mapped_column(Text, nullable=True)

	pages: Mapped[list["Page"]] = relationship(
		"Page",
		back_populates="doujinshi",
		foreign_keys="Page.doujinshi_id",
		cascade="all, delete-orphan",
		order_by="Page.order_number"
	)

	parodies: Mapped[list["Parody"]] = relationship(
		"Parody",
		secondary=many_to_many_tables.doujinshi_parody,
		back_populates="doujinshis"
	)
	characters: Mapped[list["Character"]] = relationship(
		"Character",
		secondary=many_to_many_tables.doujinshi_character,
		back_populates="doujinshis"
	)
	tags: Mapped[list["Tag"]] = relationship(
		"Tag",
		secondary=many_to_many_tables.doujinshi_tag,
		back_populates="doujinshis"
	)
	artists: Mapped[list["Artist"]] = relationship(
		"Artist",
		secondary=many_to_many_tables.doujinshi_artist,
		back_populates="doujinshis"
	)
	groups: Mapped[list["Group"]] = relationship(
		"Group",
		secondary=many_to_many_tables.doujinshi_circle,
		back_populates="doujinshis"
	)
	languages: Mapped[list["Language"]] = relationship(
		"Language",
		secondary=many_to_many_tables.doujinshi_language,
		back_populates="doujinshis"
	)

	__table_args__ = (
		CheckConstraint("length(trim(full_name, ' \n\t\r\b\v\t\f')) > 0"),
		CheckConstraint("length(trim(path, ' \n\t\r\b\v\f')) > 0"),

		CheckConstraint("length(trim(full_name_original, ' \n\t\r\b\v\f')) > 0"),
		CheckConstraint("length(trim(pretty_name, ' \n\t\r\b\v\f')) > 0"),
		CheckConstraint("length(trim(pretty_name_original, ' \n\t\r\b\v\f')) > 0"),
		CheckConstraint("length(trim(note, ' \n\t\r\b\v\f')) > 0")
	)