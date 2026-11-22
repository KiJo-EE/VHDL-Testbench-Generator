import argparse
import sys
from pathlib import Path

from . import project, runner, server
from .core import SpecError


def main():
    ap = argparse.ArgumentParser(prog='wavetb', description='VHDL-Testbenches aus Wellenformen')
    sub = ap.add_subparsers(dest='cmd', required=True)

    g = sub.add_parser('gui', help='Web-GUI starten')
    g.add_argument('dir', nargs='?', default='.')
    g.add_argument('--port', type=int, default=0)
    g.add_argument('--no-browser', action='store_true')

    n = sub.add_parser('new', help='Neuen Testbench-Ordner anlegen')
    n.add_argument('dir')
    n.add_argument('--entity', default='')
    n.add_argument('--top', default='', help='Top-Datei (VHDL), Untermodule werden automatisch gefunden')

    for name, hlp in (('gen', 'Testbenches erzeugen'), ('run', 'Erzeugen + GHDL simulieren')):
        p = sub.add_parser(name, help=hlp)
        p.add_argument('dir', nargs='?', default='.')
        p.add_argument('--test', help='nur diesen Test')
        if name == 'run':
            p.add_argument('--surfer', action='store_true', help='danach Surfer oeffnen')

    a = ap.parse_args()
    if a.cmd == 'gui':
        server.serve(a.dir, a.port, not a.no_browser)
        return 0
    if a.cmd == 'new':
        cfg = dict(project.DEFAULT, entity=a.entity, top=a.top)
        project.save(a.dir, cfg, {})
        print('Projekt angelegt:', Path(a.dir).resolve())
        return 0
    try:
        cfg, tests = project.load(a.dir)
    except OSError as e:
        print(e)
        return 2
    r = runner.execute(a.dir, cfg, tests, 'generate' if a.cmd == 'gen' else 'sim', a.test,
                       getattr(a, 'surfer', False))
    print(r['log'])
    return 0 if r['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
