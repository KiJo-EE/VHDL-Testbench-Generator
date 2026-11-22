"""Abhaengigkeiten zwischen VHDL-Dateien aufloesen (Untermodule, Packages, getrennte Architekturen).

Ausgehend von einer oder mehreren Start-Dateien werden alle benoetigten Dateien gefunden und in
Compile-Reihenfolge (Abhaengigkeiten zuerst) zurueckgegeben. Nicht benoetigte Dateien im Suchbaum
werden ignoriert.
"""
import os
import re
from pathlib import Path

EXTS = ('.vhd', '.vhdl')
SKIP_DIRS = {'build', 'vunit_out', '__pycache__', 'node_modules'}
MAX_FILES = 5000

_ENTITY = re.compile(r'^\s*entity\s+(\w+)\s+is\b', re.I | re.M)
_PACKAGE = re.compile(r'^\s*package\s+(?!body\b)(\w+)\s+is\b', re.I | re.M)
_PKGBODY = re.compile(r'^\s*package\s+body\s+(\w+)\s+is\b', re.I | re.M)
_ARCH = re.compile(r'^\s*architecture\s+\w+\s+of\s+(\w+)\s+is\b', re.I | re.M)
_WORK = re.compile(r'\bwork\s*\.\s*(\w+)', re.I)
_INST = re.compile(r'\b\w+\s*:\s*(?:component\s+)?(\w+)\s*(?:generic|port)\s+map\b', re.I)


class Unit:
    def __init__(self, path):
        self.path = path
        text = path.read_text(encoding='utf-8', errors='replace')
        text = re.sub(r'--[^\n]*', '', text)
        low = lambda it: {x.lower() for x in it}  # noqa: E731
        self.provides = low(_ENTITY.findall(text)) | low(_PACKAGE.findall(text))
        self.extends = low(_ARCH.findall(text)) | low(_PKGBODY.findall(text))
        refs = low(_WORK.findall(text)) | low(_INST.findall(text)) | self.extends
        self.refs = refs - self.provides


def scan(dirs):
    """Alle VHDL-Dateien unterhalb der Ordner (rekursiv). -> (liste, warnungen)"""
    found, warn = [], []
    for d in dirs:
        d = Path(d)
        if not d.is_dir():
            warn.append('Suchordner nicht gefunden: %s' % d)
            continue
        for root, subdirs, files in os.walk(d):
            subdirs[:] = [s for s in subdirs if s not in SKIP_DIRS and not s.startswith('.')]
            for f in sorted(files):
                if f.lower().endswith(EXTS):
                    p = Path(root, f).resolve()
                    if p not in found:
                        found.append(p)
            if len(found) > MAX_FILES:
                warn.append('Mehr als %d VHDL-Dateien im Suchbaum - Suche abgebrochen. '
                            'Top-Datei naeher an den Quellen waehlen.' % MAX_FILES)
                return found, warn
    return found, warn


def resolve(roots, universe):
    """roots: Start-Dateien, universe: durchsuchbare Dateien.
    -> (dateien in Compile-Reihenfolge, warnungen)"""
    roots = [Path(r).resolve() for r in roots]
    universe = list(dict.fromkeys([Path(u).resolve() for u in universe] + roots))
    units, warn = {}, []
    for p in universe:
        try:
            units[p] = Unit(p)
        except OSError as e:
            warn.append('Datei nicht lesbar: %s (%s)' % (p, e))
    provides, extends = {}, {}
    for p, u in units.items():
        for n in u.provides:
            provides.setdefault(n, []).append(p)
        for n in u.extends:
            extends.setdefault(n, []).append(p)

    def best(cands, frm):
        def key(c):
            return (c.parent != frm.parent, len(c.parts))
        return sorted(cands, key=key)[0]

    order, seen, missing = [], set(), set()

    def visit(f):
        if f in seen or f not in units:
            return
        seen.add(f)
        u = units[f]
        for name in sorted(u.refs):
            cands = [c for c in provides.get(name, []) if c != f]
            if not cands:
                if name not in u.extends:
                    missing.add(name)
                continue
            if len(cands) > 1:
                warn.append("'%s' ist mehrfach definiert (%s) - verwende %s" % (
                    name, ', '.join(c.name for c in cands), best(cands, f).name))
            visit(best(cands, f))
        order.append(f)
        for name in sorted(u.provides):
            for ext in extends.get(name, []):
                visit(ext)

    for r in roots:
        visit(r)
    # nur Namen melden, die nirgends (auch nicht als Entity/Package im selben Baum) vorkommen
    local = set(provides)
    for n in sorted(missing - local):
        warn.append("'%s' nicht in den Quellen gefunden (Vendor-Primitive/Bibliothek?)" % n)
    return order, list(dict.fromkeys(warn))
