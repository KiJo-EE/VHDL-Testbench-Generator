"""VHDL-Testbench-Generator (plain VHDL-2008 oder VUnit)."""
import re
from pathlib import Path

from . import project
from .core import SpecError, build_wave
from .vhdl import make_port


def _ident(s):
    return re.sub(r'\W', '_', s).strip('_') or 'test'


def _ports_from_waves(waves):
    ports, seen = [], {}
    for w in waves.values():
        for s in w['signals']:
            key = s['name'].lower()
            if key in seen:
                if seen[key]['dir'] != s['dir']:
                    raise SpecError("Signal '%s' hat in Tests unterschiedliche Richtungen" % s['name'])
                continue
            vec = s['width'] or any(c['v'] == 'd' for c in s['cells'])
            if vec and not s['width']:
                raise SpecError("Signal '%s': 'width' fehlt (kein VHDL-Entity gefunden)" % s['name'])
            t = 'std_logic_vector(%d downto 0)' % (s['width'] - 1) if vec else 'std_logic'
            p = make_port(s['name'], s['dir'], t)
            seen[key] = p
            ports.append(p)
    return ports


def _bits(n, w, label, name):
    """Zweierkomplement-Bitstring, mit Bereichspruefung."""
    if n < 0:
        if n < -(1 << (w - 1)):
            raise SpecError("Wert %s passt nicht in %s (%d Bit)" % (label, name, w))
        n &= (1 << w) - 1
    elif n >= 1 << w:
        raise SpecError("Wert %s passt nicht in %s (%d Bit)" % (label, name, w))
    return format(n, '0%db' % w)


def _fill(p, ch):
    """Konstante, die ein ganzes Signal mit ch ('X','Z','0','1') fuellt."""
    if p['scalar']:
        return "'%s'" % ch
    if p['width']:
        return '"%s"' % (ch * p['width'])
    return "(%s'range => '%s')" % (p['name'], ch)


def _bitstring(n, w, label, name):
    """Zweierkomplement-Bitstring, mit Bereichspruefung."""
    if n < 0:
        if n < -(1 << (w - 1)):
            raise SpecError("Wert %s passt nicht in %s (%d Bit)" % (label, name, w))
        n &= (1 << w) - 1
    elif n >= 1 << w:
        raise SpecError("Wert %s passt nicht in %s (%d Bit)" % (label, name, w))
    return '"%s"' % format(n, '0%db' % w)


def _literal(n, base):
    if n >= 0 and base == 16:
        return '16#%X#' % n
    if n >= 0 and base == 2:
        return '2#%s#' % format(n, 'b')
    if n >= 0 and base == 8:
        return '8#%o#' % n
    return str(n)


def _data_expr(p, c):
    n, w, name = c['num'], p['width'], p['name']
    signed = bool(c.get('signed')) or n < 0
    if w:
        lo, hi = (-(1 << (w - 1)), (1 << (w - 1)) - 1) if signed else (0, (1 << w) - 1)
        if not lo <= n <= hi:
            raise SpecError("Wert %s passt nicht in %s (%d Bit%s)" % (c['label'], name, w, ', signed' if signed else ''))
        if not -(1 << 31) < n < (1 << 31):
            return _bitstring(n, w, c['label'], name)
    inner = ("to_signed(%s, %s'length)" if signed else "to_unsigned(%s, %s'length)") % (
        _literal(n, c.get('base')), name)
    kind, base = ('signed' if signed else 'unsigned'), p['base']
    if base == 'slv':
        return 'std_logic_vector(%s)' % inner
    if base == 'slvu':
        return 'std_ulogic_vector(%s)' % inner
    return inner if base == kind else '%s(%s)' % (base, inner)


def _value(p, c, default):
    """VHDL-Ausdruck fuer den Wert eines Signals in einem Zyklus (c=None -> default)."""
    name = p['name']
    if c is None:
        return _fill(p, default)
    v = c['v']
    if v in ('x', 'z', '0', '1'):
        return _fill(p, v.upper())
    if v == 'd':
        if p['scalar']:
            raise SpecError("Signal '%s' ist 1 Bit breit, hat aber Datenwerte" % name)
        return _fill(p, 'X') if c['num'] is None else _data_expr(p, c)
    raise SpecError("Signal '%s': Takt-Wellenform an falscher Stelle" % name)


def _calls(wave, ports, clock, ind):
    pad = ' ' * ind
    sigs = {s['name'].lower(): s for s in wave['signals']}
    args = [(p, sigs.get(p['name'].lower())) for p in ports if p['name'] != clock]
    L = []
    for i in range(wave['ncyc']):
        L.append('%s-- Cycle %d.' % (pad, i))
        L.append('%scheck_cycle (' % pad)
        items = []
        for p, s in args:
            c = s['cells'][i] if s else None
            e = _value(p, c, 'X' if p['dir'] == 'out' else '0')
            items.append('%s    %s_value => %s' % (pad, p['name'], e))
        L.append(',\n'.join(items))
        L.append('%s);' % pad)
        L.append('')
    return L


def _procedure(ports, clock, edge, ind):
    pad = ' ' * ind
    io = [p for p in ports if p['name'] != clock]
    L = ['%sprocedure check_cycle (' % pad]
    L.append(';\n'.join('%s    constant %s_value : in %s' % (pad, p['name'], p['type']) for p in io))
    L += ['%s) is' % pad, '%sbegin' % pad]
    for p in io:
        if p['dir'] != 'out':
            L.append('%s    %s <= %s_value;' % (pad, p['name'], p['name']))
    L.append('%s    wait until %s(%s);' % (pad, edge, clock))
    for p in io:
        if p['dir'] != 'out':
            continue
        n = p['name']
        dc = "'X'" if p['scalar'] else "(%s_value'range => 'X')" % n
        L += ['%s    if %s_value /= %s then' % (pad, n, dc),
              '%s        if %s /= %s_value then' % (pad, n, n),
              '%s            errors := errors + 1;' % pad,
              '%s            report "cycle " & integer\'image(cycle) & ": %s - expected \'" & to_string(%s_value) &' % (pad, n, n),
              '%s                "\' got \'" & to_string(%s) & "\'" severity error;' % (pad, n),
              '%s        end if;' % pad,
              '%s    end if;' % pad]
    L += ['%s    cycle := cycle + 1;' % pad, '%send procedure check_cycle;' % pad, '']
    return L


def _header(entity, what):
    import datetime
    return ['-' * 80, '--', '--! @file    %s' % what, '--! @brief   Generated testbench for %s (wavetb).' % entity,
            '--! @date    %s' % datetime.date.today().strftime('%d/%m/%Y'),
            '--! @details Self-checking testbench generated from WaveJSON. Do not edit by hand.',
            '--', '-' * 80, '']


def _arch_head(tb, entity, ports, clock, cch, period_ps):
    L = ['architecture test of %s is' % tb, '    constant CLK_PERIOD : time := %d ps;' % period_ps, '']
    for p in ports:
        if p['name'] == clock:
            init = " := '0'" if cch in 'nN' else " := '1'"
        elif p['dir'] == 'out':
            init = ''
        elif p['scalar']:
            init = " := '0'"
        else:
            init = " := (others => 'X')"
        L.append('    signal %s : %s%s;' % (p['name'], p['type'], init))
    L += ['', '    component %s is' % entity, '        port (']
    L.append(';\n'.join('            %s : %s %s' % (p['name'], p['dir'], p['type']) for p in ports))
    L += ['        );', '    end component;', '', 'begin', '', '    UUT : %s' % entity, '        port map (']
    L.append(',\n'.join('            %s => %s' % (p['name'], p['name']) for p in ports))
    L += ['        );', '', '    %s <= not %s after CLK_PERIOD / 2;' % (clock, clock), '']
    return L


def _clock_info(wave):
    clock = wave['clock']
    cch = next(s for s in wave['signals'] if s['name'] == clock)['cells'][0]['clk']
    return clock, cch, ('falling_edge' if cch in 'nN' else 'rising_edge')


def plain_tb(tb, entity, ports, wave, test, period_ps):
    clock, cch, edge = _clock_info(wave)
    out = _header(entity, tb + '.vhd') + [
        'library ieee;', 'use ieee.std_logic_1164.all;', 'use ieee.numeric_std.all;', 'use std.env.all;', '',
        'entity %s is' % tb, 'end entity; -- %s' % tb, ''] + _arch_head(tb, entity, ports, clock, cch, period_ps) + [
        '    process', '        variable errors : natural := 0;', '        variable cycle  : natural := 0;', ''] + \
        _procedure(ports, clock, edge, 8) + ['    begin', '        -- Test: %s' % test, ''] + \
        _calls(wave, ports, clock, 8) + [
        '        if errors = 0 then',
        '            report "TEST PASSED: %s";' % test,
        '            finish;',
        '        else',
        '            report "TEST FAILED: " & integer\'image(errors) & " mismatch(es) in %s" severity failure;' % test,
        '        end if;',
        '        wait;', '    end process;', '', 'end architecture; -- test', '']
    return '\n'.join(out)


def vunit_tb(tb, entity, ports, waves, period_ps):
    first = next(iter(waves.values()))
    clock, cch, edge = _clock_info(first)
    maxn = max(w['ncyc'] for w in waves.values())
    out = _header(entity, tb + '.vhd') + [
        'library ieee;', 'use ieee.std_logic_1164.all;', 'use ieee.numeric_std.all;', '',
        'library vunit_lib;', 'context vunit_lib.vunit_context;', '',
        'entity %s is' % tb, '    generic (runner_cfg : string);', 'end entity; -- %s' % tb, ''] + \
        _arch_head(tb, entity, ports, clock, cch, period_ps) + [
        '    test_runner_watchdog(runner, %d * CLK_PERIOD);' % (maxn + 20), '',
        '    process', '        variable errors : natural := 0;', '        variable cycle  : natural := 0;', ''] + \
        _procedure(ports, clock, edge, 8) + [
        '    begin', '        test_runner_setup(runner, runner_cfg);', '', '        while test_suite loop',
        '            errors := 0;', '            cycle  := 0;', '']
    for k, (name, w) in enumerate(waves.items()):
        out.append('            %s run("test_%s") then' % ('if' if k == 0 else 'elsif', name))
        out.append('')
        out += _calls(w, ports, clock, 16)
    out += ['            end if;', '',
            '            check_equal(errors, 0, "Mismatches between DUT and waveform");',
            '        end loop;', '', '        test_runner_cleanup(runner);', '    end process;', '',
            'end architecture; -- test', '']
    return '\n'.join(out)


MARK = 'Self-checking testbench generated from WaveJSON'
RUN_MARK = '# Generiert von wavetb.'

RUN_PY = '''# Generiert von wavetb.
from pathlib import Path
from vunit import VUnit

ROOT = Path(__file__).resolve().parent
vu = VUnit.from_argv(vhdl_standard="2008", compile_builtins=False)
vu.add_vhdl_builtins()
lib = vu.add_library("lib")
for f in %r:
    lib.add_source_files(f)
for f in %r:
    lib.add_source_files(ROOT / f)
vu.main()
'''


def generate(pdir, cfg, tests):
    """Erzeugt die Testbenches direkt in <pdir>. -> {'tbs': [...], 'runpy': Path|None}"""
    pdir = Path(pdir)
    if not tests:
        raise SpecError("Keine Tests vorhanden")
    ent = project.find_entity(pdir, cfg)
    if not ent and (cfg.get('top') or '').strip():
        raise SpecError("Entity '%s' nicht in der Top-Datei gefunden" % (cfg.get('entity') or '?'))
    ename = ent['name'] if ent else (cfg.get('entity') or '').strip()
    if not ename:
        raise SpecError("Keine Entity: bitte eine Top-Datei waehlen")
    ports = ent['ports'] if ent else None
    pd = project.ports_dict(ent)
    waves = {n: build_wave(t, pd, cfg.get('clock', ''), True) for n, t in tests.items()}
    clocks = {w['clock'] for w in waves.values()}
    if len(clocks) > 1:
        raise SpecError("Tests verwenden verschiedene Takt-Signale: %s" % ', '.join(sorted(clocks)))
    if ports is None:
        ports = _ports_from_waves(waves)
    try:
        period_ps = round(float(cfg.get('period_ns', 10)) * 1000)
    except (TypeError, ValueError):
        raise SpecError("Takt-Periode ungueltig")
    if period_ps < 20:
        raise SpecError("Takt-Periode zu klein")

    pdir.mkdir(parents=True, exist_ok=True)
    written = []

    def put(path, text):
        if path.exists() and MARK not in path.read_text(encoding='utf-8', errors='replace')[:2000] \
                and RUN_MARK not in path.read_text(encoding='utf-8', errors='replace')[:200]:
            raise SpecError("%s existiert und stammt nicht von WaveTB - wird nicht ueberschrieben" % path.name)
        path.write_text(text, encoding='utf-8')
        written.append(path)

    tbs, runpy = [], None
    if cfg.get('mode') == 'vunit':
        tb = '%s_tb' % _ident(ename)
        f = pdir / (tb + '.vhd')
        put(f, vunit_tb(tb, ename, ports, {_ident(n): w for n, w in waves.items()}, period_ps))
        tbs.append({'file': f, 'entity': tb, 'test': None, 'order': {n: [(x['name'], x['group']) for x in w['signals']] for n, w in waves.items()}})
        runpy = pdir / 'run_vunit.py'
        srcs = [str(s).replace('\\', '/') for s in project.source_files(pdir, cfg)]
        put(runpy, RUN_PY % (srcs, [f.name]))
    else:
        for n, w in waves.items():
            tb = '%s_%s_tb' % (_ident(ename), _ident(n))
            f = pdir / (tb + '.vhd')
            put(f, plain_tb(tb, ename, ports, w, n, period_ps))
            tbs.append({'file': f, 'entity': tb, 'test': n, 'order': {n: [(x['name'], x['group']) for x in w['signals']]}})
    # veraltete, von WaveTB erzeugte Dateien (umbenannte/geloeschte Tests, Moduswechsel) entfernen
    for old in list(pdir.glob('*_tb.vhd')) + list(pdir.glob('run_vunit.py')):
        if old in written:
            continue
        head = old.read_text(encoding='utf-8', errors='replace')[:2000]
        if MARK in head or RUN_MARK in head:
            old.unlink()
    return {'tbs': tbs, 'runpy': runpy, 'entity': ename}


def skeleton(ent, clock=''):
    """Vorlage fuer einen neuen Test aus den Ports des Entity (Spalten ausgerichtet)."""
    rows = []                                   # (dir, name, wave, extras)
    for p in ent['ports']:
        is_clk = p['scalar'] and p['dir'] == 'in' and (
            p['name'].lower() == clock.lower() if clock else bool(re.search(r'clk|clock', p['name'], re.I)))
        w = 'width: %d' % p['width'] if p['width'] else ''
        if is_clk:
            rows.append(('in', p['name'], 'p.......', ''))
            clock = p['name']
        elif p['scalar']:
            rows.append((p['dir'], p['name'], ('x' if p['dir'] == 'out' else '0') + '.......', ''))
        elif p['dir'] == 'out':
            rows.append(('out', p['name'], 'x.......', w))
        else:
            rows.append((p['dir'], p['name'], '=.......', 'data: ["0"], radix: \'h\'' + (', ' + w if w else '')))
    dirs = ["dir: '%s'" % r[0] for r in rows]
    names = ["name: '%s'" % r[1] for r in rows]
    mids = ["wave: '%s'%s" % (r[2], ' ,  ' + r[3] if r[3] else '') for r in rows]
    dw, nw, mw = (max(len(x) for x in col) for col in (dirs, names, mids))
    lines = ['    { %s ,  %s ,  %s },' % (d.ljust(dw), n.ljust(nw), m.ljust(mw)) for d, n, m in zip(dirs, names, mids)]
    return '{\n  signal: [\n%s\n  ],\n}\n' % '\n'.join(lines)
