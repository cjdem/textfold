"""TextFold.

  python -m textfold serve [--port 3017]                 the local app (landing, sidebar, reader)
  python -m textfold <arxiv id or url> [--lang zh] ...   generate from the command line, then export
  python -m textfold notes.md [--lang zh] ...           the same for a Markdown file
  python -m textfold export <arxiv id>                   one self-contained HTML file in out/<id>/
  python -m textfold get <link or file> [--level topic] [--section 3] [--json]   a document at one level
  python -m textfold mineru status                        MinerU's Cloud API and its key
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

from . import build, local, pipeline


def _say(*a):
    print(*a, file=sys.stderr, flush=True)


def get(a):
    """A document at one level, on stdout: written first when it has no levels yet (a model is called), unless
    --no-generate. Common Office/E-book/CSV/HTML files are read here; every PDF and every picture goes through MinerU's
    Cloud API. New RTF, OpenDocument and old Office files are refused."""
    from . import engine, fold, langs, models, office, pdfdoc, store
    if a.lang not in langs.LANGS:
        _say(f"unknown language {a.lang}: " + ", ".join(langs.LANGS))
        return 2
    f = Path(a.ref).expanduser()
    ext = engine.kind_of(f.name) if f.is_file() else None
    if ext:
        data = f.read_bytes()
        if data[:5] == b"%PDF-" and ext != "pdf":   # a PDF under another name: read as the PDF it is
            ext = "pdf"
        pid = pdfdoc.pid_of(data, ext)
        if ext in engine.LEGACY and not (store.pdir(pid) / "meta.json").exists():
            _say("TextFold no longer opens new RTF, OpenDocument or old Word, PowerPoint or Excel files: "
                 "save it as DOCX, PPTX, XLSX or PDF first.")
            return 2
        if not (store.pdir(pid) / "meta.json").exists():
            read_here = False
            if ext != "pdf" and office.reads(ext):
                try:
                    office.save(pid, f, f.name)
                    read_here = True
                except ValueError:
                    pass
            if not read_here and not engine.readable(ext):
                what = "PDF" if ext == "pdf" else "picture" if ext in engine.PICTURES else f"{engine.FILES[ext]} file"
                how = ("set mineru_api_key in ~/.textfold/settings.json"
                       if ext in engine.API_FILES else "MinerU's API does not read this kind")
                _say(f"This {what} cannot be read here: {how}")
                return 2
            if not read_here:
                tier = engine.tier_for(f"x.{ext}", models.load_settings().get("pdf_tier") or "fast")
                out = store.DATA / "uploads" / f"{pid}-{tier}"
                src = f
                if f.suffix.lower() != f".{ext}":   # (an extension the engine knows by another: .tif)
                    src = store.DATA / "uploads" / f"{pid}.{ext}"
                    src.parent.mkdir(parents=True, exist_ok=True)
                    src.write_bytes(data)
                engine.convert(src, out, tier, progress=lambda s, d, t: _say(f"  converting {d}/{t}") if t else None, log=lambda line: None)
                pdfdoc.store_pdf(pid, out, pdfdoc.read_output(out), f.name, tier)
                (store.pdir(pid) / pdfdoc.kept_name(pid, src)).write_bytes(data)
                shutil.rmtree(out, ignore_errors=True)   # MinerU's output (and its copy of the file), stored
                if src != f:
                    src.unlink(missing_ok=True)
    elif f.is_file():
        pid = local.import_file(f)
    else:
        pid = store.resolve(a.ref)
    try:
        spec = None if a.no_generate else models.resolve(None)
    except RuntimeError:
        spec = None
    try:
        pipeline.generate(pid, a.lang, spec, progress=lambda s, d, t: _say(f"  {s} {d}/{t}") if t and s != "done" else None, log=lambda line: None)
    except RuntimeError as e:   # fetched and parsed; its levels need a model: the local ones, said so
        if "No model" not in str(e):
            raise
        _say("No API model: the written levels are the author's first sentences (connect one in Settings).")
    except ValueError as e:   # (a delete in the other process took the folder while this command was reading it)
        if str(e) != "no-document":
            raise
        _say("The document is no longer there: it was deleted while this command was reading it.")
        return 1
    d = fold.document(pid, a.lang)
    if a.json:
        import json
        print(json.dumps(d, ensure_ascii=False, indent=1))
    else:
        print(fold.markdown(d, a.level, a.section), end="")
    return 0


def mineru_cmd(args):
    from . import engine
    what = args[0] if args else "status"
    if what != "status":
        _say("python -m textfold mineru status")
        return 2
    st = engine.status()
    print("MinerU API key: " + ("set" if st["api"] else "not set")
          + " (mineru_api_key in ~/.textfold/settings.json)")
    print("MinerU API address: " + st["base"]
          + ("" if st["baseOk"] else "  (not valid; fix mineru_api_url in ~/.textfold/settings.json)"))
    return 0


def _utf8_streams():
    """The document's text (titles, quotes) reaches stdout/stderr as UTF-8, whatever the locale's codepage is: on
    Windows a redirected or piped stream is otherwise cp936 (or another legacy codepage) and a character outside it
    raises instead of printing."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def main():
    _utf8_streams()
    if sys.argv[1:2] == ["--version"]:
        from . import __version__
        return print(f"TextFold {__version__}")
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        ap = argparse.ArgumentParser(prog="python -m textfold serve")
        ap.add_argument("--port", type=int, default=3017)
        a = ap.parse_args(sys.argv[2:])
        from .server import serve
        return serve(a.port)
    if len(sys.argv) > 1 and sys.argv[1] == "get":
        from .fold import LEVELS
        ap = argparse.ArgumentParser(prog="python -m textfold get", description="A document at one level: the map first, then the parts that matter, deeper.")
        ap.add_argument("ref", help="a link (any web page, arXiv, PubMed Central, bioRxiv, Wikipedia, GitHub), an arXiv id, a DOI, or a file (.pdf, .docx, .pptx, .xlsx, .epub, .html, a picture, .md, .txt)")
        ap.add_argument("--level", default="topic", choices=LEVELS, help="topic (a map of the sections) ... full (every word); default topic")
        ap.add_argument("--section", help="one section: its number (3.2), its id (S3), or its place in the list (1 is the first)")
        ap.add_argument("--lang", default="en", help="the language to read it in (en, zh); default en")
        ap.add_argument("--json", action="store_true", help="the whole document in the TextFold format (docs/format.md)")
        ap.add_argument("--no-generate", action="store_true", help="call no model: the levels already written, or the local ones")
        return sys.exit(get(ap.parse_args(sys.argv[2:])))
    if len(sys.argv) > 1 and sys.argv[1] in ("mineru", "engine"):
        return sys.exit(mineru_cmd(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "export":
        print(build.export(sys.argv[2]))
        return
    ap = argparse.ArgumentParser(prog="textfold", description="Generate a zoomable reader for an arXiv paper or a Markdown file.")
    ap.add_argument("paper", help="arXiv id or URL, e.g. 2512.23916, or a Markdown file")
    ap.add_argument("--lang", action="append", default=[], help="also generate this language (zh); repeatable")
    ap.add_argument("--model", help="API model id (defaults to the model selected in TextFold settings)")
    ap.add_argument("--jobs", type=int, default=4, help="parallel model calls")
    ap.add_argument("--force", action="store_true", help="regenerate (ignore what is stored and cached)")
    a = ap.parse_args()
    from . import langs, models
    unknown = [l for l in a.lang if l not in langs.LANGS]
    if unknown:
        ap.error(f"unknown language {unknown[0]}: " + ", ".join(langs.LANGS))
    t0 = time.time()
    spec = models.resolve(a.model)   # the chosen API model, or the default provider's
    ref = local.import_file(a.paper) if Path(a.paper).suffix.lower() in local.KINDS and Path(a.paper).is_file() else a.paper
    pid = None
    for lang in ["en"] + a.lang:
        try:
            pid = pipeline.generate(ref, lang, spec, force=a.force, jobs=a.jobs, log=print,
                                    progress=lambda s, d, t: print(f"  {s} {d}/{t}", end="\r"))
        except ValueError as e:   # (a delete in the other process took the folder while this command was reading it)
            if str(e) != "no-document":
                raise
            _say("The document is no longer there: it was deleted while this command was reading it.")
            sys.exit(1)
    print(f"\n  → {build.export(pid)}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
