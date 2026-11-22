import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, Request, UploadFile

from ..config import get_settings
from ..schemas import ChatRequest
from ..services.ingest import ingest_document
from ..services.jobs import jobs
from ..services.llm import LLMConfigError, get_llm
from ..services.rag import answer_question

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def _llm():
    try:
        return get_llm()
    except LLMConfigError as exc:
        raise HTTPException(503, str(exc))


@router.get("/health")
def health(request: Request):
    s = get_settings()
    return {"neo4j": request.app.state.store.healthy(), "llm_provider": s.llm_provider,
            "llm_configured": s.llm_configured}


@router.post("/documents", status_code=202)
async def upload_document(request: Request, background: BackgroundTasks, file: UploadFile = File(...)):
    s = get_settings()
    name = os.path.basename(file.filename or "")
    if not name.lower().endswith(".pdf"):
        raise HTTPException(400, "Only .pdf files are supported.")
    llm = _llm()

    os.makedirs(s.upload_dir, exist_ok=True)
    doc_id = uuid.uuid4().hex[:12]
    path = os.path.join(s.upload_dir, f"{doc_id}.pdf")
    limit, size = s.max_upload_mb * 1024 * 1024, 0
    try:
        with open(path, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                if size == 0 and not chunk.startswith(b"%PDF"):
                    raise HTTPException(400, "File is not a valid PDF.")
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, f"File exceeds {s.max_upload_mb} MB.")
                out.write(chunk)
        if size == 0:
            raise HTTPException(400, "File is empty.")
    except HTTPException:
        if os.path.exists(path):
            os.remove(path)
        raise

    job = jobs.create(doc_id)
    background.add_task(ingest_document, job.id, doc_id, path, os.path.splitext(name)[0],
                        s, request.app.state.store, llm)
    return {"doc_id": doc_id, "job_id": job.id}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    return job


@router.get("/documents")
def list_documents(request: Request):
    return {"documents": request.app.state.store.list_documents()}


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str, request: Request):
    request.app.state.store.delete_document(doc_id)
    return {"status": "deleted"}


@router.get("/graph")
def graph(request: Request, doc_id: Optional[str] = None, limit: int = Query(150, ge=1, le=1000)):
    return request.app.state.store.get_graph(doc_id, limit)


@router.post("/chat")
def chat(req: ChatRequest, request: Request):
    llm = _llm()
    try:
        return answer_question(request.app.state.store, llm, req.question, req.doc_id)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        log.exception("Chat failed")
        raise HTTPException(502, f"Could not answer: {exc}")
