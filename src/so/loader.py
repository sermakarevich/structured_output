import logging

import pymupdf

from so import config

logger = logging.getLogger(__name__)


def load_pdf(path: str) -> str:
    doc = pymupdf.open(path)
    text = "\n".join(page.get_text() for page in doc)
    text = text[: config.MAX_DOC_CHARS]
    logger.info("loaded %d pages, %d characters", doc.page_count, len(text))
    return text
