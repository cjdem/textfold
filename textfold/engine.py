"""MinerU's v4 API (the official base, or a v4-compatible one set in the reader).

TextFold sends the kinds MinerU reads to its servers and turns the returned zip into the same
structured_content.json the rest of the reader already consumes. There is no local MinerU install and no local PDF
reader: every PDF goes to MinerU. Some Office, EPUB, CSV and HTML files are still read on this computer by office.py. A
file sent to MinerU leaves this computer.

Two tiers: fast is MinerU's pipeline, with formulas as pictures; accurate is its vision model, with formulas as LaTeX and
tables laid out. The API does not read EPUB, CSV/TSV, MHTML, OFD, TIFF or the legacy kinds in LEGACY; TextFold's own
readers handle EPUB, CSV/TSV and MHTML, the others are not taken as new files."""
import hashlib
import http.client
import json
import re
import shutil
import subprocess
import threading
import time
import urllib.error
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

# MinerU's API: the only MinerU path. Its zip (full.md, *_content_list_v2.json, images/) becomes the same
# structured_content.json below. The base is the setting `mineru_api_url` (official by default; see models.MINERU_API).
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


class Resumable(RuntimeError):
    """The conversion stopped for now, with its batch and its out/ kept: importing the same file again continues it
    instead of uploading the paper again."""


class _ApiError(RuntimeError):
    """An error the API answered with (HTTP 200, a code in the JSON): its code says whether waiting could help."""

    def __init__(self, code, msg=""):
        super().__init__(f"the MinerU API: {msg or code}")
        self.code = code


class _BatchGone(RuntimeError):
    """The API no longer has the batch: only a new one can read the file."""


class _NoFile(RuntimeError):
    """The API has the batch but none of the file: the upload did not land."""


class _UploadRejected(RuntimeError):
    """The signed URL refused the file (expired, or the upload it signs is gone)."""

    def __init__(self, status):
        super().__init__(f"the file could not be uploaded ({status})")
        self.status = status


class _UploadLost(RuntimeError):
    """The batch still has no file after the upload's tries: it can be replaced."""


class _DownloadGone(RuntimeError):
    """The result link no longer works: the batch can be asked for a fresh one."""


class _DownloadFailed(RuntimeError):
    """The result could not be fetched (a dropped connection, a timeout): trying it again may work."""


STATE_NAME = "_mineru.json"   # in a conversion's out/: the batch and the stage an interrupted attempt reached
STATE_V = 1
RETRY_DELAYS = (1, 2, 4, 8, 15, 30)   # seconds between tries of one call
LAND_GRACE = 30          # an upload whose answer was lost may still be arriving at the batch
POLL_EVERY = 3
WAIT_LIMIT = 30 * 60     # one wait for the file to be read
MAX_MISSES = 10          # polls in a row that cannot be made (a few minutes with the delays below)
MAX_BATCHES = 2          # a batch, and one replacement when the API no longer has it
MAX_ZIPS = 2

# The API's codes that end a conversion by themselves, a code that means the task is gone, and one that means its file
# never arrived. Every other code is the file's or the key's own refusal: trying again cannot change it.
_TRANSIENT_CODES = {"-10001", "-60001", "-60007", "-60008", "-60009"}
_RESTART_CODES = {"-60012"}
_NO_FILE_CODES = {"-60011"}


def _why(e):
    """A failure's first line, short enough for a job's log (no message here carries the key)."""
    text = str(e).strip().splitlines()
    return (text[0] if text else e.__class__.__name__)[:300]


def _transient(e):
    """Whether calling again could work: the connection, the service's own trouble, a truncated answer. A bad key, a
    file the API refuses and our own parse do not become true by waiting."""
    if isinstance(e, _ApiError):
        return str(e.code) in _TRANSIENT_CODES
    if isinstance(e, urllib.error.HTTPError):
        return e.code in (408, 429) or e.code >= 500
    if isinstance(e, urllib.error.URLError):
        return True
    if isinstance(e, _UploadRejected):
        return e.status in (408, 429) or e.status >= 500
    if isinstance(e, _DownloadFailed):
        return True
    if isinstance(e, (http.client.HTTPException, TimeoutError, ConnectionError, json.JSONDecodeError)):
        return True
    if isinstance(e, OSError):   # (a socket's own error; a missing file or a refused write is not one)
        return not isinstance(e, (FileNotFoundError, PermissionError, IsADirectoryError, NotADirectoryError))
    return False


def _pause(stop, seconds):
    """Waits between tries, unless the reader stopped the job: True when it did."""
    if stop is not None:
        return stop.wait(seconds)
    time.sleep(seconds)
    return False


def _retry(stop, log, what, call, tries=3):
    """call() again after a transient failure, pausing between tries. The last failure raises Resumable when waiting
    could help (its out/ and state are kept), or the error itself when it cannot."""
    for i in range(tries):
        try:
            return call()
        except Exception as e:
            if isinstance(e, (Stopped, _BatchGone, _NoFile, _DownloadGone)) or not _transient(e):
                raise
            if i == tries - 1:
                raise Resumable(f"{what} failed ({_why(e)}); trying the conversion again resumes it") from e
            delay = RETRY_DELAYS[min(i, len(RETRY_DELAYS) - 1)]
            log(f"the MinerU API: {what} failed ({_why(e)}); trying again in {delay}s")
            if _pause(stop, delay):
                raise Stopped()


def api_key():
    """The MinerU cloud API's key from the reader's settings (settings.json, beside the papers), or "" when none."""
    from . import models
    key = models.load_settings().get("mineru_api_key") or ""
    return key.strip() if isinstance(key, str) else ""


def key_ok(key):
    """Whether key is one printable, whitespace-free word (what can safely go in an Authorization header)."""
    return bool(key) and all(ch.isprintable() and not ch.isspace() for ch in key)


def base_ok(url):
    """A v4-compatible base as it is stored and called (no trailing /), or "" when it is not one: http(s), a host, no
    query, fragment or sign-in, and no whitespace. The path is the reader's business (a proxy may add one)."""
    if not isinstance(url, str):
        return ""
    url = url.strip()
    if not url or any(not ch.isprintable() or ch.isspace() for ch in url):
        return ""
    if "?" in url or "#" in url:   # (a raw delimiter, even an empty query, is not a base)
        return ""
    try:
        u = urllib.parse.urlsplit(url)
        _ = u.port   # (a non-numeric port raises here, before any request is made)
    except ValueError:
        return ""
    if u.scheme not in ("http", "https") or not u.hostname or u.query or u.fragment or u.username or u.password \
            or "@" in u.netloc:
        return ""
    return urllib.parse.urlunsplit((u.scheme, u.netloc, u.path.rstrip("/"), "", ""))


def _configured_base():
    """The setting as stored (text stripped), or None when the file holds null: an absent key is already the default
    (a string). Absent, empty and null mean the official base. Any other non-text value is returned as it is, so
    api_base() refuses it rather than calling it empty."""
    from . import models
    raw = models.load_settings().get("mineru_api_url")
    return raw.strip() if isinstance(raw, str) else raw


def api_base():
    """The base a conversion calls: the setting normalized, or the official one when none is set. A saved value that is
    not usable raises before a socket is opened, rather than silently sending the file to the official service."""
    from . import models
    raw = _configured_base()
    if raw is None or raw == "":
        return models.MINERU_API
    if isinstance(raw, str):
        clean = base_ok(raw)
        if clean:
            return clean
    raise RuntimeError("bad-mineru-url")


def available():
    """Whether the MinerU cloud API can convert a file now (a key is set)."""
    return bool(api_key())


def readable(ext):
    """Whether the MinerU cloud API reads this kind and a key is set. The kinds it does not read are TextFold's own
    readers, or are refused."""
    return bool(api_key() and ext in API_FILES)


def _utf8_safe(text):
    """The text as UTF-8 can carry it: a hand-edited lone surrogate is replaced, so the page's JSON still encodes and
    the settings page that fixes the value can open."""
    return text.encode("utf-8", "replace").decode("utf-8")


def status():
    """What the settings page shows. Never raises: a hand-edited, invalid address must not make the page that fixes it
    unopenable, so it is reported with baseOk false instead of through api_base()."""
    from . import models
    raw = _configured_base()
    clean = base_ok(raw)
    if clean:
        base, ok = clean, True
    elif raw is None or raw == "":
        base, ok = models.MINERU_API, True
    else:
        base, ok = _utf8_safe(raw if isinstance(raw, str) else str(raw)), False
    return {"api": bool(api_key()), "service": "MinerU API", "version": "v4",
            "base": base, "official": models.MINERU_API, "baseOk": ok, "tiers": list(TIERS)}


def convert(pdf, out, tier="fast", progress=lambda *a: None, log=lambda *a: None, stop=None):
    """A file the API reads converted into out/ through MinerU's servers: structured_content.json and images/, and a
    PDF itself as input.pdf. The API is the only MinerU path; without a key or for a kind it does not read, this fails
    before anything is uploaded."""
    ext = kind_of(str(pdf))
    if not api_key():
        raise RuntimeError("needs-mineru-key")
    if ext not in API_FILES:
        raise RuntimeError("not-supported")
    base = api_base()   # (one base for the whole conversion: a settings save mid-job cannot redirect its polls)
    try:
        return _convert_api(pdf, out, tier, progress, log, stop, base)
    except Resumable:
        raise
    except Exception:   # (a refusal, or a stop: no state is left to resume a batch that will not be read)
        (Path(out) / STATE_NAME).unlink(missing_ok=True)
        raise


PDF = "input.pdf"


def _unzip(z, out):
    """A zip into out/, and nothing outside it."""
    with zipfile.ZipFile(z) as f:
        for name in f.namelist():
            if name.startswith("/") or ".." in Path(name).parts:
                raise RuntimeError("unsafe path in the engine's output")
        f.extractall(out)
    z.unlink()


# ── MinerU's API (the configured v4 base) ───────────────────────────────────────────────────────────────────────
# The file is uploaded, read on MinerU's servers and its zip brought back; the zip's own formats (full.md,
# *_content_list_v2.json, images/) are written into the same structured content consumed by pdfdoc, so everything after
# the conversion sees no difference. The API's boxes are 0-1000 of the page's width and height.

def _fingerprint(file):
    """What identifies a file across attempts: its size and its bytes, not its path. The server converts
    uploads/<pid>.pdf and the command line converts the file where the reader left it; the same bytes must find the
    state the other wrote."""
    file = Path(file)
    h = hashlib.sha256()
    with open(file, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return {"size": file.stat().st_size, "sha256": h.hexdigest()}


def _new_state(pdf, base, pass_no, model):
    return {"v": STATE_V, "file": _fingerprint(pdf), "base": base, "pass": pass_no, "model": model,
            "batch_id": "", "uploaded": False, "stage": "start", "updated": time.time()}


def _state_load(out, file, base):
    """The state an earlier attempt left for this very file, or None: a changed file, an older version, or a folder
    without one starts from the beginning (and what it wrote is thrown away)."""
    try:
        st = json.loads((Path(out) / STATE_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(st, dict) or st.get("v") != STATE_V or st.get("file") != _fingerprint(file):
        return None
    if not isinstance(st.get("base"), str) or not st["base"]:
        st["base"] = base
    return st


def _state_save(out, st):
    """The state beside its output, in one replacement: a crash leaves the old file or the new one, never half. The
    shared writer is used because two processes can convert the same file: a unique temporary name and a move that
    retries leave one whole state, not their mixture."""
    from . import store
    st["updated"] = round(time.time(), 3)
    store.write_text_atomic(Path(out) / STATE_NAME, json.dumps(st))


def _api(path, body=None, base=None):
    """A call to the API (a batch's creation, its state): its JSON. `base` is the conversion's base; a call made on its
    own reads the setting. A key that is not one printable word is refused here, before urllib could put it in an error
    message (which the job log would keep)."""
    key = api_key()
    if not key_ok(key):
        raise RuntimeError("the MinerU API key in settings.json is not valid")
    base = base or api_base()
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method="POST" if data is not None else "GET",
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                                          "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _put(url, file):
    """The file to its signed upload URL. http.client, not urllib: urllib adds a Content-Type, and the signature
    (computed over the headers) then does not match."""
    u = urllib.parse.urlsplit(url)
    cls = http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection
    conn = cls(u.hostname, u.port, timeout=300)   # (the signed URL's scheme and port, not the API's)
    try:
        conn.request("PUT", u.path + ("?" + u.query if u.query else ""), body=Path(file).read_bytes())
        r = conn.getresponse()
        r.read()
        if r.status not in (200, 201):
            raise _UploadRejected(r.status)
    finally:
        conn.close()


def _get(url, dest):
    """The result zip. Its host refuses Python's TLS handshake (every context tried), the system's curl does not;
    curl is used when there is one (Windows ships it), urllib otherwise."""
    curl = shutil.which("curl")
    if curl:
        r = subprocess.run([curl, "-sS", "-f", "-L", "--max-time", "600", "-w", "%{http_code}", "-o", str(dest), url],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            status = int((r.stdout or "").strip() or 0)
        except ValueError:
            status = 0
        if r.returncode == 22:   # (curl: the server answered an HTTP error; its code says whether the link is dead)
            Path(dest).unlink(missing_ok=True)
            why = (r.stderr or "").strip()[-300:] or f"the result link answered {status}"
            if status == 0 or status in (408, 429) or status >= 500:
                raise _DownloadFailed(f"the result could not be downloaded: {why}")
            raise _DownloadGone(why)
        if r.returncode or not Path(dest).exists():
            Path(dest).unlink(missing_ok=True)
            raise _DownloadFailed(f"the result could not be downloaded: {(r.stderr or '').strip()[-300:]}")
        return
    try:
        with urllib.request.urlopen(url, timeout=600) as f:
            Path(dest).write_bytes(f.read())
    except Exception as e:
        Path(dest).unlink(missing_ok=True)
        if isinstance(e, urllib.error.HTTPError) and 400 <= e.code < 500 and e.code not in (408, 429):
            raise _DownloadGone(str(e)) from e
        raise


def _new_batch(pdf, is_ocr, model, base, stop, log):
    """A batch for this file: (its id, the signed URL to upload it to). A lost answer leaves a batch nobody can name
    again — there is no call that lists them — but one with no file never starts to be read."""
    body = {"files": [{"name": Path(pdf).name, "is_ocr": bool(is_ocr)}], "model_version": model}

    def call():
        r = _api("/file-urls/batch", body, base=base)
        code = r.get("code")
        if code not in (0, None):
            raise _ApiError(code, r.get("msg"))
        data = r.get("data") or {}
        if not data.get("batch_id") or not data.get("file_urls"):
            raise RuntimeError(f"the MinerU API refused the file: {r.get('msg') or code}")
        return data["batch_id"], data["file_urls"][0]

    batch_id, url = _retry(stop, log, "the batch", call)
    log(f"the MinerU API reads it ({model}{', OCR' if is_ocr else ''})")
    return batch_id, url


def _landed(batch_id, name, stop, log, base):
    """Whether a file whose upload answer was lost reached the batch: its state leaves waiting-file. A batch the API
    no longer has is not evidence that it did; a poll that cannot be made is no evidence at all, and raises Resumable
    rather than replace a batch that may be reading the file."""
    deadline = time.monotonic() + LAND_GRACE
    last = None   # (the last state the batch answered with; None when the last poll gave no answer about a file)
    while True:
        try:
            got = _api(f"/extract-results/batch/{batch_id}", base=base)
            code = got.get("code")
            if code not in (0, None) and str(code) not in _TRANSIENT_CODES:
                return False   # (gone, or refused: the caller's poll reports it properly)
            rows = (got.get("data") or {}).get("extract_result") or []
            row = next((x for x in rows if x.get("file_name") == name), rows[0] if rows else None)
            last = row.get("state") if row is not None else None
            if last not in (None, "waiting-file"):
                return True
        except Exception as e:
            if not _transient(e):
                return False
            last = None
        left = deadline - time.monotonic()
        if left <= 0:
            if last == "waiting-file":   # (the batch answered, and had no file: it can be replaced)
                return False
            raise Resumable("the MinerU API could not be reached; trying the conversion again continues this batch")
        if _pause(stop, min(POLL_EVERY, left)):
            raise Stopped()


def _put_retry(url, pdf, batch_id, name, log, stop, base):
    """The file to its signed URL, trying a few times. When the answer is lost the batch is asked before giving up:
    the bytes may already be there, and MinerU submits the task as soon as they are."""
    try:
        _retry(stop, log, "the upload", lambda: _put(url, pdf))
    except Resumable as e:
        if _landed(batch_id, name, stop, log, base):
            return
        raise _UploadLost(str(e)) from e


def _get_retry(url, dest, log, stop):
    _retry(stop, log, "the download", lambda: _get(url, dest), tries=3)   # (a hung link: 3 x 600 s at most)


def _api_wait(batch_id, name, log, stop, base):
    """The batch's row for this file, once read there (with its zip's URL). A lost connection is waited out on the
    same batch — the API is still reading the file — and a stop stops it. Only a batch the API no longer has, or one
    with no file, is the caller's cue to act; every other failure is waited out here."""
    seen, deadline, misses = None, time.monotonic() + WAIT_LIMIT, 0
    while True:
        if time.monotonic() > deadline:   # (a poll with no rows never ends it by itself)
            raise Resumable("the MinerU API did not finish the file in time; trying the conversion again continues "
                            "this batch")
        if (stop.wait(POLL_EVERY) if stop is not None else time.sleep(POLL_EVERY)):
            raise Stopped()
        failure = None
        try:
            got = _api(f"/extract-results/batch/{batch_id}", base=base)
        except Exception as e:
            if not _transient(e):
                raise
            got = None
            failure = e
        if got is not None and got.get("code") in (0, None):
            misses = 0
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
            continue
        if got is not None:   # an error comes as JSON with HTTP 200 (an expired token, a quota, the task gone)
            code = got.get("code")
            if str(code) in _RESTART_CODES:
                raise _BatchGone(f"the MinerU API no longer has the task ({got.get('msg') or code})")
            if str(code) in _NO_FILE_CODES:
                raise _NoFile(f"the MinerU API has no file for the task ({got.get('msg') or code})")
            if str(code) not in _TRANSIENT_CODES:
                raise _ApiError(code, got.get("msg"))
            failure = _ApiError(code, got.get("msg"))
        misses += 1
        if misses >= MAX_MISSES:
            raise Resumable(f"the MinerU API could not be reached ({_why(failure)}); trying the conversion again "
                            "continues this batch") from failure
        delay = RETRY_DELAYS[min(misses - 1, len(RETRY_DELAYS) - 1)]
        log(f"the MinerU API: the poll failed ({_why(failure)}); trying again in {delay}s")
        if _pause(stop, delay):
            raise Stopped()


def _api_read(pdf, out, tier, is_ocr, log, stop, base, st):
    """One pass through the API: uploaded, read there, its zip unpacked into out/, made into structured content (and
    the input file copied beside it). A state a lost connection left continues at its stage — a batch already made is
    polled, a file already uploaded is not sent again, a pass already parsed is not fetched again."""
    ext = kind_of(str(pdf)) or "pdf"
    name = Path(pdf).name
    model = API_TIERS.get(tier_for(pdf, tier), "vlm")
    st["model"] = model
    out = Path(out)
    url, batches, zips, refused = "", 0, 0, 0
    while True:
        if not st.get("batch_id"):
            if batches >= MAX_BATCHES:
                raise Resumable("the MinerU API kept losing the task; trying the conversion again starts a new batch")
            try:
                batch_id, url = _new_batch(pdf, is_ocr, model, base, stop, log)
            except _ApiError as e:
                if str(e.code) != "-60003" or batches:   # (the API could not read the upload: send it once more)
                    raise
                batches += 1
                log("the MinerU API could not read the upload; sending the file once more")
                continue
            batches += 1
            refused = 0
            st.update(batch_id=batch_id, uploaded=False, stage="created")
            _state_save(out, st)
        if not st.get("uploaded"):
            if url:
                try:
                    _put_retry(url, pdf, st["batch_id"], name, log, stop, base)
                except (_UploadRejected, _UploadLost):
                    st.update(batch_id="", uploaded=False, stage="reupload")
                    _state_save(out, st)
                    url = ""
                    continue
                st.update(uploaded=True, stage="uploaded")
                _state_save(out, st)
            elif _landed(st["batch_id"], name, stop, log, base):
                st.update(uploaded=True, stage="uploaded")
                _state_save(out, st)
            else:   # (no signed URL is kept: a batch whose file never arrived is replaced, not re-signed)
                st.update(batch_id="", uploaded=False, stage="not-uploaded")
                _state_save(out, st)
                continue
        try:
            row = _api_wait(st["batch_id"], name, log, stop, base)
        except _BatchGone:
            st.update(batch_id="", uploaded=False, stage="gone")
            _state_save(out, st)
            url = ""
            continue
        except _NoFile:
            refused += 1
            if refused > 1:   # (the same signed URL did not take the file twice: a new batch is the way forward)
                st.update(batch_id="", uploaded=False, stage="no-file")
                url = ""
            else:
                st.update(uploaded=False, stage="no-file")
            _state_save(out, st)
            continue
        z = out / "result.zip"
        try:
            _get_retry(row["full_zip_url"], z, log, stop)
        except _DownloadGone as e:
            z.unlink(missing_ok=True)
            zips += 1
            if zips > MAX_ZIPS:
                raise Resumable(f"the result link did not work ({e}); trying the conversion again continues this "
                                "batch") from e
            log("the MinerU API: the result link did not work; asking the batch for a fresh one")
            continue
        try:
            _unzip(z, out)
        except zipfile.BadZipFile:
            z.unlink(missing_ok=True)
            zips += 1
            if zips > MAX_ZIPS:
                raise RuntimeError("the MinerU API wrote a result that is not a zip")
            log("the MinerU API: the result arrived incomplete; downloading it again")
            continue
        sc = _structured(out, ext)
        if Path(str(pdf)).suffix.lower() == ".pdf":
            shutil.copyfile(pdf, out / PDF)   # the file beside its output: a figure is cut from its page (crop)
        st.update(stage="parsed")
        _state_save(out, st)
        return sc


def _convert_api(pdf, out, tier, progress, log, stop, base):
    """A file through MinerU's API into out/, the output the engine here writes. A file with no text (a scan) is read
    again once with OCR: the API does not look at the page without being asked to. An earlier attempt's state resumes
    at its stage; it is used only for the same file, so a changed file or an older state starts from the beginning."""
    ext = kind_of(str(pdf)) or "pdf"
    out = Path(out)
    st = _state_load(out, pdf, base) if out.exists() else None
    if st is None:
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        st = _new_state(pdf, base, 1, API_TIERS.get(tier_for(pdf, tier), "vlm"))
        _state_save(out, st)
    else:
        base = st["base"]
        log(f"the MinerU API: continuing the conversion at {st.get('stage')}")
    progress("convert", 0, 0)
    if (out / "structured_content.json").exists() and st.get("stage") == "done":
        return out
    if st.get("stage") == "parsed":
        sc = _structured(out, ext)   # this pass's output is already here: no network at all
    else:
        sc = _api_read(pdf, out, tier, ext in PICTURES or st.get("pass") == 2, log, stop, base, st)
    text = any(b.get("content") for p in sc["pages"] for b in p["blocks"]
               if b["type"] in ("text", "paragraph_title", "doc_title", "list", "page_footnote"))
    if not text and ext == "pdf" and st.get("pass") == 1:   # (a picture is read with OCR from the start)
        log("no text came back: the MinerU API reads it again with OCR")
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        st = _new_state(pdf, base, 2, API_TIERS.get(tier_for(pdf, tier), "vlm"))
        _state_save(out, st)
        sc = _api_read(pdf, out, tier, True, log, stop, base, st)
    # ASCII-escaped, as MinerU's own zip is: pdfdoc reads this file as UTF-8 (read_output)
    (out / "structured_content.json").write_text(json.dumps(sc), encoding="utf-8")
    st.update(stage="done")
    _state_save(out, st)
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
