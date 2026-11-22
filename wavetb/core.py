"""Parser fuer WaveDrom-artige Wellenform-Beschreibungen (lockeres JSON)."""
import json
import re


class SpecError(Exception):
    pass


_RADIX = {'h': 16, 'x': 16, 'hex': 16, 'b': 2, 'bin': 2, 'd': 10, 'dec': 10, 'o': 8, 'oct': 8}


def loose_loads(text):
    """JSON mit JS-Komfort: unquoted keys, 'single quotes', Kommentare, trailing commas."""
    toks, buf, i, n = [], [], 0, len(text)
    while i < n:
        c = text[i]
        if c in "\"'":
            j, s = i + 1, []
            while j < n and text[j] != c:
                if text[j] == '\\' and j + 1 < n:
                    j += 1
                s.append(text[j])
                j += 1
            if j >= n:
                raise SpecError("String nicht geschlossen (Zeile %d)" % (text.count("\n", 0, i) + 1))
            toks.append(('c', ''.join(buf)))
            buf = []
            toks.append(('s', json.dumps(''.join(s))))
            i = j + 1
        elif text.startswith('//', i):
            j = text.find('\n', i)
            i = n if j < 0 else j
        elif text.startswith('/*', i):
            j = text.find('*/', i + 2)
            j = n if j < 0 else j + 2
            buf.append('\n' * text.count('\n', i, j))
            i = j
        else:
            buf.append(c)
            i += 1
    toks.append(('c', ''.join(buf)))
    out = []
    for kind, t in toks:
        if kind == 'c':
            t = re.sub(r'([{,]\s*)([A-Za-z_$][\w$]*)(\s*:)', r'\1"\2"\3', t)
            t = re.sub(r',(\s*[}\]])', r'\1', t)
        out.append(t)
    try:
        return json.loads(''.join(out))
    except json.JSONDecodeError as e:
        raise SpecError("Syntaxfehler in Zeile %d: %s" % (e.lineno, e.msg))


def parse_num(label, radix=None):
    """-> (wert|None, basis|None, vorzeichenbehaftet). Basis nur bei explizitem radix."""
    s = str(label).strip().replace('_', '')
    if not s:
        return None, None, False
    r = str(radix).lower() if radix else ''
    signed = False
    if r[:1] == 's' and r[1:] in _RADIX:      # 'sd' = vorzeichenbehaftet dezimal usw.
        r, signed = r[1:], True
    base = _RADIX.get(r)
    try:
        if base:
            return int(s, base), base, signed
        if s.lower().lstrip('-').startswith(('0x', '0b', '0o')):
            return int(s, 0), None, signed
        if s.lstrip('-').isdigit():
            return int(s), None, signed
        return int(s, 16), None, signed
    except ValueError:
        return None, base, signed


def expand_wave(wave, data, radix, reps=1):
    cells, di, prev = [], 0, None
    for ch in wave:
        if ch in '.|':
            c = dict(prev) if prev else {'v': 'x'}
            c['cont'] = prev is not None
        elif ch in 'pnPN':
            c = {'v': 'clk', 'clk': ch}
        elif ch in '01':
            c = {'v': ch}
        elif ch in 'hH':
            c = {'v': '1'}
        elif ch in 'lL':
            c = {'v': '0'}
        elif ch in 'xX':
            c = {'v': 'x'}
        elif ch in 'zZ':
            c = {'v': 'z'}
        elif ch == '=' or ch in '23456789':
            label = data[di] if di < len(data) else ''
            di += 1
            num, base, sgn = parse_num(label, radix)
            c = {'v': 'd', 'label': str(label), 'num': num, 'base': base, 'signed': sgn}
        else:
            raise SpecError("Unbekanntes Wave-Zeichen '%s'" % ch)
        c.setdefault('cont', False)
        cells.append(c)
        prev = c
    if reps > 1:
        out = []
        for c in cells:
            out.append(c)
            for _ in range(reps - 1):
                d = dict(c)
                d['cont'] = True
                out.append(d)
        cells = out
    return cells


def _flatten(items, group, out):
    for it in items:
        if isinstance(it, list):
            if it and isinstance(it[0], str):
                _flatten(it[1:], it[0], out)
            else:
                _flatten(it, group, out)
        elif isinstance(it, dict):
            if it.get('name') and 'wave' in it:
                out.append((it, group))


def _norm_dir(d):
    d = str(d or '').lower()
    return {'in': 'in', 'input': 'in', 'out': 'out', 'output': 'out', 'inout': 'inout'}.get(d, '')


def build_wave(text, ports=None, clock='', strict=True):
    """Liefert {'signals': [...], 'ncyc': n, 'clock': name}.

    ports: {name_lower: port_dict} aus dem VHDL-Entity (optional).
    strict=False: fuer die Vorschau, Fehler bei dir/Port werden toleriert.
    """
    obj = loose_loads(text)
    if not isinstance(obj, dict) or not isinstance(obj.get('signal'), list):
        raise SpecError("Erwartet ein Objekt mit 'signal: [ ... ]'")
    flat = []
    _flatten(obj['signal'], None, flat)
    if not flat:
        raise SpecError("Keine Signale definiert")
    sigs = []
    for item, group in flat:
        data = item.get('data', [])
        if isinstance(data, str):
            data = data.split()
        try:
            reps = max(1, int(float(item.get('period', 1))))
        except (TypeError, ValueError):
            reps = 1
        cells = expand_wave(str(item.get('wave', '')), data, item.get('radix'), reps)
        width = item.get('width')
        sigs.append({
            'name': str(item['name']), 'dir': _norm_dir(item.get('dir')),
            'width': int(width) if width else None, 'group': group, 'cells': cells,
        })
    n = max((len(s['cells']) for s in sigs), default=0)
    if n == 0:
        raise SpecError("Alle Wellenformen sind leer")
    for s in sigs:
        if not s['cells']:
            s['cells'] = [{'v': 'x', 'cont': False}]
        while len(s['cells']) < n:
            c = dict(s['cells'][-1])
            c['cont'] = True
            s['cells'].append(c)

    if ports is not None:
        for s in sigs:
            p = ports.get(s['name'].lower())
            if p:
                s['name'], s['dir'] = p['name'], p['dir']
                s['width'] = p['width'] or s['width']
            elif strict:
                raise SpecError("Signal '%s' existiert nicht im Entity" % s['name'])

    clk = None
    for s in sigs:
        is_clk = s['cells'][0]['v'] == 'clk'
        if clock and s['name'].lower() == clock.lower():
            if not is_clk:
                raise SpecError("Clock '%s' braucht eine p/n-Wellenform" % clock)
            clk = s
        elif not clock and is_clk and clk is None:
            clk = s
    if clk is None and strict:
        raise SpecError("Kein Takt gefunden (Signal mit Wellenform 'p...' / 'n...')")
    for s in sigs:
        if s is clk:
            s['dir'] = 'in'
        elif not s['dir'] and strict:
            raise SpecError("Signal '%s' hat keine Richtung (dir: 'in' | 'out')" % s['name'])
    return {'signals': sigs, 'ncyc': n, 'clock': clk['name'] if clk else ''}
