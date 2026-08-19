import base64
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


def render_pdf(path: str) -> list[str]:
    doc = pymupdf.open(path)
    images = [
        base64.b64encode(page.get_pixmap(dpi=config.RENDER_DPI).tobytes("png")).decode()
        for page in doc
    ]
    total_mb = sum(len(base64.b64decode(img)) for img in images) / 1e6
    logger.info("rendered %d pages, dpi=%d, %.1f MB", len(images), config.RENDER_DPI, total_mb)
    return images
