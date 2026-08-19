import base64
import logging

import pymupdf

from so import config

logger = logging.getLogger(__name__)


def render_pdf(path: str) -> list[str]:
    doc = pymupdf.open(path)
    images = [
        base64.b64encode(page.get_pixmap(dpi=config.RENDER_DPI).tobytes("png")).decode()
        for page in doc
    ]
    payload_mb = sum(len(img) for img in images) / 1e6
    logger.info(
        "rendered %d pages, dpi=%d, %.1f MB base64", len(images), config.RENDER_DPI, payload_mb
    )
    return images
