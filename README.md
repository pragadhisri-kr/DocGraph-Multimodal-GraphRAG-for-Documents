# Multimodal-GraphRAG for Documents

Document version of the video Multimodal-GraphRAG: PDFs are turned into a Neo4j
knowledge graph plus a Qdrant vector index, and queried with a hybrid
graph-first / vector-fallback / graph-backfill strategy.

## Pipeline

1. **Parse** (`preprocessor/pdf_parser.py`, PyMuPDF)
   - page text
   - tables -> markdown (`[TABLE]`)
   - embedded figures -> saved PNG + VLM caption (`[FIGURE]`)
   - scanned pages (no text layer) -> VLM transcription
2. **Chunk** pages (text + tables + captions) into ~1500-char chunks with doc/page metadata.
3. **Index**: chunks -> Qdrant (fastembed); chunks -> `LLMGraphTransformer` -> Neo4j.
   Every entity is linked `(Document {doc, page})-[:MENTIONS]->(entity)` for citations.
4. **Query** (`graph/KnowledgeGraph.py`)
   1. `GraphCypherQAChain` on Neo4j
   2. if empty/insufficient -> Qdrant top-k + LLM answer with `[doc, p.N]` citations
   3. if that answers -> re-extract the retrieved chunks with a question-aware prompt and
      write the new entities back to Neo4j (graph learning)

## Setup

```bash
uv sync
cp .env.example .env        # add API keys + Neo4j password
docker-compose up -d        # Neo4j (7474/7687) + Qdrant (6333)
```

## Run

```bash
python index_data.py --path ./data/documents          # a folder or a single PDF
python query_graph.py "Which methods were compared in the results table?"
python query_graph.py "What does Figure 2 show?" --naive
```

## Notes

- Figure captions and table markdown become text inside chunks, so graph and vector
  search both cover non-text content.
- Parsed output is cached in `data/parsed/<doc>/` (delete to re-parse).
- To constrain the schema, pass `allowed_nodes=[...]` / `allowed_relationships=[...]`
  to `LLMGraphTransformer` in `KnowledgeGraph.__init__`.
- The Cypher chain runs LLM-generated queries; use a read-only Neo4j user in production.
