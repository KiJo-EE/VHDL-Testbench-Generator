"""Ordner mit allem: wavetb.json, <test>.wave.json und die generierten Testbenches"""
import glob
import json
import os
from pathlib import Path

from . import deps
from .core import SpecError
from .vhdl import parse_entities

DEFAULT = {"top": "", "entity": "", "search": [], "sources": [], "period_ns": 10, "clock": "",
           "mode": "plain", "surfer": ""}


CONFIG_NAME = "wavetb.json"
TEST_SUFFIX = ".wave.json"
LEGACY_CONFIG = "project.json"      # frueheres Layout: project.json + tests/*.json


def exists(pdir):
    pdir = Path(pdir)
    return (pdir / CONFIG_NAME).is_file() or (pdir / LEGACY_CONFIG).is_file()


def _read_tests(pdir):
    pdir = Path(pdir)
    tests = {}
    for p in sorted(pdir.glob("*" + TEST_SUFFIX)):
        tests[p.name[:-len(TEST_SUFFIX)]] = p.read_text(encoding="utf-8")
    return tests


def load(pdir):
    """Ordner laden: wavetb.json + <test>.wave.json (altes Layout project.json + tests/ wird mitgelesen)."""
    pdir = Path(pdir)
    cfg = dict(DEFAULT)
    new, old = pdir / CONFIG_NAME, pdir / LEGACY_CONFIG
    if new.is_file():
        cfg.update(json.loads(new.read_text(encoding="utf-8")))
        return cfg, _read_tests(pdir)
    tests = {}
    if old.is_file():
        cfg.update(json.loads(old.read_text(encoding="utf-8")))
        td = pdir / "tests"
        if td.is_dir():
            for p in sorted(td.glob("*.json")):
                tests[p.stem] = p.read_text(encoding="utf-8")
    return cfg, tests


def absolutize(pdir, cfg):
    """Relative Pfade der Config gegen pdir aufloesen (beim Wechsel des Ordners)."""
    out = dict(cfg)
    if str(out.get("top", "")).strip():
        out["top"] = str(_abs(pdir, out["top"]))
    out["search"] = [str(_abs(pdir, x)) for x in out.get("search", []) if str(x).strip()]
    return out


def _relativize(pdir, p):
    """Pfad relativ zum Projektordner speichern (portabel), wenn auf demselben Laufwerk."""
    p = str(p).strip()
    if not p or not os.path.isabs(p):
        return p
    try:
        rel = os.path.relpath(p, str(Path(pdir).resolve())).replace('\\', '/')
    except ValueError:      # anderes Laufwerk
        return p
    return p if rel.count('../') > 3 else rel      # sehr weit entfernt: absolut ist lesbarer


def save(pdir, cfg, tests):
    pdir = Path(pdir)
    pdir.mkdir(parents=True, exist_ok=True)
    merged = dict(DEFAULT)
    merged.update(cfg)
    merged["top"] = _relativize(pdir, merged.get("top", ""))
    merged["search"] = [_relativize(pdir, s) for s in merged.get("search", []) if str(s).strip()]
    (pdir / CONFIG_NAME).write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    for name, text in tests.items():
        (pdir / (name + TEST_SUFFIX)).write_text(text, encoding="utf-8")
    for p in pdir.glob("*" + TEST_SUFFIX):
        if p.name[:-len(TEST_SUFFIX)] not in tests:
            p.unlink()


def _abs(pdir, p):
    p = Path(str(p).strip())
    return (p if p.is_absolute() else Path(pdir) / p).resolve()


def _glob_files(pdir, patterns):
    out = []
    for pat in patterns or []:
        pat = str(pat).strip()
        if not pat:
            continue
        full = pat if Path(pat).is_absolute() else str(Path(pdir) / pat)
        for f in sorted(glob.glob(full, recursive=True)):
            fp = Path(f).resolve()
            if fp not in out:
                out.append(fp)
    return out


def top_path(pdir, cfg):
    top = (cfg.get("top") or "").strip()
    if not top:
        return None
    tp = _abs(pdir, top)
    if not tp.is_file():
        raise SpecError("Top-Datei nicht gefunden: %s" % tp)
    return tp


def resolve_sources(pdir, cfg):
    """-> (dateien in Compile-Reihenfolge, warnungen).
    Mit 'top': Abhaengigkeiten ab der Top-Datei (Suche in ihrem Ordner + 'search', rekursiv).
    Ohne 'top': alle Dateien aus 'sources' (Globs), nur sortiert."""
    explicit = _glob_files(pdir, cfg.get("sources"))
    tp = top_path(pdir, cfg)
    if tp:
        dirs = [tp.parent] + [_abs(pdir, s) for s in cfg.get("search", []) if str(s).strip()]
        universe, warn = deps.scan(dirs)
        order, w2 = deps.resolve([tp] + explicit, universe + explicit)
        return order, warn + w2
    if not explicit:
        raise SpecError("Keine Quellen: bitte eine Top-Datei waehlen")
    return deps.resolve(explicit, explicit)


def source_files(pdir, cfg):
    return resolve_sources(pdir, cfg)[0]


def entities_of(pdir, cfg):
    """Entities, aus denen gewaehlt werden kann: -> {name_lower: entity}"""
    tp = top_path(pdir, cfg)
    files = [tp] if tp else _glob_files(pdir, cfg.get("sources"))
    ents = {}
    for f in files:
        try:
            ents.update(parse_entities(f.read_text(encoding="utf-8", errors="replace")))
        except SpecError as e:
            raise SpecError("%s: %s" % (f.name, e))
    return ents


def pick_entity(ents, name):
    """Gewuenschte Entity, sonst die einzige, sonst die letzte der Datei (Top steht meist unten)."""
    name = (name or "").strip().lower()
    if name:
        return ents.get(name)
    return list(ents.values())[-1] if ents else None


def find_entity(pdir, cfg):
    """-> entity-dict oder None."""
    try:
        return pick_entity(entities_of(pdir, cfg), cfg.get("entity"))
    except SpecError:
        if (cfg.get("top") or "").strip():
            raise
        return None


def ports_dict(ent):
    return {p["name"].lower(): p for p in ent["ports"]} if ent else None


def browse(path, mode="file"):
    """Server-seitiger Datei-Dialog. -> {path, parent, dirs, files}"""
    if not path:
        if os.name == "nt":
            drives = ["%s:\\" % c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists("%s:\\" % c)]
            return {"path": "", "parent": None, "dirs": drives, "files": [], "drives": True}
        path = "/"
    p = Path(path)
    if p.is_file():
        p = p.parent
    if not p.is_dir():
        p = Path.home()
    dirs, files = [], []
    try:
        for e in os.scandir(p):
            if e.name.startswith("."):
                continue
            if e.is_dir():
                dirs.append(e.name)
            elif mode == "file" and e.name.lower().endswith(deps.EXTS):
                files.append(e.name)
    except OSError:
        pass
    parent = str(p.parent) if p.parent != p else ""
    return {"path": str(p), "parent": parent, "dirs": sorted(dirs, key=str.lower),
            "files": sorted(files, key=str.lower)}
