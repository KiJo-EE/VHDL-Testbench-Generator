"""GHDL / VUnit ausfuehren und Surfer starten."""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import gen, project
from .core import SpecError

STD = '--std=08'


def _run(cmd, cwd, log, env=None):
    exe = shutil.which(cmd[0])
    if not exe:
        raise SpecError("'%s' nicht im PATH gefunden" % cmd[0])
    log.append('$ ' + ' '.join([cmd[0]] + [str(c) for c in cmd[1:]]))
    p = subprocess.run([exe] + [str(c) for c in cmd[1:]], cwd=str(cwd), capture_output=True, text=True,
                       errors='replace', env=env)
    out = re.sub(r'\[[0-9;]*m', '', p.stdout + p.stderr).strip()
    if out:
        log.append(out)
    return p.returncode


def find_surfer(cfg):
    for cand in (cfg.get('surfer'), os.environ.get('SURFER'), shutil.which('surfer')):
        if cand and (Path(cand).exists() or shutil.which(cand)):
            return cand
    return None


def open_surfer(cfg, wave, log, scope=None, names=()):
    s = find_surfer(cfg)
    if not s:
        log.append("Surfer nicht gefunden (PATH, Umgebungsvariable SURFER oder 'surfer' in project.json).")
        return False
    cmd = [s, str(wave)]
    if scope and names:
        cf = Path(str(wave) + '.surfer.cmd')
        lines, grp = [], None
        for n, g in names:
            if g != grp:
                if grp:
                    lines.append('divider_add')          # Trennstrich am Gruppenende
                if g:
                    # Surfer-Batchbefehle kennen keine Gruppen -> benannte Trennlinie (ein Wort)
                    lines.append('divider_add ' + '_'.join(str(g).split()))
            grp = g
            lines.append('variable_add %s.%s' % (scope, n.lower()))
        if grp:
            lines.append('divider_add')
        lines.append('zoom_fit')
        cf.write_text(chr(10).join(lines) + chr(10), encoding='utf-8')
        cmd += ['-c', str(cf)]
    kw = {}
    if sys.platform == 'win32':
        kw['creationflags'] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
    log.append('Surfer gestartet: %s' % wave)
    return True


def execute(pdir, cfg, tests, action='sim', test=None, surfer=False):
    """action: 'generate' | 'sim'. -> {'ok': bool, 'log': str, 'wave': str|None}"""
    pdir = Path(pdir).resolve()
    log, wave, ok = [], None, False
    try:
        g = gen.generate(pdir, cfg, tests)
        log.append('Testbench(es) erzeugt: ' + ', '.join(str(t['file'].relative_to(pdir)) for t in g['tbs']))
        if action == 'generate':
            return {'ok': True, 'log': '\n'.join(log), 'wave': None}
        build = pdir / 'build'
        if cfg.get('mode') == 'vunit':
            wave, ok = _vunit(pdir, build, cfg, g, test, log)
        else:
            wave, ok = _plain(pdir, build, cfg, g, test, log)
    except SpecError as e:
        log.append('FEHLER: %s' % e)
        return {'ok': False, 'log': '\n'.join(log), 'wave': None}
    log.append('=> ' + ('ALLE TESTS BESTANDEN' if ok else 'FEHLGESCHLAGEN'))
    if wave and surfer:
        tb = next((t for t in g['tbs'] if t['test'] == test), g['tbs'][-1] if test is None else g['tbs'][0])
        order = tb['order']
        names = order.get(test) or list(order.values())[-1]
        open_surfer(cfg, wave, log, tb['entity'], names)
    return {'ok': ok, 'log': '\n'.join(log), 'wave': str(wave) if wave else None}


def _plain(pdir, build, cfg, g, test, log):
    srcs, warn = project.resolve_sources(pdir, cfg)
    if not srcs:
        raise SpecError("Keine VHDL-Quellen gefunden")
    log.append('Quellen (%d): %s' % (len(srcs), ', '.join(s.name for s in srcs)))
    log += ['Hinweis: ' + w for w in warn]
    (build / 'work').mkdir(parents=True, exist_ok=True)
    (build / 'waves').mkdir(parents=True, exist_ok=True)
    for old in (build / 'waves').glob('*'):
        if old.is_file():
            old.unlink()
    tbs = [t for t in g['tbs'] if test is None or t['test'] == test]
    ok, wave = True, None
    for t in tbs:
        log.append('--- Test: %s ---' % t['test'])
        if _run(['ghdl', '-a', STD, '--workdir=work'] + srcs + [t['file']], build, log):
            return None, False
        if _run(['ghdl', '-e', STD, '--workdir=work', t['entity']], build, log):
            return None, False
        w = build / 'waves' / (t['entity'] + '.ghw')
        rc = _run(['ghdl', '-r', STD, '--workdir=work', t['entity'], '--wave=waves/%s' % w.name], build, log)
        if rc:
            ok = False
        if w.exists():
            wave = w
    return wave, ok


def _vunit(pdir, build, cfg, g, test, log):
    try:
        import vunit  # noqa: F401
    except ImportError:
        raise SpecError("VUnit nicht installiert: pip install vunit_hdl")
    env = dict(os.environ, VUNIT_SIMULATOR='ghdl')
    build.mkdir(parents=True, exist_ok=True)
    out = build / 'vunit_out'
    cmd = [sys.executable, str(g['runpy']), '--gtkwave-fmt', 'ghw', '--output-path', str(out), '-v']
    if test:
        cmd.append('lib.%s.%s' % (g['tbs'][0]['entity'], 'test_' + gen._ident(test)))
    rc = _run(cmd, build, log, env=env)
    waves = sorted(out.glob('**/*.ghw'), key=lambda p: p.stat().st_mtime) if out.exists() else []
    return (waves[-1] if waves else None), rc == 0
