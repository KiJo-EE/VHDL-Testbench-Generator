"""Lokaler Web-Server fuer die GUI (nur Standardbibliothek)."""
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import gen, project, runner
from .core import SpecError, build_wave

STATIC = Path(__file__).parent / 'static'


def make_handler(start_dir):
    ctx = {'pdir': Path(start_dir).resolve()}      # aktueller Testbench-Ordner (in der GUI aenderbar)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, obj, code=200, ctype='application/json'):
            data = obj if isinstance(obj, bytes) else json.dumps(obj).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', ctype + '; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path in ('/', '/index.html'):
                self._send((STATIC / 'index.html').read_bytes(), ctype='text/html')
            elif self.path == '/api/project':
                cfg, tests = project.load(ctx['pdir'])
                self._send({'config': cfg, 'tests': tests, 'dir': str(ctx['pdir'])})
            else:
                self._send({'error': 'not found'}, 404)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
            try:
                self._send(self.route(self.path, body))
            except SpecError as e:
                self._send({'ok': False, 'error': str(e)})
            except Exception as e:  # noqa: BLE001
                self._send({'ok': False, 'error': 'Interner Fehler: %r' % e}, 500)

        def route(self, path, b):
            pdir = ctx['pdir']
            cfg = b.get('config', {})
            if path == '/api/save':
                project.save(pdir, cfg, b['tests'])
                return {'ok': True}
            if path == '/api/probe':        # liegt im Ordner schon ein Projekt?
                d = Path(b['dir']).expanduser()
                if not d.is_absolute():
                    raise SpecError('Bitte einen absoluten Pfad angeben')
                n = len(project.load(d)[1]) if project.exists(d) else 0
                return {'ok': True, 'exists': d.is_dir(), 'has_project': project.exists(d), 'tests': n}
            if path == '/api/chdir':        # Speicherort wechseln, optional vorhandenes Projekt laden
                d = Path(b['dir']).expanduser()
                if not d.is_absolute():
                    raise SpecError('Bitte einen absoluten Pfad angeben')
                d.mkdir(parents=True, exist_ok=True)
                d = d.resolve()
                if b.get('load') and project.exists(d):
                    ncfg, tests = project.load(d)
                    ctx['pdir'] = d
                    return {'ok': True, 'dir': str(d), 'config': ncfg, 'tests': tests, 'loaded': True}
                ncfg = project.absolutize(pdir, cfg)      # Pfade bleiben gueltig, auch wenn der Ordner wechselt
                ctx['pdir'] = d
                return {'ok': True, 'dir': str(d), 'config': ncfg, 'loaded': False}
            if path == '/api/browse':
                return {'ok': True, **project.browse(b.get('path', ''), b.get('mode', 'file'))}
            if path == '/api/resolve':
                ents = project.entities_of(pdir, cfg)
                ent = project.pick_entity(ents, cfg.get('entity')) or project.pick_entity(ents, '')
                files, warn = project.resolve_sources(pdir, cfg)
                return {'ok': True, 'entities': [e['name'] for e in ents.values()],
                        'entity': ent['name'] if ent else '', 'files': [str(f) for f in files],
                        'warnings': warn, 'dir': str(pdir)}
            if path == '/api/render':
                ent = project.find_entity(pdir, cfg)
                w = build_wave(b['text'], project.ports_dict(ent), cfg.get('clock', ''), strict=False)
                for s in w['signals']:
                    for c in s['cells']:
                        c.pop('num', None)
                return {'ok': True, 'wave': w, 'entity_found': bool(ent)}
            if path == '/api/skeleton':
                ent = project.find_entity(pdir, cfg)
                if not ent:
                    raise SpecError("Entity nicht gefunden - Top-Datei und Entity pruefen")
                return {'ok': True, 'text': gen.skeleton(ent, cfg.get('clock', ''))}
            if path == '/api/run':
                return runner.execute(pdir, cfg, b['tests'], b.get('action', 'sim'), b.get('test'),
                                      bool(b.get('surfer')))
            raise SpecError('unbekannter Endpunkt')

    return H


def serve(pdir, port=0, open_browser=True):
    srv = ThreadingHTTPServer(('127.0.0.1', port), make_handler(pdir))
    url = 'http://127.0.0.1:%d/' % srv.server_address[1]
    print('WaveTB laeuft auf %s  (Ordner: %s)  - Strg+C zum Beenden' % (url, Path(pdir).resolve()))
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
