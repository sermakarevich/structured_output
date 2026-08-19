from so import config
from so.loader import load_pdf


def test_load_pdf():
    text = load_pdf(config.PDF_PATH)
    assert text
    assert "arenas" in text.lower()
    assert len(text) <= config.MAX_DOC_CHARS
