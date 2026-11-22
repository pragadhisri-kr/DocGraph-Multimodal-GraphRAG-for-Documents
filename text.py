"""Pure text helpers: chunking, name normalisation, search-query building."""
import re
import unicodedata
from typing import List

STOP_WORDS = frozenset("""
a an the is are was were be been being do does did can could would should will may might must
what which who whom whose where when why how tell me show give list explain describe about of in on
at to for with by from this that these those it its and or but if then than so as not no
""".split())

_LUCENE_SPECIAL = re.compile(r'([+\-&|!(){}\[\]^"~*?:\\/])')


def normalize_name(name: str) -> str:
    """Canonical form used to merge the same entity mentioned in different chunks."""
    s = unicodedata.normalize("NFKC", name or "").lower().strip()
    s = re.sub(r"[^\w\s&.-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" .-")
    if s.startswith("the ") and len(s) > 4:
        s = s[4:]
    return s


def normalize_rel_type(rel: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", rel or "").strip("_").upper()
    return s or "RELATED_TO"


def _tail(text: str, size: int) -> str:
    if size <= 0:
        return ""
    t = text[-size:]
    i = t.find(" ")
    if 0 <= i < len(t) - 1:
        t = t[i + 1:]
    return t.strip()


def _split_long(paragraph: str, max_chars: int) -> List[str]:
    """Split an oversized paragraph on sentence boundaries, hard-splitting as a last resort."""
    out: List[str] = []
    buf = ""
    for sent in re.split(r"(?<=[.!?])\s+", paragraph):
        while len(sent) > max_chars:
            if buf:
                out.append(buf)
                buf = ""
            out.append(sent[:max_chars])
            sent = sent[max_chars:]
        if buf and len(buf) + 1 + len(sent) > max_chars:
            out.append(buf)
            buf = sent
        else:
            buf = f"{buf} {sent}".strip()
    if buf:
        out.append(buf)
    return out


def chunk_text(text: str, max_chars: int = 1800, overlap: int = 200) -> List[str]:
    """Paragraph-aware chunking with a small character overlap between chunks."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    overlap = max(0, min(overlap, max_chars // 2))
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]

    pieces: List[str] = []
    for p in paragraphs:
        pieces.extend([p] if len(p) <= max_chars else _split_long(p, max_chars))

    chunks: List[str] = []
    buf = ""
    for piece in pieces:
        if buf and len(buf) + 2 + len(piece) > max_chars:
            chunks.append(buf)
            tail = _tail(buf, overlap)
            buf = f"{tail}\n\n{piece}" if tail and len(tail) + 2 + len(piece) <= max_chars else piece
        else:
            buf = f"{buf}\n\n{piece}" if buf else piece
    if buf:
        chunks.append(buf)
    return chunks


def query_tokens(question: str, limit: int = 8) -> List[str]:
    seen, out = set(), []
    for tok in re.findall(r"\w+", (question or "").lower()):
        if len(tok) > 2 and tok not in STOP_WORDS and tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out[:limit]


def lucene_query(tokens: List[str]) -> str:
    """OR-query for Neo4j full-text indexes, with Lucene syntax characters escaped."""
    return " OR ".join(_LUCENE_SPECIAL.sub(r"\\\1", t) for t in tokens if t)
