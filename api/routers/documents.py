import os
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.database import get_db
from api import models, schemas
from api.rag.processor import process_pdf
from api.rag.retriever import query_document

UPLOADS_PATH = "./uploads"
Path(UPLOADS_PATH).mkdir(exist_ok=True)

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("", response_model=schemas.DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=422,
            detail={
                "type": "https://api.financeassistant.dev/errors/invalid-file",
                "title": "Invalid file type",
                "status": 422,
                "detail": "Only PDF files are accepted",
            },
        )

    # 1. Guardar el documento en la base de datos con status processing
    document = models.Document(
        filename=file.filename,
        status=models.DocumentStatus.processing,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    # 2. Guardar el archivo en disco
    file_path = f"{UPLOADS_PATH}/{document.id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 3. Procesar el PDF y guardar embeddings en ChromaDB
    try:
        await process_pdf(file_path, document.id)
        document.status = models.DocumentStatus.ready
    except Exception as e:
        document.status = models.DocumentStatus.error

    await db.commit()
    await db.refresh(document)
    return document

@router.post("/{id}/query", response_model=schemas.DocumentQueryOut)
async def query_document_endpoint(
    id: int,
    body: schemas.DocumentQuery,
    db: AsyncSession = Depends(get_db),
):
    # 1. Verificar que el documento existe y está listo
    result = await db.execute(
        select(models.Document).where(models.Document.id == id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://api.financeassistant.dev/errors/not-found",
                "title": "Resource not found",
                "status": 404,
                "detail": f"Document with id {id} does not exist",
            },
        )
    if document.status != models.DocumentStatus.ready:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "https://api.financeassistant.dev/errors/not-ready",
                "title": "Document not ready",
                "status": 422,
                "detail": f"Document with id {id} has status '{document.status.value}'",
            },
        )

    # 2. Consultar el documento
    answer = await query_document(id, body.question)
    return schemas.DocumentQueryOut(question=body.question, answer=answer)