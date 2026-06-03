from fastapi import APIRouter, BackgroundTasks

from models.schemas import InternalIngestPayload, ProcessDocumentRequest
from services.backend_callback import BackendCallback
from services.chunker_service import ChunkerService
from services.classifier_service import ClassifierService
from services.extractor_service import ExtractorService
from services.ocr_service import OcrService
from services.retrieval_service import RetrievalService
from services.storage_service import StorageService

router = APIRouter()

storage = StorageService()
ocr = OcrService()
classifier = ClassifierService()
chunker = ChunkerService()
extractor = ExtractorService()
retrieval = RetrievalService()
callback = BackendCallback()


@router.post("/process")
async def process_document(request: ProcessDocumentRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(_process, request)
    return {"status": "accepted", "documentId": request.documentId}


async def _process(request: ProcessDocumentRequest) -> None:
    try:
        local_path = storage.download(request.objectKey, request.fileName)
        pages = ocr.extract_pages(local_path)
        full_text = "\n\n".join(page.get("text", "") for page in pages)
        document_type = classifier.classify(full_text, request.fileName)
        chunks = chunker.chunk(pages)
        if not chunks:
            raise RuntimeError("No readable text was extracted from the document")
        entities = extractor.extract(chunks)
        retrieval.index(request.documentId, request.userId, chunks)
        payload = InternalIngestPayload(
            documentType=document_type,
            status="READY",
            message=f"Processed {len(chunks)} chunks and {len(entities)} entities",
            chunks=chunks,
            entities=entities,
        )
        await callback.ingest(request.documentId, payload)
    except Exception as exc:
        await callback.failed(request.documentId, str(exc))
