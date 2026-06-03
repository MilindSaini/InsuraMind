import tempfile
from pathlib import Path
from typing import Any

from utils.text_utils import clean_text


class OcrService:
    def __init__(self):
        self._ocr = None

    def extract_pages(self, path: Path) -> list[dict[str, Any]]:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf(path)
        if suffix in {".png", ".jpg", ".jpeg"}:
            return self._extract_image(path)
        return [{"page": 1, "text": path.read_text(errors="ignore"), "blocks": []}]

    def _extract_pdf(self, path: Path) -> list[dict[str, Any]]:
        try:
            import fitz

            pages: list[dict[str, Any]] = []
            with fitz.open(path) as doc:
                for index, page in enumerate(doc, start=1):
                    text = clean_text(page.get_text("text"))
                    blocks = []
                    for block in page.get_text("blocks"):
                        if len(block) >= 5 and str(block[4]).strip():
                            blocks.append({
                                "x0": block[0],
                                "y0": block[1],
                                "x1": block[2],
                                "y1": block[3],
                                "text": clean_text(str(block[4])),
                            })
                    if text:
                        pages.append({"page": index, "text": text, "blocks": blocks})
                        continue

                    ocr_page = self._ocr_pdf_page(page, index)
                    if ocr_page["text"]:
                        pages.append(ocr_page)
                        continue

                    pages.append({"page": index, "text": text, "blocks": blocks})
            if pages:
                return pages
        except Exception:
            pass

        pages = self._pdfplumber(path)
        if pages:
            return pages
        return [{"page": 1, "text": self._naive_pdf_text(path), "blocks": []}]

    def _pdfplumber(self, path: Path) -> list[dict[str, Any]]:
        try:
            import pdfplumber

            pages = []
            with pdfplumber.open(path) as pdf:
                for index, page in enumerate(pdf.pages, start=1):
                    text = clean_text(page.extract_text() or "")
                    pages.append({"page": index, "text": text, "blocks": []})
            return pages
        except Exception:
            return []

    def _extract_image(self, path: Path) -> list[dict[str, Any]]:
        try:
            from paddleocr import PaddleOCR

            ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
            result = ocr.ocr(str(path), cls=True)
            lines = []
            for page in result or []:
                for line in page or []:
                    if len(line) > 1 and line[1]:
                        lines.append(line[1][0])
            return [{"page": 1, "text": clean_text("\n".join(lines)), "blocks": []}]
        except Exception:
            return [{"page": 1, "text": "", "blocks": []}]

    def _ocr_pdf_page(self, page: Any, page_number: int) -> dict[str, Any]:
        try:
            import fitz

            ocr = self._ocr_engine()
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                temp_path = Path(tmp.name)
            try:
                pixmap.save(str(temp_path))
                result = ocr.ocr(str(temp_path), cls=True)
            finally:
                temp_path.unlink(missing_ok=True)

            lines = []
            blocks = []
            for page_result in result or []:
                for line in page_result or []:
                    if len(line) < 2 or not line[1]:
                        continue
                    text = clean_text(str(line[1][0]))
                    if not text:
                        continue
                    lines.append(text)
                    box = line[0] or []
                    if len(box) >= 4:
                        xs = [point[0] for point in box]
                        ys = [point[1] for point in box]
                        blocks.append({
                            "x0": min(xs),
                            "y0": min(ys),
                            "x1": max(xs),
                            "y1": max(ys),
                            "text": text,
                        })
            return {"page": page_number, "text": clean_text("\n".join(lines)), "blocks": blocks}
        except Exception:
            return {"page": page_number, "text": "", "blocks": []}

    def _ocr_engine(self):
        if self._ocr is not None:
            return self._ocr
        from paddleocr import PaddleOCR

        self._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        return self._ocr

    def _naive_pdf_text(self, path: Path) -> str:
        data = path.read_bytes()
        text = data.decode("latin1", errors="ignore")
        return clean_text(text)
