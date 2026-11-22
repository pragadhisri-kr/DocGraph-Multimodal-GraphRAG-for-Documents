# DocGraph-Multimodal-GraphRAG-for-Documents
A knowledge-graph based Retrieval-Augmented Generation (RAG) system that turns PDF documents into a Neo4j knowledge graph and answers questions with page-cited, chunk-grounded answers.
Standard RAG ranks isolated text chunks by vector similarity, so it struggles with questions that need facts spread across several passages or relationships between entities. DocGraph represents a document as a graph of entities and relationships, so retrieval can follow links between facts instead of relying on similarity alone.
# Features
1.PDF ingestion – page-by-page text extraction with PyMuPDF
2.Provenance-aware chunking – sliding window (1,500 chars, 250 overlap); every chunk keeps document, page and character span
3.LLM entity & relation extraction – Google Gemini returns typed entities (Technology, Person, Organization, Concept, Metric) and relationships as schema-constrained JSON, processed in parallel (4 workers)
4.Entity deduplication – a GraphAccumulator merges entities by canonical key (idempotent Cypher MERGE upserts)
5.Graph retrieval – seed entities → 1–2 hop Cypher traversal → keyword fallback over chunk nodes
6.Grounded answers – the model answers only from retrieved chunks and cites the exact page
7.Dashboard – interactive graph view with entity-type filter, chunk browser, GraphRAG Q&A panel, and a FastAPI & Cypher tab
# Architecture
Browser (DocGraph dashboard: Graph & Q&A | Chunks | FastAPI & Cypher)
        │  REST
        ▼
Back end: PDF parser + chunker → Gemini extractor → GraphAccumulator → Retrieval engine
        │                                   │
        ▼                                   ▼
Neo4j (Document, Chunk, Entity)       Google Gemini API

# Indexing: PDF → page text → overlapping chunks → entities & relations (Gemini) → deduplicate → store in Neo4j

# Query: question → seed entities → 1–2 hop Cypher traversal → linked chunks → grounded answer with page citations

# Graph schema
Node	                          Content
Document	                    file name, page count
Chunk                 	chunk_id, text, page, character span
Entity                 	name, type, aliases, doc_ids, pages, canonical_key
Edge	                                  Meaning
MENTIONED_IN	                    entity appears in a chunk (provenance for citations)
Entity–entity relations          	typed relationships extracted by the LLM
Document–Chunk	                  chunk belongs to a document
# Tech stack
Layer                                    	Technology
Language	                          Python, JavaScript/TypeScript
PDF parsing                       	PyMuPDF
LLM                               	Google Gemini (structured JSON output)
Graph database                     	Neo4j (Bolt) + Cypher
Back end                          	FastAPI, Express REST routes
Config	                            pydantic-settings (.env)
# REST API
Method & route                            	Purpose
GET /api/health                           	service status, storage mode, whether the Gemini key is                                             configured
GET /api/documents                        	list indexed documents
GET /api/documents/:docId/chunks           	list chunks of one document (or all)
DELETE /api/documents/:docId	              delete a document and its chunks
# Getting started
1.Install and start Neo4j (default Bolt URI bolt://localhost:7687).
2.Create a .env file:
env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=your_gemini_model
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
DEFAULT_CHUNK_CHARS=1500
DEFAULT_CHUNK_OVERLAP=250
EXTRACTION_MAX_WORKERS=4
Install dependencies and start the back end and the dashboard:
bash
# TODO: replace with your actual commands
pip install -r requirements.txt
# start the back end
# start the dashboard
Open the dashboard, drop a PDF (or click Load Sample Technical PDF), check the Chunks tab, then ask questions in the GraphRAG Q&A panel.

Never commit your .env file or API keys.

# Results

Evaluated by inspecting the indexed output (no accuracy benchmark against a baseline has been run yet):

Measure	Value
Pages → chunks (test PDF)	17 → 17
Entities in knowledge graph	34
Relationships	25
Technology / Concept / Metric / Person / Organization	15 / 13 / 3 / 2 / 1
# Limitations
Charts, figures and image-only slides are not read yet; only extractable text is indexed (slides with only charts produced almost no text).
No benchmark of answer accuracy or latency against plain RAG yet.
Relations are extracted per chunk, so the graph has several small disconnected clusters.
Extraction depends on the LLM and an API key.

# Roadmap
[1] Multimodal extraction – vision-language model / OCR for charts, tables and images, stored as graph nodes
[2] Cross-page entity linking – merge similar entities and extract relations over neighbouring chunks
[3] Evaluation – question set comparing accuracy, faithfulness and latency vs. plain text RAG
[4] Hybrid retrieval – vector embeddings alongside graph traversal and community summaries
[5] Platform features – multi-user support, authentication, Word/PowerPoint input
[6] Docker setup for one-command deployment
References

Lewis et al., Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (2020) · Edge et al., From Local to Global: A Graph RAG Approach to Query-Focused Summarization (2024) · Neo4j / Cypher documentation.
