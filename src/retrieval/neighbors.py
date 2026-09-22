"""Neighbor-chunk expansion: keep a clause that was split across chunk
boundaries intact in the retrieved context.

Chunking cuts a document into pieces. Sometimes it cuts *through* an answer.
On the NDA corpus, "8. Remedies" is split by fallback paragraph chunking into

    ...::p41  "8. Remedies. a. ... the unauthorized dissemination ... could
               cause irreparable harm ..."
    ...::p42  "b. Therefore, the Parties shall be entitled to injunctive
               relief ..."

p41 ranks well for "what happens if the receiving party discloses confidential
information" — it is *about* unauthorized disclosure. p42 ranks badly for that
same question: on its own it mentions neither disclosure nor the receiving
party, it just says "Therefore, ...". So the harm reaches the context and the
actual remedy does not, and the answer reads as incomplete.

No amount of reranking fixes this, because p42's relevance genuinely is low in
isolation. The signal that p42 belongs in the context is not relevance, it is
*adjacency*: it is the continuation of a chunk that was already selected. This
module therefore pulls neighbors in unscored and unranked, purely positionally.

Adjacency is decided by document order, reconstructed from chunk ids:

    fallback paragraph ids   "<source>::p41"    -> ('p', (41,), '')
    SAC section body ids     "<source>::s4"     -> ('s', (4,),  '')
    SAC clause ids           "<source>::s4:b"   -> ('s', (4,),  'b')

The *ordinal* is only used to sort a document's chunks; adjacency is then a
±window step over that sorted list, not arithmetic on the number. That means
gaps (a deleted chunk, a section with no body chunk) do not silently break
expansion, and ids the parser does not understand simply drop out of the
ordering rather than producing a wrong neighbor. Neighbors are always drawn
from the same source document, so expansion can never cross a document
boundary.
"""

from __future__ import annotations

import re
from collections.abc import Callable

SEPARATOR = "::"

# "p41" / "s4" / "s4:b" / "s12.1:c"
_TAIL = re.compile(r"^(?P<prefix>[a-zA-Z]+)(?P<numbers>\d+(?:\.\d+)*)(?::(?P<clause>.+))?$")

# Key marking a row that was added by expansion rather than selected by ranking.
NEIGHBOR_OF_KEY = "expanded_neighbor"


def split_chunk_id(chunk_id: str) -> tuple[str, str] | None:
    """Split "<source_id>::<tail>" into its two halves, or None if malformed.

    rsplit, not split: a source id is a filename stem and may itself contain
    "::" on some systems; the ordinal is always the last segment.
    """
    if not chunk_id or SEPARATOR not in chunk_id:
        return None
    source_id, _, tail = chunk_id.rpartition(SEPARATOR)
    if not source_id or not tail:
        return None
    return source_id, tail


def source_of(chunk_id: str) -> str | None:
    """The source document id a chunk id belongs to, or None if unparseable."""
    parts = split_chunk_id(chunk_id)
    return parts[0] if parts else None


def chunk_order_key(chunk_id: str) -> tuple[str, tuple[int, ...], str] | None:
    """Sort key placing a chunk in document order within its source document.

    Returns None for any id shape this module does not understand — the caller
    then leaves that chunk alone instead of guessing at a neighbor.
    """
    parts = split_chunk_id(chunk_id)
    if parts is None:
        return None
    match = _TAIL.match(parts[1])
    if match is None:
        return None
    numbers = tuple(int(part) for part in match.group("numbers").split("."))
    return (match.group("prefix"), numbers, match.group("clause") or "")


def document_order(chunk_ids: list[str]) -> list[str]:
    """Order one document's chunk ids by position in the document.

    Ids with no parseable ordinal are dropped: they have no defined position,
    so nothing can be adjacent to them.
    """
    keyed = [(chunk_order_key(cid), cid) for cid in chunk_ids]
    return [cid for key, cid in sorted((k, c) for k, c in keyed if k is not None)]


def neighbor_ids(chunk_id: str, sibling_ids: list[str], window: int) -> list[str]:
    """Ids of `chunk_id`'s neighbors within ±window, in document order.

    `sibling_ids` must all come from the same source document. The anchor
    itself is not included.
    """
    if window < 1:
        return []
    ordered = document_order(sibling_ids)
    if chunk_id not in ordered:
        return []
    index = ordered.index(chunk_id)
    start = max(0, index - window)
    end = min(len(ordered), index + window + 1)
    return [cid for cid in ordered[start:end] if cid != chunk_id]


def expand_with_neighbors(
    rows: list[dict],
    siblings_for: Callable[[str], list[dict]],
    window: int,
) -> list[dict]:
    """Add each selected row's adjacent chunks to the context.

    `siblings_for(source_id)` returns every indexed row of that source document,
    as dicts with at least "chunk_id"; it is called at most once per distinct
    source document per query and its result may be cached by the caller.

    Ordering: the ranked rows keep their relevance order, and each one's
    neighbors are emitted immediately around it in *document* order — so a
    clause split across p41/p42 is contiguous and reads forwards. Rows already
    emitted (as an anchor or as another anchor's neighbor) are not repeated.

    Neighbors extend the context rather than displacing ranked results, and
    carry no score: they are here because they are adjacent, not because they
    are relevant. Each is tagged with NEIGHBOR_OF_KEY = the anchor that pulled
    it in, so downstream layers can tell selected context from expanded context.
    """
    if window < 1:
        return list(rows)

    sibling_cache: dict[str, list[dict]] = {}

    def siblings(source_id: str) -> list[dict]:
        if source_id not in sibling_cache:
            sibling_cache[source_id] = siblings_for(source_id) or []
        return sibling_cache[source_id]

    emitted: set[str] = set()
    out: list[dict] = []

    for row in rows:
        chunk_id = row.get("chunk_id")
        source_id = source_of(chunk_id) if chunk_id else None
        if source_id is None:
            # No parseable position: pass the row through untouched.
            if chunk_id is not None and str(chunk_id) in emitted:
                continue
            if chunk_id is not None:
                emitted.add(str(chunk_id))
            out.append(row)
            continue

        by_id = {str(s["chunk_id"]): s for s in siblings(source_id) if s.get("chunk_id")}
        wanted = neighbor_ids(str(chunk_id), list(by_id), window)

        group: list[dict] = []
        for cid in wanted:
            neighbor = dict(by_id[cid])
            neighbor[NEIGHBOR_OF_KEY] = chunk_id
            group.append(neighbor)
        group.append(row)
        group.sort(key=lambda r: chunk_order_key(str(r["chunk_id"])) or ("", (), ""))

        for item in group:
            cid = str(item["chunk_id"])
            if cid in emitted:
                continue
            emitted.add(cid)
            out.append(item)

    return out
