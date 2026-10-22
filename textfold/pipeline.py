"""Generate a paper in a language: fetch (an arXiv paper), parse, the English ladder (once), the translation.

Every step reports through `progress(stage, done, total)`; the server turns that into a progress bar. A set `stop`
(a threading.Event) ends it with llm.Stopped at the next step: what the model has already written stays in the cache,
so the same generation started again goes on from there (a gap retry or fill asks the model itself, so its prompt is
asked anew).
"""
import urllib.error

from . import biorxiv, epmc, github, ladder, langs, llm, models, store, translate, webpage, wiki
from .fetch import fetch


def task(cfg, name):
    """The model spec a task runs with: its reasoning level from the settings (models.for_task)."""
    return models.for_task(llm.spec_of(cfg), name)


def _wants_zh(en, tr):
    """Whether the default Simplified Chinese version still has to be made: the English base is a layer with a version,
    and the Chinese one is missing, is no layer at all, or stands on an older base."""
    return isinstance(en, dict) and bool(en.get("version")) and (not isinstance(tr, dict) or tr.get("base") != en.get("version"))


def generate(ref, lang, cfg, force=False, jobs=4, progress=lambda *a: None, log=lambda *a: None, stop=None, also_zh=False):
    if lang not in langs.LANGS:
        raise RuntimeError(f"unknown language {lang}: " + ", ".join(langs.LANGS))

    def check():
        if stop is not None and stop.is_set():
            raise llm.Stopped()

    pid = store.resolve(ref)
    progress("fetch", 0, 1)
    if store.is_imported(pid):   # stored when it was opened (local.py), or fetched once from Europe PMC (epmc.py)
        if pid.startswith(("pmc", "ppr")):
            epmc.fetch(pid)
        elif pid.startswith(("biorxiv-", "medrxiv-")):
            biorxiv.fetch(pid, progress)
        elif pid.startswith("wiki-"):
            wiki.fetch(pid)
        elif pid.startswith("gh-"):
            github.fetch(pid)
        elif pid.startswith("web-"):
            webpage.fetch(pid)
        d = store.pdir(pid)
    else:
        try:
            d = fetch(pid, store.DATA)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise RuntimeError("no-html")  # the app shows its own sentence for this
            raise
    check()
    progress("parse", 0, 1)
    doc = store.parsed(pid)
    cache = d / "llm-cache"
    en = store.read(pid, "en")
    if cfg is None and (en is None or force or (lang != "en" and store.read(pid, f"tr-{lang}") is None)):
        # fetched and parsed, so it can be read as written; its levels need a model
        raise RuntimeError("No model is available: add an API provider in Settings")
    model = llm.label(cfg) if cfg else ""
    if en is None or (force and lang == "en"):
        check()
        ladder.build(doc, task(cfg, "ladder"), cache, jobs=jobs, log=log, progress=lambda a, b: progress("ladder", a, b), force=force, stop=stop)
        check()
        store.save_en(doc, model)
        en = store.read(pid, "en")
    else:
        store.apply_en(doc, en)
    if lang != "en":
        tr = store.read(pid, f"tr-{lang}")
        if force or tr is None or tr.get("base") != en["version"]:
            check()
            translate.build(doc, lang, task(cfg, "translate"), cache, jobs=jobs, log=log, progress=lambda a, b: progress("translate", a, b), force=force, stop=stop)
            n = len(translate.gaps(doc, lang))
            if n:   # (a part that still failed: the layer is kept, and the app asks for its paragraphs as it opens)
                log(f"the {langs.name(lang)} version has {n} paragraphs without a translation")
            store.save_tr(doc, lang, en["version"], model)
        elif cfg is not None:
            store.apply_tr(doc, lang, tr)
            if translate.gaps(doc, lang):   # paragraphs it was stored without (a call that failed): asked for now
                check()
                translate.fill(doc, lang, task(cfg, "translate"), cache, jobs=jobs, log=log,
                               progress=lambda a, b: progress("translate", a, b), stop=stop)
                was = tr.get("model") or model
                store.save_tr(doc, lang, en["version"], was if was == model else f"{was} + {model}")
    # An English document is read in Simplified Chinese by default: the version is made at the end of this generation,
    # whichever language was asked for (the app passes also_zh; the command line does not).
    if also_zh and cfg is not None and lang != "zh":
        try:
            tr = store.read(pid, "tr-zh")
        except (OSError, ValueError):
            tr = None   # (an unreadable layer is no layer: it is made again, and the save replaces it)
        if _wants_zh(en, tr):
            check()
            try:
                translate.build(doc, "zh", task(cfg, "translate"), cache, jobs=jobs, log=log,
                                progress=lambda a, b: progress("zh", a, b), stop=stop)
                n = len(translate.gaps(doc, "zh"))
                if n:   # (a part that still failed: the layer is kept, and the app asks for its paragraphs as it opens)
                    log(f"the Simplified Chinese version has {n} paragraphs without a translation")
                store.save_tr(doc, "zh", en["version"], model)
            except llm.Stopped:
                raise
            except Exception as e:   # (the language asked for is made: the default one does not fail the whole job)
                log(f"the Simplified Chinese version could not be made ({str(e)[:200]})")
        elif tr is not None:   # the default version stands on this base but has gaps: filled now, the rest kept
            check()
            try:
                store.apply_tr(doc, "zh", tr)
                if translate.gaps(doc, "zh"):
                    translate.fill(doc, "zh", task(cfg, "translate"), cache, jobs=jobs, log=log,
                                   progress=lambda a, b: progress("zh", a, b), stop=stop)
                    was = tr.get("model") or model
                    store.save_tr(doc, "zh", en["version"], was if was == model else f"{was} + {model}")
            except llm.Stopped:
                raise
            except Exception as e:
                log(f"the Simplified Chinese version could not be completed ({str(e)[:200]})")
    progress("done", 1, 1)
    return pid
