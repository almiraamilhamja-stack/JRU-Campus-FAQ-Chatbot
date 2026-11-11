"""PDF loading and chunking (the professor's template approach: PyPDFLoader + RecursiveCharacterTextSplitter).

Every chunk keeps its source file name, PDF page, the handbook it belongs to, and the page number inside that
handbook, so answers can show where the information came from."""
import hashlib
from datetime import datetime
from pathlib import Path

from config import (DATA_DIR, STUDENT_LAST_PDF_PAGE, STUDENT_HANDBOOK, FACULTY_HANDBOOK, COMBINED_PDF_NAME,
                    DOCUMENT_DESCRIPTIONS, MAX_UPLOAD_MB)


def handbook_for_page(source_name: str, pdf_page: int):
    """Return (handbook title, page number inside that handbook) for a 1-based PDF page."""
    if source_name == COMBINED_PDF_NAME:
        if pdf_page <= STUDENT_LAST_PDF_PAGE:
            return STUDENT_HANDBOOK, pdf_page
        return FACULTY_HANDBOOK, pdf_page - STUDENT_LAST_PDF_PAGE
    return Path(source_name).stem.replace("_", " "), pdf_page


def list_pdf_files(data_dir=DATA_DIR):
    return sorted(p for p in Path(data_dir).glob("*.pdf") if p.is_file())


def fingerprint_files(files):
    """SHA-256 over the names and contents of the PDFs, used to detect that the index is out of date."""
    h = hashlib.sha256()
    for p in files:
        h.update(p.name.encode("utf-8"))
        with open(p, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(block)
    return h.hexdigest()


def load_documents(data_dir=DATA_DIR):
    """Load all PDFs. Raises FileNotFoundError when there is nothing to index."""
    from langchain_community.document_loaders import PyPDFLoader
    files = list_pdf_files(data_dir)
    if not files:
        raise FileNotFoundError(f"No PDF reference documents were found in {data_dir}. Add a PDF and rebuild the index.")
    documents, problems = [], []
    for path in files:
        try:
            pages = PyPDFLoader(str(path)).load()
        except Exception as exc:                       # unreadable or corrupt PDF
            problems.append(f"{path.name}: {exc}")
            continue
        for doc in pages:
            pdf_page = int(doc.metadata.get("page", 0)) + 1
            handbook, handbook_page = handbook_for_page(path.name, pdf_page)
            doc.metadata.update({"source": path.name, "pdf_page": pdf_page,
                                 "handbook": handbook, "handbook_page": handbook_page})
        documents.extend(d for d in pages if d.page_content.strip())   # skip blank pages (e.g. covers)
    if not documents:
        raise ValueError("The PDF files contained no extractable text. " + "; ".join(problems))
    return documents, problems


def split_documents(documents, chunk_size, chunk_overlap):
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap,
                                              add_start_index=True)
    return splitter.split_documents(documents)


def describe_documents(data_dir=DATA_DIR):
    """Rows for the Reference Documents page."""
    rows = []
    for p in list_pdf_files(data_dir):
        n_pages = None
        try:
            from pypdf import PdfReader
            n_pages = len(PdfReader(str(p)).pages)
        except Exception:
            pass
        rows.append({
            "title": p.stem.replace("_", " "),
            "file": p.name,
            "type": "PDF",
            "description": DOCUMENT_DESCRIPTIONS.get(p.name, "Uploaded reference document."),
            "pages": n_pages,
            "size_mb": round(p.stat().st_size / 1e6, 2),
            "modified": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return rows


def validate_upload(filename: str, data: bytes):
    """Validate an uploaded file. Returns (ok, message, safe_filename)."""
    name = Path(filename or "").name
    if not name.lower().endswith(".pdf"):
        return False, "Only PDF files are accepted.", None
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        return False, f"The file is larger than {MAX_UPLOAD_MB} MB.", None
    if not data.startswith(b"%PDF"):
        return False, "The file is not a valid PDF (missing PDF header).", None
    safe = "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in name)[:120]
    try:
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            return False, "Encrypted PDFs are not supported.", None
        text = "".join((pg.extract_text() or "") for pg in reader.pages[:5])
        if not text.strip():
            return False, "No text could be extracted from the first pages. Scanned PDFs need OCR first.", None
    except Exception as exc:
        return False, f"The PDF could not be read: {exc}", None
    return True, "OK", safe
