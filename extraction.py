"""LLM extraction: prompt, tolerant JSON parsing, and cross-chunk entity merging.

The model refers to entities by *name* (not ids), so relations can never dangle and
the same entity found in many chunks merges into one node.
"""
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .text import normalize_name, normalize_rel_type

MAX_TEXT_CHARS = 6000
MAX_DESC = 300

PROMPT = """You are a knowledge-graph extraction engine.
Read the text and extract the important entities and the relationships between them.

Return ONLY a JSON object of this exact shape:
{{
  "entities": [{{"name": "...", "type": "...", "description": "..."}}],
  "relations": [{{"source": "...", "target": "...", "type": "...", "description": "..."}}]
}}

Rules:
- "type" for entities is a short category such as Person, Organization, Policy, Coverage, Benefit,
  Amount, Date, Location, Condition, Term, Document.
- "type" for relations is a short verb phrase in UPPER_SNAKE_CASE, e.g. COVERS, EXCLUDES, PAYS, REQUIRES.
- Use the same exact name for an entity everywhere it appears. Keep descriptions under 200 characters.
- "source" and "target" must be names of entities you list. Do not invent facts that are not in the text.
- If nothing is worth extracting, return {{"entities": [], "relations": []}}.

TEXT:
{text}
"""


def build_prompt(text: str) -> str:
    return PROMPT.format(text=text[:MAX_TEXT_CHARS])


@dataclass
class Entity:
    name: str
    type: str = "Concept"
    description: str = ""


@dataclass
class Relation:
    source: str
    target: str
    type: str = "RELATED_TO"
    description: str = ""


@dataclass
class Extraction:
    entities: List[Entity] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)


def _clean(v, limit: int = MAX_DESC) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:limit]


def parse_extraction(raw: str) -> Extraction:
    """Parse model output into an Extraction. Never raises; bad output yields an empty result."""
    if not raw:
        return Extraction()
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.I)
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end <= start:
        return Extraction()
    try:
        data = json.loads(s[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        return Extraction()
    if not isinstance(data, dict):
        return Extraction()

    def as_list(v):
        return v if isinstance(v, list) else []

    entities: Dict[str, Entity] = {}
    for item in as_list(data.get("entities")):
        if not isinstance(item, dict):
            continue
        name = _clean(item.get("name"), 120)
        key = normalize_name(name)
        if not key:
            continue
        entities.setdefault(key, Entity(name, _clean(item.get("type"), 40) or "Concept", _clean(item.get("description"))))

    relations: List[Relation] = []
    for item in as_list(data.get("relations")):
        if not isinstance(item, dict):
            continue
        src, tgt = _clean(item.get("source"), 120), _clean(item.get("target"), 120)
        sk, tk = normalize_name(src), normalize_name(tgt)
        if not sk or not tk or sk == tk:
            continue
        for key, name in ((sk, src), (tk, tgt)):   # keep referential integrity
            entities.setdefault(key, Entity(name))
        relations.append(Relation(src, tgt, normalize_rel_type(_clean(item.get("type"), 60)), _clean(item.get("description"))))

    return Extraction(list(entities.values()), relations)


class GraphAccumulator:
    """Merges per-chunk extractions into one deduplicated graph for a document."""

    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        self._entities: Dict[str, dict] = {}
        self._relations: Dict[Tuple[str, str, str], dict] = {}

    def key(self, name: str) -> str:
        return f"{self.doc_id}::{normalize_name(name)}"

    def add(self, chunk_id: str, ex: Extraction) -> None:
        for e in ex.entities:
            k = self.key(e.name)
            cur = self._entities.setdefault(k, {"key": k, "name": e.name, "type": e.type, "description": "", "chunks": set()})
            if cur["type"] == "Concept" and e.type != "Concept":
                cur["type"] = e.type
            if len(e.description) > len(cur["description"]):
                cur["description"] = e.description
            cur["chunks"].add(chunk_id)
        for r in ex.relations:
            rk = (self.key(r.source), r.type, self.key(r.target))
            cur = self._relations.setdefault(rk, {"source": rk[0], "type": r.type, "target": rk[2], "description": ""})
            if len(r.description) > len(cur["description"]):
                cur["description"] = r.description

    def entity_rows(self) -> List[dict]:
        return [{k: v for k, v in e.items() if k != "chunks"} for e in self._entities.values()]

    def mention_rows(self) -> List[dict]:
        return [{"chunk_id": c, "key": e["key"]} for e in self._entities.values() for c in sorted(e["chunks"])]

    def relation_rows(self) -> List[dict]:
        return [r for r in self._relations.values() if r["source"] in self._entities and r["target"] in self._entities]
