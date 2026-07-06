"""Magic-byte sniffing for user uploads.

Uploads (hero photos, BirdNET clips) arrive as raw request bodies. Trusting the client's
Content-Type lets a caller store arbitrary bytes or hand malformed input to the audio decoder
(a 500). These check the actual leading bytes instead.
"""

from __future__ import annotations

# (leading signature, media type) - covers the formats the client actually produces.
_IMAGE_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
]


def sniff_image(data: bytes) -> str | None:
    """Return the detected image media type from the leading bytes, or None if it isn't one."""
    for sig, media_type in _IMAGE_SIGNATURES:
        if data.startswith(sig):
            return media_type
    # WebP is RIFF-framed: "RIFF" <4-byte size> "WEBP".
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def is_wav(data: bytes) -> bool:
    """Whether the bytes are a RIFF/WAVE (.wav) container, which the client records."""
    return data[:4] == b"RIFF" and data[8:12] == b"WAVE"
