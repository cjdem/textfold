"""The local server: python -m textfold serve  ->  http://localhost:3017  (ThoughtDAG keeps 3001)

  GET  /                      landing: paste a link, pick a language, the list of papers
  GET  /p/<id>?lang=xx        a paper in the reader
  GET  /api/papers            the papers on disk, each with when it came in and was last opened (library.py)
  GET  /api/jobs              generation jobs (queued, running, recently finished)
  POST /api/jobs/stop         {id}: stop a job: a queued one is dropped; a running one ends once the model calls under way
                              return (what they wrote is kept in the cache, so starting it again goes on from there)
  POST /api/generate          {paper, lang, force}: queue a generation; one runs at a time. paper: an arXiv id or
                              link, a PMC or PPR id, a DOI (Europe PMC, epmc.py), or a stored document's id
  POST /api/import            {name, text}: store a Markdown file as a paper (local.py); its id, to generate
  GET  /api/models            every API model this computer can reach
  POST /api/models/select     {model, effort}: the model generations use; {task: "ask", model, effort}: the one questions
                              are answered with (none: the same) and its reasoning level (none: the default)
  POST /api/providers/probe   {base, api_key | key, preset}: a provider's /models. A key the server keeps (a saved
                              provider's, or a minted OpenRouter one) goes only to the address it was saved with
  POST /api/providers/save    {key?, preset, name, base, api_key?, models}  ·  POST /api/providers/remove {key}
  POST /api/settings          {use_thoughtdag_env, pdf_tier, mineru_api_key, mineru_api_url}: one change; the models
                              after it (mineru_api_url: a v4-compatible base; empty restores the official one)
  POST /api/settings/test     {model?} or {task: "ask"}: one tiny call
  GET  /api/notes/<id>        the reader's notes on a paper (docs/notes-format.md)
  POST /api/files             a file dropped on the landing, its bytes (X-Name, X-Lang): a PDF through MinerU's API,
                              or a Word, PowerPoint, Excel, EPUB, HTML file or picture through TextFold's own readers,
                              else MinerU's API (new RTF, OpenDocument and old Office files: refused, legacy-format)
  GET  /api/pdf/<id>          the paper's original PDF (arXiv, PubMed Central, bioRxiv), fetched once and kept (pdf.py)
  POST /api/pdf/<id>          the PDF itself (the reader's copy, when the server would not give it): kept the same way
  POST /api/notes/<id>        {op: "put", note} or {op: "delete", id}
  POST /api/export            {paper, lang, langs: "current" | "all", kinds: ["hl", "note", "ask"], pdf}: the paper as one
                              HTML file: its levels, the reader's notes of the kinds chosen, and (pdf) its original PDF
                              with PDF.js, for the side-by-side view
  POST /api/ask               {paper, id, question, req}: the model answers a note's question; the answer is stored in it
  POST /api/ask/stop          {req}: that question stopped: its answer, when it comes, is not stored
  GET  /api/card/<id>         the document's reading card (cards.py), with what is stale or no longer reachable
  POST /api/card/<id>         {op}: create | save | evidence | adopt | adopt_item | discard | review | generate | export
  POST /api/papers/delete     {paper}: move a paper to papers/.trash (not while it is being generated); the list. Or
                              {papers: [ids]}: each that can go; {papers: the list, deleted: [ids], busy: [ids],
                              failed: [ids]} (a folder that could not move is put back in the library, not lost)
  POST /api/papers/restore    {papers: [ids]}: those deleted last back from papers/.trash, in their folders (the
                              reader's Undo); {papers: the list, folders, restored: [ids]}
  POST /api/papers/name       {paper, name}: what the reader calls it in the library ("": its own title again); the list
  GET  /api/folders           the reader's folders (inside one another) and which document is in which (library.py)
  POST /api/folders           {op: new | rename | delete | nest | move, ...}: one change; the folders after it
  POST /api/openrouter/start   {back}: the OpenRouter consent URL (OAuth PKCE); GET /oauth/openrouter is its return
  GET  /api/zotero             Zotero Desktop (its local API): running, its libraries, the one chosen (zotero.py)
  GET  /api/zotero/collections ?lib=users/0 | groups/<id>: the library's collections, each with its parent
  GET  /api/zotero/items       ?lib=…&collection=<key>&q=…: its items, each with the document it became, if any
  POST /api/zotero/library     {library}: the one to browse, kept
  POST /api/zotero/read        {item: "<lib>/<key>", lang}: an item read. {ref} for its paper online, generated as a
                               link is; else its file, taken as a file dropped on the landing is (/api/files' reply)

Loopback only, and POSTs from other origins are refused. A GET or POST addressed to any name but this computer's own
(localhost, 127.0.0.1, [::1]) is answered 421 and nothing else: a web page that points its own domain at 127.0.0.1 (DNS
rebinding) is the same origin as its requests to the browser, so only the name they carry tells them apart. Settings and
keys live in ~/.textfold/settings.json (mode 600), never in the project folder, which may be synced or shared.
"""
import base64
import json
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
import traceback
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from . import build, cards, engine, fetch, langs, library, llm, local, models, notes, office, openrouter, pdf, pdfdoc, pipeline, providers, store, zotero

STATIC = {"app.js": "text/javascript", "app.css": "text/css", "reader.js": "text/javascript",
          "card.js": "text/javascript", "card.css": "text/css", "reader.css": "text/css",
          "i18n.js": "text/javascript", "tutorial.js": "text/javascript"}
# fonts and KaTeX, kept here so that no page asks another server for them (web/vendor)
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
VENDOR_TYPES = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8", ".woff2": "font/woff2",
                ".txt": "text/plain; charset=utf-8"}


def vendor_file(rel):
    """A file of web/vendor by its path under /static/vendor/, or None: nothing outside it, nothing but those kinds."""
    root = (build.WEB / "vendor").resolve()
    f = (root / rel).resolve()
    return f if rel and root in f.parents and f.is_file() and f.suffix in VENDOR_TYPES else None


def models_payload():
    s = models.load_settings()
    cat, provs = models.catalog(s)
    selected = models.default_model(s, cat)
    ask, ask_effort = models.ask_choice(s, cat)
    name = lambda mid: next((m["name"] for m in cat if m["id"] == mid), mid)
    return {
        "models": cat, "selected": selected, "selectedName": name(selected),
        "askModel": ask, "askEffort": ask_effort, "askName": name(ask) if ask and ask != selected else "",
        "efforts": s.get("efforts") or {},
        "providers": [{"key": p["key"], "name": p["name"], "source": p["source"], "base": p["base"], "protocol": p["protocol"],
                       "preset": p.get("preset"), "models": [m["id"] for m in p["models"]],
                       "hasKey": bool(p["api_key"]) and p["api_key"] not in ("none", "ollama")} for p in provs],
        "presets": providers.PRESETS[:-1] + [models.ANTHROPIC_PRESET, providers.PRESETS[-1]],
        "useThoughtdagEnv": s.get("use_thoughtdag_env", True), "thoughtdagEnv": providers.THOUGHTDAG_ENV.exists(),
        "pdfTier": s.get("pdf_tier") or "fast", "mineru": engine.status(),
    }


class Jobs:
    """Two queues, each worked one job at a time: generation (model calls) and MinerU conversions (uploads and polling),
    so that one document converts while another is generated."""

    def __init__(self):
        self.items, self.q, self.cq = {}, queue.Queue(), queue.Queue()
        self.stops = {}   # job id -> threading.Event, set when the reader stops it (kept out of the job: it is sent as JSON)
        threading.Thread(target=self.work, daemon=True).start()
        threading.Thread(target=self.work_convert, daemon=True).start()

    def _new(self, q, **kw):
        job = {"id": uuid.uuid4().hex[:10], "kind": "generate", "pid": "", "lang": "", "force": False, "status": "queued",
               "stage": "queued", "done": 0, "total": 0, "error": "", "log": [], "created": time.time(), "finished": None, **kw}
        self.items[job["id"]] = job
        self.stops[job["id"]] = threading.Event()
        q.put(job["id"])
        return job

    def _same(self, **kw):   # the same request already waiting or running is that job
        return next((j for j in self.items.values() if j["status"] in ("queued", "running") and all(j.get(k) == v for k, v in kw.items())), None)

    def submit(self, ref, lang, force):
        pid = store.resolve(ref)
        return self._same(kind="generate", pid=pid, lang=lang) or self._new(self.q, pid=pid, lang=lang, force=bool(force))

    def card(self, pid, lang):
        """A reading card draft (cards.py): its own job, so the reader sees its progress and can stop it, and so it is
        not mistaken for a generation of the document. A draft in another language is another job."""
        return self._same(kind="card", pid=pid, lang=lang) or self._new(self.q, kind="card", pid=pid, lang=lang, title="Reading card")

    def convert(self, pid, file, name, lang, tier=None, replace=False):
        """A file through MinerU's API (then generated): file is on disk; replace converts a stored one again."""
        tier = engine.tier_for(file, tier or models.load_settings().get("pdf_tier") or "fast")
        return self._same(kind="convert", pid=pid) or self._new(self.cq, kind="convert", pid=pid, lang=lang, file=str(file), name=name,
                                                                title=name, tier=tier, replace=bool(replace))

    def stop(self, job_id):
        job = self.items.get(job_id)
        if not job or job["status"] not in ("queued", "running"):
            return job
        if job["status"] == "queued":   # never started: off the queue (work() skips it)
            job.update(status="stopped", finished=time.time())
        else:
            job["stopping"] = True
            self.stops[job_id].set()
        return job

    def _progress(self, job, stop):
        def progress(stage, done, total):
            if stop.is_set() and stage != "done":   # a fetch that reports (bioRxiv's paced figures) ends here too
                raise llm.Stopped()
            job.update(stage=stage, done=done, total=total)
            if stage in ("ladder", "translate", "zh", "done"):   # parsed: the reader can open it (in its own words)
                job["readable"] = True
            if job["kind"] == "generate" and stage not in ("queued", "fetch") and (store.pdir(job["pid"]) / "meta.json").exists():
                if not job.get("title"):   # a new paper's title, once it is parsed
                    try:
                        job["title"] = json.loads(store.read_text(store.pdir(job["pid"]) / "meta.json"))["title"]
                    except (OSError, ValueError, KeyError):
                        pass
        return progress

    def _log(self, job):
        def log(line):
            job["log"] = (job["log"] + [line])[-40:]
        return log

    def _end(self, job, e, stop):
        if job["pid"] and (store.pdir(job["pid"]) / "source.html").exists():
            job["readable"] = True   # what failed was its levels: it reads as written
        if isinstance(e, (llm.Stopped, engine.Stopped)) or stop.is_set():
            job.update(status="stopped", stopping=False)
        else:
            job.update(status="error", error="no-model" if str(e).startswith("No model is available") else str(e))
            self._log(job)(traceback.format_exc()[-800:])
            # the last lines to stdout too, which MyGo keeps as server.log: a failure is visible after the page is gone
            print(f"job {job['id']} {job['pid']} {job['lang']} failed:\n" + "\n".join(job["log"][-12:]), flush=True)
        job["finished"] = time.time()
        PAGES.pop(job["pid"], None)

    def _card_progress(self, job, stop):
        def progress(stage, done, total):
            if stop.is_set():
                raise llm.Stopped()
            job.update(stage=stage, done=done, total=total)
        return progress

    def work(self):
        while True:
            job = self.items[self.q.get()]
            if job["status"] == "stopped":
                continue
            job["status"] = "running"
            stop = self.stops[job["id"]]
            try:
                try:
                    spec = models.resolve(None)  # the model chosen in the settings, resolved once per job
                    job["model"] = spec["id"]
                except RuntimeError:   # none: the paper is still fetched and parsed, to be read as written
                    spec = None
                if job["kind"] == "card":
                    if spec is None:
                        raise RuntimeError("No model is available: add an API provider in Settings")
                    cards.generate(job["pid"], job["lang"] or "en", models.for_task(spec, "card"),
                                   progress=self._card_progress(job, stop), log=self._log(job), stop=stop)
                    job["status"] = "done"
                    job["finished"] = time.time()
                    continue
                pipeline.generate(job["pid"], job["lang"], spec, force=job["force"], progress=self._progress(job, stop), log=self._log(job), stop=stop,
                                  also_zh=True)   # an English document is read in Simplified Chinese by default
                job["status"] = "done"
            except Exception as e:  # shown in the app; the traceback stays in the job log
                if str(e) == "no-html" and not stop.is_set():
                    try:   # an arXiv paper without its HTML version: its PDF, through MinerU
                        self._pdf_link(job, f"https://arxiv.org/pdf/{job['pid']}")
                        continue
                    except Exception:   # arXiv's PDF out of reach too: the app's own sentence for no HTML
                        pass
                if str(e) == "web-pdf" and not stop.is_set():
                    try:
                        self._pdf_link(job)   # a link to a PDF: the file, as if it had been dropped on the landing
                        continue
                    except Exception as e2:
                        e = e2
                self._end(job, e, stop)
                continue
            job["finished"] = time.time()
            PAGES.pop(job["pid"], None)

    def _pdf_link(self, job, url=None):
        url = url or store.read_url(store.pdir(job["pid"]) / "url.txt").strip()
        with urllib.request.urlopen(urllib.request.Request(url, headers=fetch.UA), timeout=90) as r:
            data = r.read(pdf.LIMIT + 1)
        if data[:5] != b"%PDF-" or len(data) > pdf.LIMIT:
            raise ValueError("not-pdf")
        shutil.rmtree(store.pdir(job["pid"]), ignore_errors=True)   # (only its address was there)
        pid = pdfdoc.pid_of(data)
        name = Path(urllib.parse.urlparse(url).path).name or "document.pdf"
        f = store.DATA / "uploads" / f"{pid}.pdf"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        job["finished"] = time.time()
        if (store.pdir(pid) / "meta.json").exists():   # read before
            f.unlink()
            job.update(status="moved", next=self.submit(pid, job["lang"], False)["id"])
        elif engine.available():
            job.update(status="moved", next=self.convert(pid, f, name, job["lang"])["id"])
        else:
            f.unlink(missing_ok=True)
            job.update(status="error", error="needs-mineru-key")

    def work_convert(self):
        while True:
            job = self.items[self.cq.get()]
            if job["status"] == "stopped":
                continue
            job["status"] = "running"
            stop = self.stops[job["id"]]
            progress, log = self._progress(job, stop), self._log(job)
            try:
                out = store.DATA / "uploads" / f"{job['pid']}-{job['tier']}"
                try:
                    engine.convert(job["file"], out, job["tier"], progress, log, stop)
                except Exception:   # a file MinerU could not read: TextFold's own reader, if it has one
                    if stop.is_set() or not office.reads(engine.kind_of(job["file"])):
                        raise
                    log("MinerU could not read this file: TextFold reads it itself")
                    office.convert(job["file"], out)
                pdfdoc.store_pdf(job["pid"], out, pdfdoc.read_output(out), job["name"], job["tier"], replace=job["replace"])
                src = store.pdir(job["pid"]) / pdfdoc.kept_name(job["pid"], job["file"])   # the file itself, kept
                if not src.exists():
                    src.write_bytes(Path(job["file"]).read_bytes())
                shutil.rmtree(out, ignore_errors=True)
                if Path(job["file"]).parent == store.DATA / "uploads":
                    Path(job["file"]).unlink(missing_ok=True)
                    Path(job["file"]).with_suffix(".json").unlink(missing_ok=True)
                PAGES.pop(job["pid"], None)
                job["readable"] = True
                job["next"] = self.submit(job["pid"], job["lang"] or "en", False)["id"]   # its levels, in the other queue
                job.update(status="done", finished=time.time())
            except Exception as e:
                if job["kind"] == "convert":   # what MinerU wrote before it failed
                    shutil.rmtree(store.DATA / "uploads" / f"{job['pid']}-{job['tier']}", ignore_errors=True)
                self._end(job, e, stop)

    def list(self):
        now = time.time()
        return [j for j in self.items.values() if j["status"] in ("queued", "running") or now - (j["finished"] or now) < 600]


def _named(headers):
    """A dropped file's name and the language to read it in, from the request's headers."""
    lang = headers.get("X-Lang") or "en"
    return Path(unquote(headers.get("X-Name") or "document.pdf")).name[:200] or "document.pdf", lang if lang in langs.LANGS else "en"


def take_file(jobs, data, headers):
    """A file from the landing, as (reply, status): a PDF (take_pdf), or another kind. TextFold's own readers go first,
    so Word, PowerPoint, Excel, EPUB, CSV, TSV, HTML and MHTML stay on this computer; a kind only MinerU reads goes to
    its API and needs a key. New imports of RTF, OpenDocument and old Office files are refused with `legacy-format`;
    a file of one of those kinds converted before the rule still opens."""
    name, lang = _named(headers)
    ext = engine.kind_of(name)
    if data[:5] == b"%PDF-" or ext == "pdf":
        return take_pdf(jobs, data, headers)
    if not ext:
        return {"error": "not-supported"}, 400
    pid = pdfdoc.pid_of(data, ext)
    if (store.pdir(pid) / "meta.json").exists():   # this file, converted before (even a kind no longer imported)
        return {"job": jobs.submit(pid, lang, False), "via": "file"}, 200
    if ext in engine.LEGACY:
        return {"error": "legacy-format"}, 400
    f = store.DATA / "uploads" / f"{pid}.{ext}"
    f.parent.mkdir(parents=True, exist_ok=True)
    if not f.exists():
        f.write_bytes(data)
    if office.reads(ext):
        try:
            office.save(pid, f, name)
        except ValueError:
            if not engine.readable(ext):
                f.unlink(missing_ok=True)
                return {"error": "bad-file"}, 400
            return {"job": jobs.convert(pid, f, name, lang), "via": "file"}, 200
        f.unlink(missing_ok=True)
        # read: it opens now, as a converted PDF does, while its levels are written (no model is needed to read it)
        return {"job": jobs.submit(pid, lang, False), "paper": pid, "via": "file"}, 200
    if engine.readable(ext):
        return {"job": jobs.convert(pid, f, name, lang), "via": "file"}, 200
    f.unlink(missing_ok=True)
    if ext in engine.API_FILES:
        return {"error": "needs-mineru-key", "upload": pid, "name": name, "mineru": engine.status()}, 409
    return {"error": "not-supported"}, 400


def take_pdf(jobs, data, headers):
    """A PDF from the landing, as (reply, status): always through MinerU's API, or asks for a key."""
    if data[:5] != b"%PDF-":
        return {"error": "not-pdf"}, 400
    name, lang = _named(headers)
    pid = pdfdoc.pid_of(data)
    f = store.DATA / "uploads" / f"{pid}.pdf"
    f.parent.mkdir(parents=True, exist_ok=True)
    if not f.exists():
        f.write_bytes(data)
    if (store.pdir(pid) / "meta.json").exists():   # this file, converted before
        f.unlink()
        return {"job": jobs.submit(pid, lang, False), "via": "pdf"}, 200
    if engine.available():
        return {"job": jobs.convert(pid, f, name, lang), "via": "pdf"}, 200
    f.unlink(missing_ok=True)
    return {"error": "needs-mineru-key", "upload": pid, "name": name, "mineru": engine.status()}, 409


PAGES = {}  # pid -> (signature of its layers and template, rendered page)
RELAYOUT = threading.Lock()


def assembled(pid, only=None):
    """The paper as the reader needs it (store.assemble), under the name the reader gave it in the library, if any."""
    doc = store.assemble(pid, only)
    name = library.name_of(pid)
    if name:
        doc["meta"]["name"] = name
    return doc


def reader_page(pid):
    layers = store.pdir(pid) / "layers"
    sig = tuple(sorted((f.name, f.stat().st_mtime) for f in layers.glob("*.json"))) if layers.exists() else ()
    sig += ((build.WEB / "template.html").stat().st_mtime, library.name_of(pid))  # a changed page template, or name, re-renders too
    hit = PAGES.get(pid)
    if not hit or hit[0] != sig:
        hit = (sig, build.page(assembled(pid), app=True))
        PAGES[pid] = hit
    return hit[1]


def listed():
    """The papers for the list: those on disk, with when each came in and was last opened."""
    return library.stamp(store.papers())


def trash_paper(pid):
    """A paper to papers/.trash with its place in the library, under the lock the name route takes: a name written
    while the folder is moving cannot outlive the delete (the library would list a document that is gone)."""
    with store.LOCK:
        kept = library.forget(pid)
        try:
            store.trash(pid, kept)
        except OSError:
            library.remember(pid, kept)   # (the folder could not move: the library stays as it was)
            raise


def name_paper(pid, value):
    """What the reader calls a document, under the lock a delete holds while its folder moves: no name is written for a
    document whose folder is being taken away (or was, a moment ago)."""
    with store.LOCK:
        if not store.valid_id(pid) or not (store.pdir(pid) / "meta.json").exists():
            raise KeyError(pid)
        return library.name(pid, value)


def busy_deleting(jobs):
    """The documents a delete has to leave where they are: those being generated (a card draft is not the document)."""
    return {j["pid"] for j in jobs.list() if j["status"] in ("queued", "running") and j.get("kind") != "card"}


def landing_page(jobs):
    s = models.load_settings()
    cat, _ = models.catalog(s)   # once: building it probes the computer's own model servers, and four builds made the page take seconds
    chosen = models.default_model(s, cat)
    ask = models.ask_choice(s, cat)[0]
    name = lambda mid: next((m["name"] for m in cat if m["id"] == mid), mid or "")
    boot = {"papers": listed(), "folders": library.folders(), "jobs": jobs.list(), "model": name(chosen) if chosen else "",
            "askName": name(ask) if ask and ask != chosen else "",
            "langs": [[code, v[1]] for code, v in langs.LANGS.items()]}
    t = (build.WEB / "app.html").read_text(encoding="utf-8")
    return t.replace("{{HEAD}}", build.fonts_head(build.APP_ASSETS)).replace("{{BOOT}}", json.dumps(boot, ensure_ascii=False).replace("</", "<\\/"))


LOCAL_NAMES = ("localhost", "127.0.0.1", "[::1]")


def addressed_here(host):
    """Whether a request's Host header names this computer (any port): what a page on another site cannot make its
    browser send, even once its domain points at 127.0.0.1."""
    m = re.fullmatch(r"(\[[0-9a-f:.]+\]|[^:\[\]]+)(?::\d{1,5})?", (host or "").strip().lower())
    return bool(m) and m.group(1) in LOCAL_NAMES


def same_origin(origin, port):
    """Whether a write's Origin is this server's own page: the local name it was opened under, and the server's port.
    A page on another localhost port is another site to a browser, and must not drive this server (a saved provider
    key must not be sendable by any local page). A request with no Origin is a command line or a native client, not a
    page; the routes that matter still refuse it a key from another address."""
    if not origin:
        return False
    u = urlparse(origin)
    if u.scheme != "http" or "@" in u.netloc or (u.hostname or "").casefold() not in ("localhost", "127.0.0.1", "::1"):
        return False   # (a browser's Origin has no userinfo; one that does is not a page of this server)
    try:
        origin_port = u.port or 80
    except ValueError:   # a malformed port
        return False
    return origin_port == port


OPENROUTER_BASE = next(p["base"] for p in providers.PRESETS if p["id"] == "openrouter")
KEY_ADDRESS = "a key the server keeps is only sent to the address it was kept for"


def _secret(key):
    """A key worth keeping from another address: a placeholder a local or keyless provider carries is not one."""
    return bool(key) and key not in ("none", "ollama", "magpie")


def _same_base(a, b):
    return (a or "").strip().rstrip("/").casefold() == (b or "").strip().rstrip("/").casefold()


def probe_key(settings, body, base):
    """The key a probe may use, and None: the request's own key; else a key the server keeps — a minted OpenRouter
    key for OpenRouter, a saved provider's key for that provider's saved address. A page must not be able to make the
    server hand a saved key to another host."""
    if body.get("minted"):
        key = openrouter.minted()
        if key:
            return (key, None) if _same_base(base, OPENROUTER_BASE) else (None, KEY_ADDRESS)
    typed = body.get("api_key")
    if isinstance(typed, str) and typed:
        return typed, None
    held = next((p for p in settings.get("providers") or [] if p.get("key") == body.get("key")), None) or {}
    key = held.get("api_key") or ""
    if _secret(key) and not _same_base(base, held.get("base")):
        return None, KEY_ADDRESS
    return key, None


def make_handler(jobs):
    class Handler(BaseHTTPRequestHandler):
        def send(self, code, body, ctype="application/json; charset=utf-8", cache="no-store"):
            data = body if isinstance(body, bytes) else body.encode("utf-8")
            try:   # (the reader stopped waiting — a question stopped, a page left or reloaded — at the body or, as
                # Windows' WinError 10053 does, mid-headers: every ConnectionError is the reader having gone, not an error)
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", cache)
                self.end_headers()
                self.wfile.write(data)
            except ConnectionError:
                pass

        def json(self, obj, code=200):
            self.send(code, json.dumps(obj, ensure_ascii=False))

        def send_error(self, code, message=None, explain=None):   # (the base's 400/501 replies: a client may be gone too)
            try:
                super().send_error(code, message, explain)
            except ConnectionError:
                pass

        def do_GET(self):
            if not addressed_here(self.headers.get("Host")):   # (DNS rebinding: the module's docstring)
                return self.json({"error": "misdirected"}, 421)
            u = urlparse(self.path)
            try:
                if u.path == "/":
                    return self.send(200, landing_page(jobs), "text/html; charset=utf-8")
                if u.path == "/api/openrouter/minted":   # the app, waiting while the system browser authorises
                    return self.json({"minted": bool(openrouter.minted())})
                if u.path == "/oauth/openrouter":   # OpenRouter sends the reader back here with a code
                    code = (parse_qs(u.query).get("code") or [""])[0]
                    desktop = openrouter.for_desktop()
                    key, err, back = openrouter.openrouter_finish(code)
                    back = back if back.startswith("/") else "/"
                    to = f"{back}#or-minted" if key else f"{back}#or-failed={quote(err or '')}"
                    if desktop:   # this tab is the system browser's: the app, waiting for the key, takes it from here
                        page = (f'<!doctype html><meta charset="utf-8"><title>TextFold</title><body style="font-family:system-ui;'
                                f'display:grid;place-items:center;height:100vh;margin:0;background:#FAF9F7;color:#1f1d1a">'
                                f'<div style="text-align:center;line-height:1.7"><h2>{"✓" if key else "✕"} OpenRouter</h2>'
                                f'<p style="color:#6b6558">{"回到 TextFold 即可，本页可以关闭。<br>Return to TextFold; this tab can be closed." if key else (err or "")}</p></div>')
                        return self.send(200, page, "text/html; charset=utf-8")
                    page = (f'<!doctype html><meta charset="utf-8"><title>TextFold</title><body style="font-family:system-ui;'
                            f'display:grid;place-items:center;height:100vh;margin:0;background:#FAF9F7;color:#1f1d1a">'
                            f'<div style="text-align:center"><h2>{"✓ OpenRouter" if key else "OpenRouter ✕"}</h2></div>'
                            f'<script>location.replace({json.dumps(to)})</script>')
                    return self.send(200, page, "text/html; charset=utf-8")
                m = re.fullmatch(r"/p/([\w.-]+)/img/([\w.-]+)", u.path)   # a paper's picture (a drawing stays inside its page)
                if m and store.valid_id(m.group(1)):
                    f = store.pdir(m.group(1)) / "img" / m.group(2)
                    kind = IMAGE_TYPES.get(f.suffix.lower())
                    if kind and f.is_file():
                        return self.send(200, f.read_bytes(), kind, cache="max-age=86400")
                    return self.json({"error": "no such picture"}, 404)
                m = re.fullmatch(r"/p/([\w.-]+)", u.path)
                if m and store.valid_id(m.group(1)):
                    if not (store.pdir(m.group(1)) / "source.html").exists():
                        try:
                            self.send_response(302)
                            self.send_header("Location", "/")
                            self.end_headers()
                        except ConnectionError:   # (the reader left while the redirect was being written)
                            pass
                        return
                    library.opened(m.group(1))
                    return self.send(200, reader_page(m.group(1)), "text/html; charset=utf-8")
                if u.path.startswith("/static/") and u.path[8:] in STATIC:
                    return self.send(200, (build.WEB / u.path[8:]).read_bytes(), STATIC[u.path[8:]] + "; charset=utf-8")
                if u.path.startswith("/static/vendor/"):
                    f = vendor_file(unquote(u.path[len("/static/vendor/"):]))
                    if f:
                        return self.send(200, f.read_bytes(), VENDOR_TYPES[f.suffix], cache="max-age=86400")
                if u.path == "/api/papers":
                    return self.json(listed())
                if u.path == "/api/folders":
                    return self.json(library.folders())
                if u.path == "/api/jobs":
                    return self.json(jobs.list())
                if u.path in ("/api/models", "/api/settings"):
                    return self.json(models_payload())
                m = re.fullmatch(r"/api/pdfmap/([\w.-]+)", u.path)   # a converted PDF's paragraphs on its pages
                if m and m.group(1).startswith("pdf-") and store.valid_id(m.group(1)) and (store.pdir(m.group(1)) / "meta.json").exists():
                    with RELAYOUT:   # (converted before the layout was kept: found again once, in seconds)
                        try:
                            pdfdoc.relayout(m.group(1))
                        except Exception:
                            pass
                    return self.json(pdfdoc.place(m.group(1)))
                if u.path in ("/api/mineru", "/api/engine"):
                    return self.json(engine.status())
                if u.path.startswith("/api/zotero"):
                    q = {k: v[0] for k, v in parse_qs(u.query).items()}
                    try:
                        if u.path == "/api/zotero":
                            return self.json(zotero.status())
                        if u.path == "/api/zotero/collections":
                            return self.json(zotero.collections(q.get("lib", "")))
                        if u.path == "/api/zotero/items":
                            return self.json(zotero.items(q.get("lib", ""), q.get("collection", ""), q.get("q", "")[:200]))
                    except zotero.Off as e:   # Zotero closed, or its local API off: the app says which
                        return self.json({"error": str(e)}, 503)
                    except ValueError as e:
                        return self.json({"error": str(e)}, 400)
                m = re.fullmatch(r"/api/notes/([\w.-]+)", u.path)
                if m and store.valid_id(m.group(1)) and (store.pdir(m.group(1)) / "meta.json").exists():
                    return self.json(notes.read(m.group(1)))
                m = re.fullmatch(r"/api/card/([\w.-]+)", u.path)
                if m and store.valid_id(m.group(1)) and (store.pdir(m.group(1)) / "meta.json").exists():
                    try:
                        return self.json(cards.payload(m.group(1)))
                    except ValueError as e:   # (a stored page that no longer parses)
                        return self.json({"error": str(e)}, 400)
                m = re.fullmatch(r"/api/pdf/([\w.-]+)", u.path)
                if m and store.valid_id(m.group(1)) and (store.pdir(m.group(1)) / "meta.json").exists():
                    f = pdf.path(m.group(1)) if pdf.has_source(m.group(1)) else None
                    if not f:   # with where the reader may open it, to drop it on the pane
                        return self.json({"error": "no-pdf", "open": pdf.where(m.group(1)) if pdf.has_source(m.group(1)) else None}, 404)
                    return self.send(200, f.read_bytes(), "application/pdf", cache="max-age=86400")
                if u.path == "/favicon.ico":
                    return self.send(204, b"", "image/x-icon")
                self.json({"error": "not found"}, 404)
            except Exception as e:
                self.json({"error": str(e)}, 500)

        def do_POST(self):
            if not addressed_here(self.headers.get("Host")):
                return self.json({"error": "misdirected"}, 421)
            u = urlparse(self.path)
            origin = self.headers.get("Origin")
            if origin and not same_origin(origin, self.server.server_address[1]):
                return self.json({"error": "forbidden"}, 403)  # another site — or another local port — may not drive it
            try:
                size = int(self.headers.get("Content-Length") or 0)
                m = re.fullmatch(r"/api/pdf/([\w.-]+)", u.path)
                if m:   # a paper's PDF, dropped on the reader's pane: the file's bytes, not JSON
                    if not (store.valid_id(m.group(1)) and (store.pdir(m.group(1)) / "meta.json").exists()):
                        return self.json({"error": "no such paper"}, 404)
                    if size > pdf.LIMIT:
                        return self.json({"error": "too-large"}, 413)
                    return self.json({"ok": True}) if pdf.keep(m.group(1), self.rfile.read(size)) else self.json({"error": "not-pdf"}, 400)
                if u.path in ("/api/files", "/api/pdfs"):   # a file dropped on the landing: its bytes
                    if size > pdf.LIMIT:
                        return self.json({"error": "too-large"}, 413)
                    return self.json(*take_file(jobs, self.rfile.read(size), self.headers))
                if size > 12_000_000:   # a Markdown file is far smaller; this is a request gone wrong
                    return self.json({"error": "too-large"}, 413)
                body = json.loads(self.rfile.read(size) or b"{}")
                s = models.load_settings()
                if u.path == "/api/generate":
                    lang = body.get("lang") or "en"
                    if lang not in langs.LANGS:
                        return self.json({"error": f"unknown language {lang}"}, 400)
                    try:
                        job = jobs.submit(body.get("paper", ""), lang, body.get("force"))
                    except ValueError as e:   # not a paper's reference, or (a DOI) none Europe PMC can read in full
                        return self.json({"error": str(e) if str(e) in ("no-fulltext", "no-article") else "bad-ref"}, 400)
                    return self.json(job)
                if u.path == "/api/zotero/library":
                    try:
                        zotero.choose(str(body.get("library") or ""))
                    except ValueError as e:
                        return self.json({"error": str(e)}, 400)
                    return self.json(zotero.status())
                if u.path == "/api/zotero/read":   # an item of the Zotero library: its file as a dropped one, or its paper online
                    lib, _, key = str(body.get("item") or "").rpartition("/")
                    lang = body.get("lang") if body.get("lang") in langs.LANGS else "en"
                    try:
                        got = zotero.read(lib, key)
                        if "ref" in got:   # generated as a pasted link is (from the page, which asks for a model first)
                            pid = store.resolve(got["ref"])
                            zotero.link(lib, key, pid, got["title"])
                            return self.json({"ref": pid, "title": got["title"]})
                    except zotero.Off as e:
                        return self.json({"error": str(e)}, 503)
                    except ValueError as e:   # no file and no paper online; not a library or item
                        return self.json({"error": str(e) if str(e) in ("no-file", "no-fulltext", "bad-library", "bad-item") else "bad-ref"}, 400)
                    named = {"X-Name": quote(got["name"]), "X-Lang": lang}
                    reply, code = take_file(jobs, got["data"], named)
                    pid = reply.get("paper") or reply.get("upload") or (reply.get("job") or {}).get("pid")
                    if code == 200 and pid:
                        zotero.link(lib, key, pid, got["title"], got["record"])
                        zotero.apply(pid)   # (read at once, or read before: its record now; else once converted)
                    return self.json({**reply, "name": got["name"]}, code)
                if u.path == "/api/convert":   # a stored PDF (or picture) converted again, at another tier (its levels follow)
                    pid, tier = str(body.get("paper") or ""), str(body.get("tier") or "accurate")
                    src = pdfdoc.source_of(pid) if pid.startswith(("pdf-", "doc-")) and store.valid_id(pid) else None
                    if not src or tier not in engine.TIERS or engine.tier_for(src, tier) != tier:
                        return self.json({"error": "no such PDF"}, 404)
                    if not engine.readable(engine.kind_of(src) or "pdf"):
                        return self.json({"error": "needs-mineru-key"}, 409)
                    name = json.loads(store.read_text(store.pdir(pid) / "meta.json")).get("source", {}).get("name") or "document.pdf"
                    lang = body.get("lang") if body.get("lang") in langs.LANGS else "en"
                    return self.json(jobs.convert(pid, src, name, lang, tier, replace=True))
                if u.path == "/api/jobs/stop":
                    job = jobs.stop(body.get("id", ""))
                    return self.json(job) if job else self.json({"error": "no such job"}, 404)
                if u.path == "/api/import":
                    text, name = str(body.get("text") or ""), str(body.get("name") or "document.md")[:200]
                    if not text.strip():
                        return self.json({"error": "empty"}, 400)
                    try:
                        pid = local.import_text(text, name)
                    except ValueError:
                        return self.json({"error": "not-markdown"}, 400)
                    return self.json({"paper": pid, "title": json.loads(store.read_text(store.pdir(pid) / "meta.json"))["title"]})
                if u.path == "/api/export":   # the paper as one file, saved by the reader for themself
                    pid, lang = str(body.get("paper") or ""), str(body.get("lang") or "en")
                    if not store.valid_id(pid) or not (store.pdir(pid) / "meta.json").exists():
                        return self.json({"error": "no such paper"}, 404)
                    kinds = {k for k in body.get("kinds") or [] if k in ("hl", "note", "ask")}
                    doc = assembled(pid, only=[lang] if body.get("langs") == "current" else None)
                    chosen = [n for n in notes.read(pid)["notes"] if notes.kind(n) in kinds]
                    saved = {"notes": chosen, "saved": uuid.uuid4().hex[:12], "lang": lang}
                    if body.get("pdf") and pdf.has_source(pid):   # the original beside it: the file, and PDF.js to show it
                        f = pdf.path(pid)
                        if f:
                            saved["pdf"] = base64.b64encode(f.read_bytes()).decode()
                            saved["pdfjs"] = {"lib": (build.VENDOR / "pdfjs" / "pdf.min.mjs").read_text(encoding="utf-8"),
                                              "worker": (build.VENDOR / "pdfjs" / "pdf.worker.min.mjs").read_text(encoding="utf-8")}
                            if pid.startswith("pdf-"):   # a converted PDF: its paragraphs' places on the pages
                                with RELAYOUT:
                                    try:
                                        pdfdoc.relayout(pid)
                                    except Exception:
                                        pass
                                saved["pdfmap"] = pdfdoc.place(pid)
                    html = build.page(doc, app=False, saved=saved)
                    return self.send(200, html, "text/html; charset=utf-8")
                m = re.fullmatch(r"/api/notes/([\w.-]+)", u.path)
                if m and store.valid_id(m.group(1)) and (store.pdir(m.group(1)) / "meta.json").exists():
                    try:
                        if body.get("op") == "delete":
                            return self.json(notes.delete(m.group(1), str(body.get("id", ""))))
                        return self.json(notes.put(m.group(1), body.get("note")))
                    except ValueError as e:
                        return self.json({"error": str(e)}, 400)
                m = re.fullmatch(r"/api/card/([\w.-]+)", u.path)
                if m and store.valid_id(m.group(1)) and (store.pdir(m.group(1)) / "meta.json").exists():
                    pid = m.group(1)
                    op = body.get("op")
                    if op == "generate":
                        lang = body.get("lang") if body.get("lang") in langs.LANGS else "en"
                        return self.json(jobs.card(pid, lang))
                    if op == "export":
                        try:
                            base = str(body.get("base") or "")[:200]
                            md = cards.markdown(pid, base)
                        except ValueError as e:
                            return self.json({"error": str(e)}, 400)
                        return self.json({"markdown": md, "name": cards.export_name(pid)})
                    try:
                        return self.json(cards.apply_op(pid, body))
                    except ValueError as e:
                        return self.json({"error": str(e)}, 400)
                    except Exception as e:
                        return self.json({"error": str(e)[:600]}, 500)
                if u.path == "/api/openrouter/start":
                    callback = f"http://{self.headers.get('Host')}/oauth/openrouter"   # (the guard above: a local name)
                    return self.json({"url": openrouter.openrouter_start(callback, str(body.get("back") or "/"), bool(body.get("desktop")))})
                if u.path == "/api/papers/delete":
                    many = isinstance(body.get("papers"), list)
                    pids = [str(p) for p in body["papers"]] if many else [str(body.get("paper", ""))]
                    there = [p for p in dict.fromkeys(pids) if store.valid_id(p) and (store.pdir(p) / "meta.json").exists()]
                    live = busy_deleting(jobs)
                    if not many and not there:
                        return self.json({"error": "no such paper"}, 404)
                    if not many and there[0] in live:
                        return self.json({"error": "busy"}, 409)
                    deleted, failed = [], []
                    for pid in [p for p in there if p not in live]:   # (its place in the library goes with it, for an Undo)
                        try:
                            trash_paper(pid)
                        except OSError:
                            if not many:
                                raise
                            failed.append(pid)
                            continue
                        PAGES.pop(pid, None)
                        deleted.append(pid)
                    if not many:
                        return self.json(listed())
                    return self.json({"papers": listed(), "deleted": deleted, "busy": [p for p in there if p in live], "failed": failed})
                if u.path == "/api/papers/restore":
                    pids = body.get("papers") if isinstance(body.get("papers"), list) else []
                    restored = []
                    for pid in dict.fromkeys(str(p) for p in pids):
                        kept = store.untrash(pid, lambda k, pid=pid: library.remember(pid, k))   # (the place while the lock is held)
                        if kept is not None:
                            restored.append(pid)
                    return self.json({"papers": listed(), "folders": library.folders(), "restored": restored})
                if u.path == "/api/papers/name":
                    try:
                        name_paper(str(body.get("paper", "")), body.get("name"))
                    except KeyError:
                        return self.json({"error": "no such paper"}, 404)
                    return self.json(listed())
                if u.path == "/api/folders":
                    try:
                        return self.json(library.change(body))
                    except ValueError as e:
                        return self.json({"error": str(e)}, 400)
                if u.path == "/api/ask/stop":
                    notes.stop(str(body.get("req") or "")[:40])
                    return self.json({"ok": True})
                if u.path == "/api/ask":
                    pid = str(body.get("paper", ""))
                    if not store.valid_id(pid) or not (store.pdir(pid) / "meta.json").exists():
                        return self.json({"error": "no such paper"}, 404)
                    try:
                        return self.json(notes.ask(pid, str(body.get("id", "")), str(body.get("question", "")).strip()[:2000],
                                                   models.ask_spec(), ui=str(body.get("ui") or ""),
                                                   req=str(body.get("req") or "")[:40] or None))
                    except notes.Stopped:
                        return self.json({"error": "stopped"}, 409)
                    except ValueError as e:
                        return self.json({"error": str(e)}, 400)
                    except Exception as e:  # the model failed: the note keeps its question, the reader can ask again
                        return self.json({"error": str(e)[:600]}, 502)
                if u.path == "/api/models/select" and body.get("task") == "ask":
                    models.update_settings(lambda current: current.update(
                        ask_model=body.get("model") or None, ask_effort=body.get("effort") or None))
                    return self.json(models_payload())
                if u.path == "/api/models/select":
                    def select_model(current):
                        current["model"] = body.get("model") or None
                        if "effort" in body and current["model"]:
                            if body["effort"]:
                                current.setdefault("efforts", {})[current["model"]] = body["effort"]
                            else:
                                current.setdefault("efforts", {}).pop(current["model"], None)
                    models.update_settings(select_model)
                    return self.json(models_payload())
                if u.path == "/api/providers/probe":
                    preset = next((p for p in providers.PRESETS + [models.ANTHROPIC_PRESET] if p["id"] == body.get("preset")), None)
                    base = str(body.get("base") or "").strip()
                    if preset and preset.get("fixed"):  # MiniMax and Anthropic have no /models a key can list
                        found = [{"id": i} for i in preset["fixed"]]
                    else:
                        key, refused = probe_key(s, body, base)
                        if refused:
                            return self.json({"error": refused}, 400)
                        if (preset or {}).get("id") == "magpie":
                            key = "magpie"
                        try:
                            found = providers.probe(base, key)
                        except Exception as e:
                            return self.json({"error": str(e)}, 400)
                    for rid in (preset or {}).get("recommend", []):  # recommended ids the probe left out
                        if rid not in {m["id"] for m in found}:
                            found.append({"id": rid, "recommended": True})
                    current = next((p.get("models") for p in s["providers"] if p["key"] == body.get("key")), None)
                    picked = providers.preselect(found, preset, [m["id"] for m in current] if current else None,
                                                 free_first=(preset or {}).get("id") == "openrouter")
                    return self.json({"models": found, "picked": picked, "recommend": (preset or {}).get("recommend", [])})
                if u.path == "/api/providers/save":
                    preset = body.get("preset") or "custom"
                    known = providers.PRESETS + [models.ANTHROPIC_PRESET]
                    name = (body.get("name") or "").strip() or next((p["name"] for p in known if p["id"] == preset), "") or "Custom"
                    key = "magpie" if preset == "magpie" else body.get("key") or re.sub(r"[^a-z0-9]+", "-", f"{preset}-{name}".lower()).strip("-")
                    base = (body.get("base") or "").strip().rstrip("/")
                    typed = body.get("api_key") if isinstance(body.get("api_key"), str) else ""
                    minted = bool(body.get("minted")) and bool(openrouter.minted())
                    if minted and not _same_base(base, OPENROUTER_BASE):
                        return self.json({"error": KEY_ADDRESS}, 400)
                    def save_provider(current):
                        old = next((p for p in current["providers"] if p["key"] == key), {})
                        if not minted and not typed and _secret(old.get("api_key")) and not _same_base(base, old.get("base")):
                            raise ValueError(KEY_ADDRESS)   # (a saved key does not move to another host)
                        row = {"key": key, "preset": preset, "name": name, "base": base,
                               "api_key": (openrouter.take_minted() if minted else None) or typed or
                                          old.get("api_key") or ("magpie" if preset == "magpie" else ""),
                               "models": [{"id": i} for i in (body.get("models") or [])][:providers.MAX_MODELS]}
                        if preset == "anthropic":
                            row["protocol"] = "anthropic"
                        current["providers"] = ([p for p in current["providers"] if p["key"] != key] + [row])[-providers.MAX_PROVIDERS:]
                    try:
                        models.update_settings(save_provider)
                    except ValueError as e:
                        return self.json({"error": str(e)}, 400)
                    return self.json(models_payload())
                if u.path == "/api/providers/remove":
                    models.update_settings(lambda current: current.update(
                        providers=[p for p in current["providers"] if p["key"] != body.get("key")]))
                    return self.json(models_payload())
                if u.path == "/api/settings":
                    key = body.get("mineru_api_key")
                    key = key.strip() if isinstance(key, str) else ""
                    if key and not engine.key_ok(key):
                        return self.json({"error": "bad-mineru-key"}, 400)
                    if "mineru_api_url" in body and not isinstance(body.get("mineru_api_url"), str):
                        return self.json({"error": "bad-mineru-url"}, 400)   # (a non-text address is not a reset)
                    url = body.get("mineru_api_url")
                    url = url.strip() if isinstance(url, str) else ""
                    if url and not engine.base_ok(url):
                        return self.json({"error": "bad-mineru-url"}, 400)
                    def update_general(current):
                        if "use_thoughtdag_env" in body:
                            current["use_thoughtdag_env"] = bool(body["use_thoughtdag_env"])
                        if body.get("pdf_tier") in engine.TIERS:
                            current["pdf_tier"] = body["pdf_tier"]
                        if "mineru_api_key" in body:
                            current["mineru_api_key"] = key
                        if "mineru_api_url" in body:   # (empty: the official base; base_ok normalized it otherwise)
                            current["mineru_api_url"] = engine.base_ok(url) or models.MINERU_API
                    models.update_settings(update_general)
                    return self.json(models_payload())
                if u.path == "/api/settings/test":
                    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
                    try:
                        spec = models.ask_spec() if body.get("task") == "ask" else models.resolve(body.get("model"))   # (questions: their model, reasoning as set)
                        t0 = time.time()
                        with tempfile.TemporaryDirectory() as tmp:
                            rec, _ = llm.call('Return JSON {"ok": true}.', schema, spec, Path(tmp), force=True, timeout=180)
                        return self.json({"ok": bool(rec["out"].get("ok")), "model": spec["id"], "seconds": round(time.time() - t0, 1)})
                    except Exception as e:
                        return self.json({"ok": False, "error": str(e)[:600]})
                self.json({"error": "not found"}, 404)
            except Exception as e:
                self.json({"error": str(e)}, 500)

        def log_message(self, *args):
            pass

    return Handler


def _quiet_children():
    """Windows: console children (the curl that downloads a MinerU result) start without opening a window."""
    init = subprocess.Popen.__init__

    def quiet(self, *a, **kw):
        kw["creationflags"] = kw.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
        init(self, *a, **kw)
    subprocess.Popen.__init__ = quiet


def serve(port=3017):
    _quiet_children()
    jobs = Jobs()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(jobs))
    print(f"TextFold on http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
