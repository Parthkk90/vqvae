from __future__ import annotations
import mimetypes
import logging

# It's good practice to get a logger for the current module.
logger = logging.getLogger(__name__)

try:
    import magic  # from python-magic or python-magic-bin (Windows)
    _HAVE_MAGIC = True
except (ImportError, ModuleNotFoundError):
    _HAVE_MAGIC = False


def detect_mime(path: str) -> tuple[str, str]:
    """Returns (mime_type, source_library_name)."""
    if _HAVE_MAGIC:
        try:
            # Use the functional interface for simplicity.
            return magic.from_file(path, mime=True), "python-magic"
        except Exception as e:  # Broad exception to be robust against libmagic errors
            # Log the error for debugging purposes, but continue gracefully.
            logger.warning(
                "python-magic failed to detect mime type for %r: %s. Falling back to mimetypes.",
                path,
                e,
            )
    mime, _ = mimetypes.guess_type(path)
    return (mime or "application/octet-stream"), "mimetypes"