from __future__ import annotations

from .base import Base
from sqlalchemy import Column, ForeignKey, Table


doujinshi_parody = Table(
    "doujinshi_parody",
    Base.metadata,
    Column("doujinshi_id", ForeignKey("doujinshi.id", ondelete="CASCADE"), primary_key=True),
    Column("parody_id", ForeignKey("parody.id", ondelete="CASCADE"), primary_key=True),
    sqlite_with_rowid=False,
)

doujinshi_character = Table(
    "doujinshi_character",
    Base.metadata,
    Column("doujinshi_id", ForeignKey("doujinshi.id", ondelete="CASCADE"), primary_key=True),
    Column("character_id", ForeignKey("character.id", ondelete="CASCADE"), primary_key=True),
    sqlite_with_rowid=False,
)

doujinshi_tag = Table(
    "doujinshi_tag",
    Base.metadata,
    Column("doujinshi_id", ForeignKey("doujinshi.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
    sqlite_with_rowid=False,
)

doujinshi_artist = Table(
    "doujinshi_artist",
    Base.metadata,
    Column("doujinshi_id", ForeignKey("doujinshi.id", ondelete="CASCADE"), primary_key=True),
    Column("artist_id", ForeignKey("artist.id", ondelete="CASCADE"), primary_key=True),
    sqlite_with_rowid=False,
)

doujinshi_circle = Table(
    "doujinshi_circle",
    Base.metadata,
    Column("doujinshi_id", ForeignKey("doujinshi.id", ondelete="CASCADE"), primary_key=True),
    Column("circle_id", ForeignKey("circle.id", ondelete="CASCADE"), primary_key=True),
    sqlite_with_rowid=False,
)

doujinshi_language = Table(
    "doujinshi_language",
    Base.metadata,
    Column("doujinshi_id", ForeignKey("doujinshi.id", ondelete="CASCADE"), primary_key=True),
    Column("language_id", ForeignKey("language.id", ondelete="CASCADE"), primary_key=True),
    sqlite_with_rowid=False,
)