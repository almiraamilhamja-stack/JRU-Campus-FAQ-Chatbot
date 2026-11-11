"""Check every FAQ evidence sentence against the PDF text (run: python verify_faq.py)."""
import re
import sys
import unicodedata

from pypdf import PdfReader

from config import DATA_DIR, COMBINED_PDF_NAME
from faq_data import get_faqs


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s)).casefold()


def main():
    pdf = DATA_DIR / COMBINED_PDF_NAME
    pages = [norm(p.extract_text() or "") for p in PdfReader(str(pdf)).pages]
    bad = 0
    for f in get_faqs():
        ok = norm(f["evidence"]) in pages[f["pdf_page"] - 1]
        bad += (not ok)
        print(("OK  " if ok else "FAIL"), f"pdf p.{f['pdf_page']:>2}", f["question"])
    print(f"\n{len(get_faqs()) - bad}/{len(get_faqs())} FAQ evidence sentences verified")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
