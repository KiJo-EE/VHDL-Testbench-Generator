"""Minimaler VHDL-Entity-Parser (Ports + Generics)."""
import re

from .core import SpecError


def _strip_comments(t):
    return re.sub(r'--[^\n]*', '', t)


def _paren_block(t, start):
    """t[start] == '(' -> Inhalt bis zur passenden ')'."""
    depth = 0
    for i in range(start, len(t)):
        if t[i] == '(':
            depth += 1
        elif t[i] == ')':
            depth -= 1
            if depth == 0:
                return t[start + 1:i], i
    raise SpecError("Klammern im Entity nicht ausgeglichen")


def _split_top(t, sep=';'):
    parts, depth, cur = [], 0, []
    for ch in t:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(''.join(cur))
            cur = []
        else:
            cur.append(ch)
    if ''.join(cur).strip():
        parts.append(''.join(cur))
    return parts


def _eval(expr, gen):
    e = expr
    for k, v in gen.items():
        e = re.sub(r'\b%s\b' % re.escape(k), str(v), e, flags=re.I)
    if re.fullmatch(r'[\d\s+\-*/()]+', e):
        try:
            return int(eval(e.replace('/', '//'), {'__builtins__': {}}, {}))
        except Exception:
            return None
    return None


_DECL = re.compile(r'^\s*(?:signal\s+|constant\s+)?(?P<names>[\w\s,]+?)\s*:\s*'
                   r'(?:(?P<dir>in|out|inout|buffer)\b\s*)?(?P<type>.+?)\s*(?::=.*)?$', re.I | re.S)


def make_port(name, direction, type_text, generics=None, spec_width=None):
    t = ' '.join(type_text.split())
    base = t.lower().split('(')[0].strip()
    port = {'name': name, 'dir': {'buffer': 'out'}.get(direction, direction), 'type': t,
            'width': None, 'scalar': False, 'base': None}
    if base in ('std_logic', 'std_ulogic'):
        port.update(scalar=True, base='sl')
        return port
    kinds = {'std_logic_vector': 'slv', 'std_ulogic_vector': 'slvu', 'unsigned': 'unsigned', 'signed': 'signed'}
    if base not in kinds:
        raise SpecError("Port '%s': Typ '%s' wird nicht unterstuetzt (nur std_logic und Vektoren)" % (name, t))
    port['base'] = kinds[base]
    m = re.search(r'\(\s*(.+?)\s+downto\s+(.+?)\s*\)', t, re.I)
    if m:
        hi, lo = _eval(m.group(1), generics or {}), _eval(m.group(2), generics or {})
        if hi is not None and lo is not None:
            port['width'] = hi - lo + 1
    if port['width'] is None and spec_width:
        port['width'] = spec_width
    if port['width']:
        port['type'] = '%s(%d downto 0)' % (t.split('(')[0].strip(), port['width'] - 1)
    return port


def parse_entities(text, spec_widths=None):
    """-> {name_lower: {'name', 'ports': [port,...], 'generics': {..}}}"""
    t = _strip_comments(text)
    found = {}
    for m in re.finditer(r'\bentity\s+(\w+)\s+is\b', t, re.I):
        name = m.group(1)
        end = re.compile(r'\bend\s+(?:entity\s*)?(?:%s\s*)?;' % re.escape(name), re.I).search(t, m.end())
        body = t[m.end(): end.start() if end else len(t)]
        generics = {}
        g = re.search(r'\bgeneric\s*\(', body, re.I)
        if g:
            inner, _ = _paren_block(body, g.end() - 1)
            for decl in _split_top(inner):
                dm = re.match(r'\s*([\w\s,]+?)\s*:\s*\w+\s*:=\s*(.+?)\s*$', decl, re.S)
                if dm:
                    val = _eval(dm.group(2), generics)
                    if val is not None:
                        for gn in dm.group(1).split(','):
                            generics[gn.strip()] = val
        ports = []
        p = re.search(r'\bport\s*\(', body, re.I)
        if p:
            inner, _ = _paren_block(body, p.end() - 1)
            for decl in _split_top(inner):
                dm = _DECL.match(decl)
                if not dm:
                    continue
                d = (dm.group('dir') or 'in').lower()
                for pn in dm.group('names').split(','):
                    pn = pn.strip()
                    if pn:
                        ports.append(make_port(pn, d, dm.group('type'), generics))
        found[name.lower()] = {'name': name, 'ports': ports, 'generics': generics}
    return found
