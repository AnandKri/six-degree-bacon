"""Phase-1 ingestion: harvest a curated neighbourhood from Wikidata / Wikipedia.

Everything here is *deterministic given a snapshot*: the network clients fetch raw facts, but the
mapping into the :class:`~sdb.schema.models.Statement` model — including the trust-relevant
rank/reference signals — is a pure function of that fetched data (see :mod:`sdb.harvest.mapping`).
Harvests are pinned to local JSON snapshots so a run is reproducible offline.
"""

from __future__ import annotations
