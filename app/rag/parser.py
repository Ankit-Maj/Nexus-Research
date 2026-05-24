"""
Document parser with extraction method tracking (DIRECT vs OCR).
Returns (text, extraction_method) tuples.
"""

import os
import docx
from pathlib import Path
from typing import Tuple
from pypdf import PdfReader
from app.utils.config import logger, OCR_TESSERACT_CMD, OCR_POPPLER_PATH

if OCR_TESSERACT_CMD:
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = OCR_TESSERACT_CMD
        logger.info(f"Tesseract OCR path set: {OCR_TESSERACT_CMD}")
    except Exception as e:
        logger.warning(f"Failed to configure pytesseract: {e}")


def parse_txt_md(file_path: Path) -> Tuple[str, str]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(), "DIRECT"
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return "", "DIRECT"


def parse_docx(file_path: Path) -> Tuple[str, str]:
    try:
        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs), "DIRECT"
    except Exception as e:
        logger.error(f"Error reading DOCX {file_path}: {e}")
        return "", "DIRECT"


def parse_pdf(file_path: Path) -> Tuple[str, str]:
    text_content = ""
    try:
        reader = PdfReader(file_path)
        pages_text = [p.extract_text() for p in reader.pages if p.extract_text()]
        text_content = "\n".join(pages_text)
    except Exception as e:
        logger.error(f"PdfReader error on {file_path}: {e}")

    if len(text_content.strip()) >= 50:
        return text_content, "DIRECT"

    # OCR fallback
    logger.info(f"PDF '{file_path.name}' has little text — attempting OCR fallback.")
    try:
        from pdf2image import convert_from_path
        import pytesseract

        poppler = OCR_POPPLER_PATH if OCR_POPPLER_PATH else None
        images = convert_from_path(str(file_path), poppler_path=poppler)
        ocr_pages = []
        for i, img in enumerate(images):
            logger.info(f"OCR page {i + 1}/{len(images)} of '{file_path.name}'")
            ocr_pages.append(pytesseract.image_to_string(img))

        ocr_text = "\n".join(ocr_pages)
        if len(ocr_text.strip()) > 50:
            logger.info(f"OCR extracted {len(ocr_text)} chars from '{file_path.name}'.")
            return ocr_text, "OCR"
        logger.warning("OCR returned minimal text.")
    except ImportError:
        logger.warning("OCR skipped: pdf2image/pytesseract not installed.")
    except Exception as e:
        logger.error(f"OCR failed for '{file_path.name}': {e}")

    return text_content, "DIRECT"


def parse_document(file_path: Path) -> Tuple[str, str]:
    """
    Parse a document and return (text, extraction_method).
    extraction_method is 'DIRECT' or 'OCR'.
    """
    suffix = file_path.suffix.lower()
    if suffix in [".txt", ".md"]:
        return parse_txt_md(file_path)
    elif suffix == ".docx":
        return parse_docx(file_path)
    elif suffix == ".pdf":
        return parse_pdf(file_path)
    else:
        logger.warning(f"Unsupported format: {suffix}")
        return "", "DIRECT"
