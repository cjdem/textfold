"""MinerU's cloud API (mineru.net/api/v4).

TextFold sends the kinds MinerU reads to its servers and turns the returned zip into the same
structured_content.json the rest of the reader already consumes. There is no local MinerU install and no local PDF
reader: every PDF goes to MinerU. Some Office, EPUB, CSV and HTML files are still read on this computer by office.py. A
file sent to MinerU leaves this computer.

Two tiers: fast is MinerU's pipeline, with formulas as pictures; accurate is its vision model, with formulas as LaTeX and
tables laid out. The API does not read EPUB, CSV/TSV, MHTML, OFD, TIFF or the legacy kinds in LEGACY; TextFold's own
readers handle EPUB, CSV/TSV and MHTML, the others are not taken as new files."""
import http.client
import json
import re
import shutil
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

TIERS = {"fast": "flash", "accurate": "advanced"}
# the files it reads besides PDFs (MinerU's own list, mineru/filetypes.py), by their extension, with the name a reader
# knows them by. A picture is read like a scanned page, in either tier; the others have one way to be read (the fast
# tier: their text and structure are in the file, no model is needed)
PICTURES = {"png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "jp2"}
FILES = {"docx": "Word", "doc": "Word", "rtf": "RTF", "pptx": "PowerPoint", "ppt": "PowerPoint", "xlsx": "Excel", "xls": "Excel",
         "odt": "OpenDocument", "ods": "OpenDocument", "odp": "OpenDocument", "epub": "EPUB", "html": "HTML", "htm": "HTML",
         "mhtml": "MHTML", "mht": "MHTML", "csv": "CSV", "tsv": "TSV", "ofd": "OFD"} | {x: "Image" for x in PICTURES}
# Kinds no longer taken as new imports: old Office, RTF and OpenDocument. They stay in FILES so a document converted
# before the rule still opens; there is no local re-conversion engine any more.
LEGACY = {"doc", "ppt", "xls", "rtf", "odt", "ods", "odp"}

# MinerU's Cloud API: the only MinerU path. Its zip (full.md, *_content_list_v2.json, images/) becomes the same
# structured_content.json below.
API = "https://mineru.net/api/v4"
API_TIERS = {"fast": "pipeline", "accurate": "vlm"}
# what the API reads (its docs' list): PDFs, Office files, HTML, and these pictures — TIFF is not one of them. RTF,
# OpenDocument and old Office files are no new imports; stored results remain readable.
API_PICTURES = {"png", "jpg", "jpeg", "jp2", "webp", "gif", "bmp"}
API_FILES = {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "html", "htm"} | API_PICTURES


def kind_of(name):
    """A file's extension as the engine knows it ("tif" is its "tiff"), or None for a file it does not read."""
    ext = Path(name).suffix.lower().lstrip(".")
    ext = {"tif": "tiff", "shtml": "html"}.get(ext, ext)
    return ext if ext == "pdf" or ext in FILES else None


def tier_for(file, tier):
    """The tier a file is read in: a PDF's or a picture's as asked, any other file's the fast one."""
    ext = Path(str(file)).suffix.lower().lstrip(".")
    return tier if ext == "pdf" or ext in PICTURES else "fast"


class Stopped(Exception):
    pass


def api_key():
    """The MinerU cloud API's key from the reader's settings (settings.json, beside the papers), or "" when none."""
    from . import models
    key = models.load_settings().get("mineru_api_key") or ""
    return key.strip() if isinstance(key, str) else ""


def key_ok(key):
    """Whether key is one printable, whitespace-free word (what can safely go in an Authorization header)."""
    return bool(key) and all(ch.isprintable() and not ch.isspace() for ch in key)


def available():
    """Whether the MinerU cloud API can convert a file now (a key is set)."""
    return bool(api_key())


def readable(ext):
    """Whether the MinerU cloud API reads this kind and a key is set. The kinds it does not read are TextFold's own
    readers, or are refused."""
    return bool(api_key() and ext in API_FILES)


def status():
    return {"api": bool(api_key()), "service": "MinerU API", "version": "v4", "tiers": list(TIERS)}


def convert(pdf, out, tier="fast", progress=lambda *a: None, log=lambda *a: None, stop=None):
    """A file the API reads converted into out/ through MinerU's servers: structured_content.json and images/, and a
    PDF itself as input.pdf. The API is the only MinerU path; without a key or for a kind it does not read, this fails
    before anything is uploaded."""
    ext = kind_of(str(pdf))
    if not api_key():
        raise RuntimeError("needs-mineru-key")
    if ext not in API_FILES:
        raise RuntimeError("not-supported")
    return _convert_api(pdf, out, tier, progress, log, stop)


PDF = "input.pdf"


def _unzip(z, out):
    """A zip into out/, and nothing outside it."""
    with zipfile.ZipFile(z) as f:
        for name in f.namelist():
            if name.startswith("/") or ".." in Path(name).parts:
                raise RuntimeError("unsafe path in the engine's output")
        f.extractall(out)
    z.unlink()


# ── MinerU's cloud API (mineru.net/api/v4) ──────────────────────────────────────────────────────────────────────
# The file is uploaded, read on MinerU's servers and its zip brought back; the zip's own formats (full.md,
# *_content_list_v2.json, images/) are written into the same structured content consumed by pdfdoc, so everything after
# the conversion sees no difference. The API's boxes are 0-1000 of the page's width and height.

def _api(path, body=None):
    """A call to the API (a batch's creation, its state): its JSON. A key that is not one printable word is refused
    here, before urllib could put it in an error message (which the job log would keep)."""
    key = api_key()
    if not key_ok(key):
        raise RuntimeError("the MinerU API key in settings.json is not valid")
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, method="POST" if data is not None else "GET",
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                                          "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _put(url, file):
    """The file to its signed upload URL. http.client, not urllib: urllib adds a Content-Type, and the signature
    (computed over the headers) then does not match."""
    u = urllib.parse.urlsplit(url)
    conn = http.client.HTTPSConnection(u.hostname, timeout=300)
    try:
        conn.request("PUT", u.path + ("?" + u.query if u.query else ""), body=Path(file).read_bytes())
        r = conn.getresponse()
        r.read()
        if r.status not in (200, 201):
            raise RuntimeError(f"the file could not be uploaded ({r.status})")
    finally:
        conn.close()


def _get(url, dest):
    """The result zip. Its host refuses Python's TLS handshake (every context tried), the system's curl does not;
    curl is used when there is one (Windows ships it), urllib otherwise."""
    curl = shutil.which("curl")
    if curl:
        r = subprocess.run([curl, "-sS", "-f", "-L", "--max-time", "600", "-o", str(dest), url], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode or not Path(dest).exists():
            raise RuntimeError(f"the result could not be downloaded: {(r.stderr or '').strip()[-300:]}")
        return
    with urllib.request.urlopen(url, timeout=600) as f:
        Path(dest).write_bytes(f.read())


def _api_wait(batch_id, name, log, stop):
    """The batch's row for this file, once read there (with its zip's URL). Waits with the job, a stop stops it."""
    seen, deadline = None, time.monotonic() + 30 * 60
    while True:
        if time.monotonic() > deadline:   # (a poll with no rows, or an error, never ends it by itself)
            raise RuntimeError("the MinerU API did not finish the file in time")
        if (stop.wait(3) if stop is not None else time.sleep(3)):
            raise Stopped()
        got = _api(f"/extract-results/batch/{batch_id}")
        if got.get("code") not in (0, None):   # an error comes as JSON with HTTP 200 (an expired token, a quota)
            raise RuntimeError(f"the MinerU API: {got.get('msg') or got.get('code')}")
        rows = (got.get("data") or {}).get("extract_result") or []
        row = next((x for x in rows if x.get("file_name") == name), rows[0] if rows else None)
        if row is None:
            continue
        state = row.get("state")
        if state != seen:
            seen = state
            log(f"the MinerU API: {state}")
        if state == "done" and row.get("full_zip_url"):
            return row
        if state == "failed":
            raise RuntimeError(row.get("err_msg") or "the MinerU API could not read the file")


def _api_read(pdf, out, tier, is_ocr, log, stop):
    """One pass through the API: uploaded, read there, its zip unpacked into out/, made into structured content (and
    the input file copied beside it, as the engine here leaves it)."""
    ext = kind_of(str(pdf)) or "pdf"
    model = API_TIERS.get(tier_for(pdf, tier), "vlm")
    r = _api("/file-urls/batch", {"files": [{"name": Path(pdf).name, "is_ocr": bool(is_ocr)}], "model_version": model})
    data = r.get("data") or {}
    batch_id, urls = data.get("batch_id"), data.get("file_urls") or []
    if r.get("code") != 0 or not batch_id or not urls:
        raise RuntimeError(f"the MinerU API refused the file: {r.get('msg') or r.get('code')}")
    log(f"the MinerU API reads it ({model}{', OCR' if is_ocr else ''})")
    _put(urls[0], pdf)
    row = _api_wait(batch_id, Path(pdf).name, log, stop)
    z = Path(out) / "result.zip"
    _get(row["full_zip_url"], z)
    _unzip(z, out)
    sc = _structured(out, ext)
    if Path(str(pdf)).suffix.lower() == ".pdf":
        shutil.copyfile(pdf, Path(out) / PDF)   # the file beside its output: a figure is cut from its page (crop)
    return sc


def _convert_api(pdf, out, tier, progress, log, stop):
    """A file through MinerU's cloud API into out/, the output the engine here writes. A file with no text (a scan)
    is read again once with OCR: the API does not look at the page without being asked to."""
    ext = kind_of(str(pdf)) or "pdf"
    out = Path(out)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    progress("convert", 0, 0)
    sc = _api_read(pdf, out, tier, ext in PICTURES, log, stop)
    text = any(b.get("content") for p in sc["pages"] for b in p["blocks"]
               if b["type"] in ("text", "paragraph_title", "doc_title", "list", "page_footnote"))
    if not text and ext == "pdf":   # (a picture is read with OCR from the start)
        log("no text came back: the MinerU API reads it again with OCR")
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        sc = _api_read(pdf, out, tier, True, log, stop)
    # ASCII-escaped, as MinerU's own zip is: pdfdoc reads this file as UTF-8 (read_output)
    (out / "structured_content.json").write_text(json.dumps(sc), encoding="utf-8")
    return out


def _inline(items):
    """A block's words from its parts, as the file runs them: text as it is, a formula as $…$, a part with no words
    left out (the flat content_list.json keeps a caption as one string, the v2 as parts)."""
    parts = []
    for x in items or []:
        if isinstance(x, str):
            parts.append(x)
            continue
        c = x.get("content")
        if not isinstance(c, str) or not c.strip():
            continue
        kind = x.get("type") or ""
        parts.append(f"${c}$" if "math" in kind or "equation" in kind else c)
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def _api_block(b):
    """One API block as the engine's: its type, words or HTML, its box 0-1; None for a block with nothing in it."""
    kind, c = b.get("type"), b.get("content") or {}
    box = [round(min(1.0, max(0.0, float(x) / 1000)), 4) for x in b["bbox"]] if b.get("bbox") else None

    def block(type_, content="", **kw):
        d = {"type": type_, "content": content}
        if box:
            d["bbox"] = box
        d.update({k: v for k, v in kw.items() if v})
        return d

    def captions_at(key):
        words = _inline(c.get(key))
        return [{"content": words}] if words else []

    if kind == "title":
        words = _inline(c.get("title_content"))
        return block("paragraph_title", words, level=int(c.get("level") or 1)) if words else None
    if kind == "paragraph":
        words = _inline(c.get("paragraph_content"))
        return block("text", words) if words else None
    if kind == "list":
        lines = (_inline(i.get("item_content")) for i in c.get("list_items") or [])
        words = "\n".join("- " + x for x in lines if x)
        return block("list", words) if words else None
    if kind in ("image", "chart"):
        src = (c.get("image_source") or {}).get("path") or ""
        return block("image", "", image_source=src,
                     captions=captions_at("image_caption" if kind == "image" else "chart_caption"))
    if kind == "table":
        src = (c.get("image_source") or {}).get("path") or ""
        return block("table", c.get("html") or "", image_source=src, captions=captions_at("table_caption"),
                     footnotes=captions_at("table_footnote"))
    if kind == "equation_interline":
        return block("equation", c.get("math_content") or "", image_source=(c.get("image_source") or {}).get("path") or "")
    if kind == "page_footnote":
        words = _inline(c.get("page_footnote_content"))
        return block("page_footnote", words) if words else None
    if kind in ("page_header", "page_footer", "page_number", "aside_text"):   # (pdfdoc drops them, as the engine's)
        words = _inline(c.get(kind + "_content"))
        return block({"page_header": "header", "page_footer": "footer", "page_number": "page_number",
                      "aside_text": "aside_text"}[kind], words) if words else None
    words = _inline(c.get("content") if isinstance(c.get("content"), list) else c.get("content") or [])
    words = words or (b.get("text") or "").strip()
    return block("text", words) if words else None


def _flat(b):
    """A block of the flat content_list.json (an older service) in the v2 shape: it keeps the words under keys of its
    own (text, img_path, table_body, latex), at the top of the block."""
    kind = b.get("type")
    c = dict(b.get("content") or {})
    if kind == "text":
        c.setdefault("paragraph_content", [{"type": "text", "content": b.get("text") or ""}])
        if b.get("text_level"):
            kind = "title"
            c = {"title_content": c["paragraph_content"], "level": b["text_level"]}
    elif kind in ("image", "chart"):
        c.setdefault("image_source", {"path": b.get("img_path") or ""})
        key = "image_caption" if kind == "image" else "chart_caption"
        c.setdefault(key, b.get(key) or [])
    elif kind in ("header", "footer", "page_header", "page_footer", "page_number", "page_footnote"):
        kind = {"header": "page_header", "footer": "page_footer"}.get(kind, kind)   # (the flat names)
        c.setdefault(kind + "_content", [{"type": "text", "content": b.get("text") or ""}])
    elif kind == "list":
        c.setdefault("list_items", b.get("list_items") or [])
    elif kind == "table":
        c.setdefault("html", b.get("table_body") or "")
        c.setdefault("image_source", {"path": b.get("img_path") or ""})
        c.setdefault("table_caption", b.get("table_caption") or [])
        c.setdefault("table_footnote", b.get("table_footnote") or [])
    elif kind in ("equation", "interline_equation"):
        kind = "equation_interline"
        c.setdefault("math_content", b.get("latex") or (b.get("text") or "").strip().strip("$"))
        c.setdefault("image_source", {"path": b.get("img_path") or ""})
    return {**b, "type": kind, "content": c}


def _structured(folder, ext):
    """MinerU's cloud output as the structured content the engine here writes: pages of blocks, boxes 0-1. Its
    *_content_list_v2.json is a list of pages; the flat *_content_list.json (an older service) carries page_idx,
    and is grouped by it."""
    folder = Path(folder)
    v2 = next(iter(sorted(folder.glob("*_content_list_v2.json"))), None)
    if v2 is not None:
        pages = [[_api_block(b) for b in page] for page in json.loads(v2.read_text(encoding="utf-8"))]
    else:
        flat = next(iter(sorted(folder.glob("*_content_list.json"))), None)
        if flat is None:
            raise RuntimeError("the MinerU API wrote no document")
        rows = json.loads(flat.read_text(encoding="utf-8"))
        pages = [[] for _ in range(max((int(x.get("page_idx") or 0) for x in rows), default=-1) + 1)]
        for x in rows:
            pages[int(x.get("page_idx") or 0)].append(_api_block(_flat(x)))
    pages = [[b for b in page if b] for page in pages]
    first = next((b for b in (pages[0] if pages else []) if b.get("type") == "paragraph_title"), None)
    if first is not None:   # the paper's title is the first page's first heading, as the engine's is its doc_title
        first["type"] = "doc_title"
    return {"pages": [{"page_idx": n, "blocks": page} for n, page in enumerate(pages)],
            "metadata": {"file_suffix": ext or "pdf", "producer": {"name": "MinerU API"}, "document": {}}}

# each region of a page as a picture: pages counted from 1, the
# region in fractions of the page's width and height (as MinerU gives them), the longest edge at most 2000 px
def crop(pdf, crops):
    """Regions of a PDF's pages as pictures: crops is [(page, [x0, y0, x1, y1], out file)]; the out files written
    (a region that cannot be cut is left out)."""
    if not crops:
        return set()
    return crop_here(pdf, crops)


PDFIUM = threading.Lock()   # pdfium serves one thread at a time, and the server reads PDFs on more than one


def crop_here(pdf, crops):
    """Cut the regions from this process with pypdfium2, using MinerU's boxes. Nothing when pypdfium2 is not installed."""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return set()
    done = set()
    with PDFIUM:
        doc = pdfium.PdfDocument(str(pdf))
        try:
            for page_no, (x0, y0, x1, y1), out in crops:
                try:
                    page = doc[page_no - 1]
                    if page.get_rotation():
                        continue
                    w, h = page.get_size()
                    scale = min(3.0, 2000 / max((x1 - x0) * w, (y1 - y0) * h, 1))
                    img = page.render(scale=scale, crop=(x0 * w, (1 - y1) * h, (1 - x1) * w, y0 * h)).to_pil()
                    img.convert("RGB").save(out, quality=92)
                    done.add(str(out))
                except Exception:   # (a region that cannot be cut is left out, as there)
                    continue
        finally:
            doc.close()
    return {o for o in done if Path(o).is_file()}
