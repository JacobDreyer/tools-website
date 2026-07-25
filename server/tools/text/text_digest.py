"""Hash a blob of text every common way at once."""

import hashlib

from toolkit import Result, Tool, fields


# region: code
ALGORITHMS = ["md5", "sha1", "sha256", "sha512", "sha3_256", "blake2b"]


def digests(text, encoding="utf-8", newline="lf"):
    """Return {algorithm: hex digest} for a string, normalising line endings first."""
    body = text.replace("\r\n", "\n").replace("\r", "\n")
    if newline == "crlf":
        body = body.replace("\n", "\r\n")
    raw = body.encode(encoding, errors="strict")
    return raw, {name: hashlib.new(name, raw).hexdigest() for name in ALGORITHMS}
# endregion: code


def run(p):
    raw, hashes = digests(p["text"], p["encoding"], p["newline"])
    upper = p["uppercase"]

    out = Result()
    out.metric("Bytes", f"{len(raw):,}")
    out.metric("Characters", f"{len(p['text']):,}")
    out.metric("Lines", f"{p['text'].count(chr(10)) + 1:,}")
    out.metric("SHA-256", (hashes["sha256"].upper() if upper else hashes["sha256"])[:16] + "…",
               emphasis=True, hint="full value in the table")

    out.table(
        [{"label": "ALGORITHM", "align": "left"}, {"label": "BITS"},
         {"label": "DIGEST", "align": "left"}],
        [[name, str(len(h) * 4), h.upper() if upper else h] for name, h in hashes.items()],
        title="Digests",
    )
    return out


TOOL = Tool(
    id="text-digest",
    name="Text Digest",
    summary="MD5, SHA-1/2/3 and BLAKE2 digests of a text blob, with line-ending control.",
    description=(
        "Line endings are normalised to LF before hashing unless you pick CRLF, which is "
        "usually the reason two tools disagree about a file's checksum."
    ),
    category="text/hashing",
    inputs=[
        fields.textarea("text", "Text", "field kit", rows=8,
                        placeholder="Paste anything…"),
        fields.select("encoding", "Encoding",
                      [("utf-8", "UTF-8"), ("utf-16", "UTF-16"), ("latin-1", "Latin-1"),
                       ("ascii", "ASCII")], "utf-8"),
        fields.select("newline", "Line endings",
                      [("lf", "Normalise to LF"), ("crlf", "Normalise to CRLF")], "lf"),
        fields.boolean("uppercase", "Uppercase hex", False),
    ],
    run=run,
)
