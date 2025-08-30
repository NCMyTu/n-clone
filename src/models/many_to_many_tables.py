from __future__ import annotations

from .base import Base
from sqlalchemy import Column, ForeignKey, Table, Index


M2M_SQLITE_WITH_ROWID = False


doujinshi_parody = Table(
	"doujinshi_parody",
	Base.metadata,
	Column("doujinshi_id", ForeignKey("doujinshi.id", ondelete="CASCADE"), primary_key=True),
	Column("parody_id", ForeignKey("parody.id", ondelete="CASCADE"), primary_key=True),
	Index("idx_doujinshi_parody__parody_doujinshi", "parody_id", "doujinshi_id"),
	sqlite_with_rowid=M2M_SQLITE_WITH_ROWID
)

doujinshi_character = Table(
	"doujinshi_character",
	Base.metadata,
	Column("doujinshi_id", ForeignKey("doujinshi.id", ondelete="CASCADE"), primary_key=True),
	Column("character_id", ForeignKey("character.id", ondelete="CASCADE"), primary_key=True),
	Index("idx_doujinshi_character__character_doujinshi", "character_id", "doujinshi_id"),
	sqlite_with_rowid=M2M_SQLITE_WITH_ROWID
)

doujinshi_tag = Table(
	"doujinshi_tag",
	Base.metadata,
	Column("doujinshi_id", ForeignKey("doujinshi.id", ondelete="CASCADE"), primary_key=True),
	Column("tag_id", ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
	Index("idx_doujinshi_tag__tag_doujinshi", "tag_id", "doujinshi_id"),
	sqlite_with_rowid=M2M_SQLITE_WITH_ROWID
)

doujinshi_artist = Table(
	"doujinshi_artist",
	Base.metadata,
	Column("doujinshi_id", ForeignKey("doujinshi.id", ondelete="CASCADE"), primary_key=True),
	Column("artist_id", ForeignKey("artist.id", ondelete="CASCADE"), primary_key=True),
	Index("idx_doujinshi_artist__artist_doujinshi", "artist_id", "doujinshi_id"),
	sqlite_with_rowid=M2M_SQLITE_WITH_ROWID
)

doujinshi_circle = Table(
	"doujinshi_circle",
	Base.metadata,
	Column("doujinshi_id", ForeignKey("doujinshi.id", ondelete="CASCADE"), primary_key=True),
	Column("circle_id", ForeignKey("circle.id", ondelete="CASCADE"), primary_key=True),
	Index("idx_doujinshi_circle__circle_doujinshi", "circle_id", "doujinshi_id"),
	sqlite_with_rowid=M2M_SQLITE_WITH_ROWID
)

doujinshi_language = Table(
	"doujinshi_language",
	Base.metadata,
	Column("doujinshi_id", ForeignKey("doujinshi.id", ondelete="CASCADE"), primary_key=True),
	Column("language_id", ForeignKey("language.id", ondelete="CASCADE"), primary_key=True),
	Index("idx_doujinshi_language__language_doujinshi", "language_id", "doujinshi_id"),
	sqlite_with_rowid=M2M_SQLITE_WITH_ROWID
)