from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EbirdTaxon(Base):
    """A cached row from eBird's full species taxonomy, for name search.

    eBird's taxonomy endpoint has no free-text search - it's a bulk reference list (~16k
    species) meant to be fetched once and searched locally. This lets the targeting picker
    find a species by name even when it has no current nearby sightings (unlike
    `WildlifeSighting`, which only has species someone has actually reported).
    """

    __tablename__ = "ebird_taxa"

    species_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    common_name: Mapped[str] = mapped_column(String(200), index=True)
    scientific_name: Mapped[str] = mapped_column(String(200))
