from pathlib import Path
from typing import Any
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions
from docling.datamodel.base_models import InputFormat

class DoclingService:
    """Service to extract structured document blocks using Docling."""
    def __init__(self):
        pipeline_options = PdfPipelineOptions()
        # Limit concurrency to prevent std::bad_alloc on large PDFs
        pipeline_options.accelerator_options = AcceleratorOptions(num_threads=1)
        
        self._converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def convert(self, path: Path) -> Any:
        """Converts a local file path into a structured DoclingDocument."""
        result = self._converter.convert(path)
        return result.document
