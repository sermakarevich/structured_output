import base64

import pymupdf

from so import config
from so.loader import load_pdf, render_pdf


def test_load_pdf():
    text = load_pdf(config.PDF_PATH)
    assert text
    assert "arenas" in text.lower()
    assert len(text) <= config.MAX_DOC_CHARS


def test_render_pdf_page_count():
    images = render_pdf(config.PDF_PATH)
    assert len(images) == len(pymupdf.open(config.PDF_PATH))


def test_render_pdf_png_bytes():
    images = render_pdf(config.PDF_PATH)
    for img in images:
        assert base64.b64decode(img).startswith(b"\x89PNG")
