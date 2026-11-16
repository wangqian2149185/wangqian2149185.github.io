#!/usr/bin/env python3
"""UCSFViewer Pro helper service — lets the browser app run NMRPipe in your working folder.

Usage (in a terminal where NMRPipe is set up, i.e. nmrPipe / bruk2pipe / pipe2ucsf are on PATH):

    python3 ucsfpro_helper.py "/path/to/working_directory"  [--port 8765]

* Standard library only; binds to 127.0.0.1 only.
* Every request must carry the token written to <working_directory>/ucsfpro-helper.json
  (the app reads it from the folder you opened, so only a page with access to that folder can use the helper).
* Paths are relative to the working directory; nothing outside it can be read, written or run.
* Only *.com scripts inside the working directory are run, with csh, in the script's own folder.
* The app's terminal can run NMRPipe tools and a few file utilities (see ALLOWED); pipes | and
  redirection > >> < work, every path must stay inside the working directory, no other shell syntax.
* If nmrPipe is not on PATH, the NMRPipe environment is loaded from ~/.cshrc, ~/.tcshrc, a login zsh
  or nmrInit*.com in the usual install places (or --init FILE / $NMRPIPE_INIT).
On macOS you can double-click "Start UCSFPro helper.command" (same folder as this file) instead.
Stop it with Ctrl+C (the token file is removed).
"""
import glob, json, os, platform, secrets, shlex, shutil, signal, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

VERSION = '1.1'
TOOLS = ['nmrPipe', 'bruk2pipe', 'var2pipe', 'delta2pipe', 'xyz2pipe', 'pipe2xyz', 'pipe2ucsf', 'csh']
# commands the app's terminal may run (anything else is refused)
NMRPIPE_CMDS = ['nmrPipe', 'bruk2pipe', 'var2pipe', 'delta2pipe', 'xyz2pipe', 'pipe2xyz', 'pipe2ucsf', 'ucsf2pipe',
                'showhdr', 'sethdr', 'addNMR', 'ucsfdata']
FILE_CMDS = ['ls', 'cat', 'head', 'tail', 'wc', 'grep', 'diff', 'du', 'file', 'mkdir', 'cp', 'mv', 'echo', 'which']
SCRIPT_SHELLS = ['csh', 'tcsh']
ALLOWED = NMRPIPE_CMDS + FILE_CMDS + SCRIPT_SHELLS
ENV_SOURCE = 'PATH of the shell that started the helper'
MAX_READ = 1 << 30
JOBS = {}
LOCK = threading.Lock()


def inside(root, rel):
    """Resolve rel against root and refuse anything that leaves root (also through symlinks)."""
    if rel is None:
        raise ValueError('missing path')
    rel = rel.replace('\\', '/').lstrip('/')
    full = os.path.realpath(os.path.join(root, rel))
    if os.path.commonpath([full, root]) != root:
        raise PermissionError('path is outside the working folder')
    return full


class Job:
    """Runs one pipeline (list of argv) or a csh script; stdout+stderr are collected line by line."""
    def __init__(self, stages=None, cwd=None, stdin_path=None, stdout_path=None, append=False, script=None):
        self.lines, self.done, self.code, self.procs = [], False, None, []
        if script:
            shell = os.environ.get('UCSFPRO_CSH') or shutil.which('csh') or shutil.which('tcsh')
            if not shell:
                self.lines.append('helper: csh not found'); self.done, self.code = True, 127; return
            stages = [[shell, '-f', os.path.basename(script)]]; cwd = os.path.dirname(script)
        r, w = os.pipe()
        try:
            fin = open(stdin_path, 'rb') if stdin_path else subprocess.DEVNULL
            fout = open(stdout_path, 'ab' if append else 'wb') if stdout_path else None
        except OSError as e:
            os.close(r); os.close(w); self.lines.append('helper: ' + str(e)); self.done, self.code = True, 1; return
        prev = fin
        try:
            for i, argv in enumerate(stages):
                last = i == len(stages) - 1
                out = (fout if fout else w) if last else subprocess.PIPE
                p = subprocess.Popen(argv, cwd=cwd, stdin=prev, stdout=out, stderr=w, start_new_session=True)
                if prev not in (subprocess.DEVNULL, None) and hasattr(prev, 'close') and prev is not fin:
                    prev.close()
                prev = p.stdout; self.procs.append(p)
        except OSError as e:
            self.lines.append('helper: cannot start %s: %s' % (stages[len(self.procs)][0], e)); self.kill()
        finally:
            os.close(w)
            if fin not in (subprocess.DEVNULL, None): fin.close()
            if fout: fout.close()
        threading.Thread(target=self._pump, args=(r,), daemon=True).start()

    def _pump(self, r):
        import codecs
        dec = codecs.getincrementaldecoder('utf-8')('replace')
        with os.fdopen(r, 'rb') as fh:
            buf = ''
            while True:
                raw = os.read(fh.fileno(), 65536)
                if not raw:
                    break
                chunk = dec.decode(raw)
                buf += chunk.replace('\r\n', '\n')
                parts = buf.split('\n'); buf = parts.pop()
                # NMRPipe progress uses \r; keep only the last state of such a line
                with LOCK:
                    self.lines.extend(x.rsplit('\r', 1)[-1] for x in parts)
            if buf:
                with LOCK:
                    self.lines.append(buf.rsplit('\r', 1)[-1])
        codes = [p.wait() for p in self.procs]
        self.code = codes[-1] if codes else (self.code if self.code is not None else 1)
        self.done = True

    def kill(self):
        for p in self.procs:
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except (OSError, ProcessLookupError):
                pass


def rel_of(root, full):
    r = os.path.relpath(full, root).replace(os.sep, '/')
    return '' if r == '.' else r


def parse_command(root, cwd, line):
    """Turn one terminal line into a checked pipeline. Raises ValueError / PermissionError with a message for the user."""
    line = line.replace('\\\n', ' ').strip()
    if not line:
        raise ValueError('empty command')
    if '\n' in line:
        raise ValueError('one command per line')
    # no shell is involved: $VAR, $(…) and backticks are passed on literally, never expanded or run
    lx = shlex.shlex(line, posix=True, punctuation_chars='|&;<>()')
    lx.whitespace_split = True; lx.commenters = ''
    toks = list(lx)
    # stderr is always shown: drop 2>&1 / >& forms of it
    clean, i = [], 0
    while i < len(toks):
        if toks[i] == '2' and i + 2 < len(toks) and toks[i + 1] == '>&' and toks[i + 2] == '1':
            i += 3; continue
        clean.append(toks[i]); i += 1
    toks = clean
    stages, cur, stdin_path, stdout_path, append = [], [], None, None, False
    i = 0
    while i < len(toks):
        t = toks[i]
        if t == '|':
            if not cur: raise ValueError('empty pipeline stage')
            stages.append(cur); cur = []
        elif t in ('>', '>>', '<'):
            if i + 1 >= len(toks): raise ValueError('missing file after ' + t)
            f = toks[i + 1]
            if os.path.isabs(f) or f.startswith('~'):
                raise PermissionError('absolute paths are not allowed: ' + f)
            target = os.path.realpath(os.path.join(cwd, f))
            if os.path.commonpath([target, root]) != root:
                raise PermissionError('path leaves the working folder: ' + f)
            if t != '<' and target.endswith('.com'):
                raise PermissionError('the terminal cannot write *.com scripts (they run without the command limits); the app writes them')
            if t == '<': stdin_path = target
            else: stdout_path, append = target, t == '>>'
            i += 1
        elif t in ('&', '&&', '||', ';', ';;', '(', ')', '>&', '>|', '<<', '|&'):
            raise ValueError("'%s' is not supported — one command (with | pipes) per line" % t)
        else:
            cur.append(t)
        i += 1
    if cur: stages.append(cur)
    if not stages: raise ValueError('nothing to run')
    checked = []
    for k, argv in enumerate(stages):
        cmd = argv[0]
        is_script = cmd.endswith('.com')
        if is_script:
            argv = ['csh', cmd] + argv[1:]; cmd = 'csh'
        if '/' in cmd or cmd not in ALLOWED:
            raise PermissionError("'%s' is not allowed. Allowed: %s; csh/tcsh only for *.com scripts in the working folder" % (argv[0], ', '.join(NMRPIPE_CMDS + FILE_CMDS)))
        args = []
        for a in argv[1:]:
            if any(c in a for c in '*?[') and not a.startswith('-'):
                hits = sorted(glob.glob(os.path.join(cwd, a)))
                args.extend([os.path.relpath(h, cwd) for h in hits] if hits else [a])
            else:
                args.append(a)
        for a in args:
            if a.startswith('~'):
                raise PermissionError('~ paths are not allowed: ' + a)
            if os.path.isabs(a):
                raise PermissionError('absolute paths are not allowed: ' + a)
            if a.startswith('-'):
                continue
            j = os.path.join(cwd, a)
            if '/' in a or a in ('.', '..') or os.path.lexists(j):
                full = os.path.realpath(j)
                if os.path.commonpath([full, root]) != root:
                    raise PermissionError('path leaves the working folder: ' + a)
        if cmd in ('cp', 'mv'):
            names = [a for a in args if not a.startswith('-')]
            if len(names) >= 2 and names[-1].endswith('.com') and any(not n.endswith('.com') for n in names[:-1]):
                raise PermissionError('the terminal cannot create *.com scripts (they run without the command limits); the app writes them')
        if cmd in SCRIPT_SHELLS:
            flags = [a for a in args if a.startswith('-')]; rest = [a for a in args if not a.startswith('-')]
            if any(f not in ('-f', '-x', '-v', '-n', '-e') for f in flags):
                raise PermissionError('csh options allowed: -f -x -v -n -e')
            if not rest or not rest[0].endswith('.com') or not os.path.isfile(os.path.join(cwd, rest[0])):
                raise PermissionError('csh/tcsh can only run an existing *.com script in the working folder')
            shell = os.environ.get('UCSFPRO_CSH') or shutil.which(cmd) or shutil.which('csh') or shutil.which('tcsh')
            if not shell:
                raise ValueError('csh not found')
            exe = [shell] + (['-f'] if '-f' not in flags else []) + flags + rest
        else:
            path = shutil.which(cmd)
            if not path:
                raise ValueError("'%s' not found on PATH%s" % (cmd, ' (NMRPipe environment not loaded?)' if cmd in NMRPIPE_CMDS else ''))
            exe = [path] + args
        checked.append(exe)
    return checked, stdin_path, stdout_path, append


def load_nmrpipe_env(init=None):
    """Make nmrPipe reachable: if it is not on PATH, import the environment of the user's NMRPipe setup."""
    global ENV_SOURCE
    if shutil.which('nmrPipe'):
        return ENV_SOURCE
    home = os.path.expanduser('~')
    csh = shutil.which('csh') or shutil.which('tcsh')
    tries = []
    for f in [init, os.environ.get('NMRPIPE_INIT')]:
        if f: tries.append(('csh', os.path.expanduser(f)))
    tries += [('csh', os.path.join(home, '.cshrc')), ('csh', os.path.join(home, '.tcshrc')), ('zsh', None), ('bash', None)]
    sysname = 'mac' if platform.system() == 'Darwin' else 'linux'
    for base in [os.path.join(home, d) for d in ('nmrpipe', 'NMRPipe', 'nmr', 'pipe', 'Applications/nmrpipe')] + ['/opt/nmrpipe', '/usr/local/nmrpipe', '/Applications/nmrpipe', '/opt/NMRPipe']:
        inits = sorted(glob.glob(os.path.join(base, 'com', 'nmrInit.*.com')))
        arm = platform.machine().lower() in ('arm64', 'aarch64')
        # Apple Silicon → *arm64* init first; Intel → the plain 64-bit one
        inits.sort(key=lambda p: (sysname not in os.path.basename(p), ('arm64' in os.path.basename(p)) != arm, 'mac11' not in p, p))
        tries += [('csh', p) for p in inits[:2]]
    for kind, path in tries:
        if kind == 'csh' and (not csh or not path or not os.path.isfile(path)):
            continue
        if kind == 'zsh' and not shutil.which('zsh'):
            continue
        try:
            if kind == 'csh':
                argv = [csh, '-f', '-c', 'source "$UCSFPRO_RC" >& /dev/null; env']
            else:
                argv = [shutil.which(kind) or kind, '-l', '-c', 'env']
            env = dict(os.environ, UCSFPRO_RC=path or '')
            out = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=15, env=env, errors='replace').stdout
        except (OSError, subprocess.SubprocessError):
            continue
        new = {}
        for ln in out.splitlines():
            k, eq, v = ln.partition('=')
            if eq and k.replace('_', 'a').isalnum() and not k[0].isdigit():
                new[k] = v
        if 'PATH' in new and shutil.which('nmrPipe', path=new['PATH']):
            for k, v in new.items():
                if k not in ('PWD', 'OLDPWD', 'SHLVL', '_', 'UCSFPRO_RC', 'TERM_SESSION_ID'):
                    os.environ[k] = v
            ENV_SOURCE = path if path else 'login ' + kind
            return ENV_SOURCE
    ENV_SOURCE = 'not found'
    return ENV_SOURCE


def make_handler(root, token):
    class H(BaseHTTPRequestHandler):
        server_version = 'ucsfpro-helper/' + VERSION

        def log_message(self, fmt, *a):
            sys.stderr.write('[helper] ' + (fmt % a) + '\n')

        def cors(self):
            origin = self.headers.get('Origin')
            # file:// pages send "null"; a local test server sends http://127.0.0.1:<port> or http://localhost:<port>
            if origin and (origin == 'null' or origin.startswith('http://127.0.0.1') or origin.startswith('http://localhost')):
                self.send_header('Access-Control-Allow-Origin', origin)
                self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Headers', 'X-UCSFPro-Token, Content-Type')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Private-Network', 'true')

        def reply(self, code, body, ctype='application/json'):
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode()
            elif isinstance(body, str):
                body = body.encode(); ctype = 'text/plain; charset=utf-8'
            self.send_response(code); self.cors()
            self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body))); self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self.send_response(204); self.cors(); self.send_header('Content-Length', '0'); self.end_headers()

        def authorised(self):
            if not secrets.compare_digest(self.headers.get('X-UCSFPro-Token', ''), token):
                self.reply(403, 'bad or missing token'); return False
            return True

        def do_GET(self):
            if not self.authorised():
                return
            u = urlparse(self.path); q = parse_qs(u.query)
            try:
                if u.path == '/ping':
                    return self.reply(200, {'version': VERSION, 'root': os.path.basename(root), 'rootPath': root, 'tools': {t: bool(shutil.which(t)) for t in TOOLS},
                                            'env': ENV_SOURCE, 'allowed': ALLOWED, 'exec': True})
                if u.path == '/list':
                    out = []
                    for d, dirs, files in os.walk(root):
                        dirs[:] = [x for x in dirs if not x.startswith('.')]
                        if d[len(root):].count(os.sep) > 6:
                            continue
                        for f in files:
                            p = os.path.join(d, f); out.append({'path': os.path.relpath(p, root).replace(os.sep, '/'), 'size': os.path.getsize(p)})
                            if len(out) > 40000:
                                break
                    return self.reply(200, out)
                if u.path == '/read':
                    p = inside(root, q.get('path', [None])[0])
                    if not os.path.isfile(p):
                        return self.reply(404, 'no such file')
                    if os.path.getsize(p) > MAX_READ:
                        return self.reply(413, 'file too large')
                    with open(p, 'rb') as fh:
                        return self.reply(200, fh.read(), 'application/octet-stream')
                if u.path == '/job':
                    j = JOBS.get(q.get('id', [''])[0])
                    if not j:
                        return self.reply(404, 'no such job')
                    a = int(q.get('from', ['0'])[0])
                    with LOCK:
                        lines = j.lines[a:a + 2000]
                    return self.reply(200, {'lines': lines, 'done': j.done and a + len(lines) >= len(j.lines), 'code': j.code})
                return self.reply(404, 'unknown endpoint')
            except PermissionError as e:
                return self.reply(403, str(e))
            except Exception as e:
                return self.reply(400, str(e))


        def exec_line(self, root, req):

            cwd = inside(root, req.get('cwd') or '')
            if not os.path.isdir(cwd):
                raise ValueError('no such folder: ' + (req.get('cwd') or '.'))
            line = (req.get('cmd') or '').strip()
            if line == 'cd' or line.startswith('cd '):
                arg = line[2:].strip()
                if arg in ('', '~', '/'):
                    return self.reply(200, {'cwd': ''})
                if os.path.isabs(arg) or arg.startswith('~'):
                    raise PermissionError('absolute paths are not allowed: ' + arg)
                a = shlex.split(arg)[0] if arg else '.'
                d = os.path.realpath(os.path.join(cwd, a))
                if os.path.commonpath([d, root]) != root:
                    raise PermissionError('path leaves the working folder: ' + a)
                if not os.path.isdir(d):
                    raise ValueError('cd: no such folder: ' + a)
                return self.reply(200, {'cwd': rel_of(root, d)})
            stages, sin, sout, app = parse_command(root, cwd, line)
            jid = secrets.token_hex(8); JOBS[jid] = Job(stages, cwd, sin, sout, app)
            return self.reply(200, {'id': jid, 'cwd': rel_of(root, cwd)})

        def do_POST(self):
            if not self.authorised():
                return
            u = urlparse(self.path); q = parse_qs(u.query)
            n = int(self.headers.get('Content-Length') or 0)
            body = self.rfile.read(n) if n else b''
            try:
                if u.path == '/write':
                    p = inside(root, q.get('path', [None])[0])
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    with open(p, 'wb') as fh:
                        fh.write(body)
                    return self.reply(200, {'ok': True, 'bytes': len(body)})
                if u.path == '/run':
                    rel = json.loads(body or b'{}').get('path')
                    p = inside(root, rel)
                    if not p.endswith('.com') or not os.path.isfile(p):
                        return self.reply(400, 'only existing .com scripts inside the working folder can be run')
                    jid = secrets.token_hex(8); JOBS[jid] = Job(script=p)
                    return self.reply(200, {'id': jid})
                if u.path == '/exec':
                    try:
                        return self.exec_line(root, json.loads(body or b'{}'))
                    except (PermissionError, ValueError) as e:   # a refused command is a normal answer for the terminal
                        return self.reply(200, {'error': str(e)})
                if u.path == '/kill':
                    j = JOBS.get(json.loads(body or b'{}').get('id', ''))
                    if not j:
                        return self.reply(404, 'no such job')
                    j.kill(); return self.reply(200, {'ok': True})
                return self.reply(404, 'unknown endpoint')
            except PermissionError as e:
                return self.reply(403, str(e))
            except Exception as e:
                return self.reply(400, str(e))
    return H


def main():
    import argparse
    ap = argparse.ArgumentParser(description='UCSFViewer Pro helper: run NMRPipe for the browser app, inside one working folder.')
    ap.add_argument('folder', help='the working directory (contains fid/, ucsf/, peaks/, seq/, save/)')
    ap.add_argument('--port', type=int, default=8765, help='first port to try (default 8765)')
    ap.add_argument('--init', help='NMRPipe init file to source (e.g. ~/nmrpipe/com/nmrInit.mac11_64.com) if nmrPipe is not on PATH')
    a = ap.parse_args(); port = a.port
    root = os.path.realpath(os.path.expanduser(a.folder))
    if not os.path.isdir(root):
        print('Not a folder:', root); sys.exit(1)
    token = secrets.token_urlsafe(24)
    srv = None
    for p in range(port, port + 20):
        try:
            srv = ThreadingHTTPServer(('127.0.0.1', p), make_handler(root, token)); port = p; break
        except OSError:
            continue
    if not srv:
        print('No free port near', port); sys.exit(1)
    info = os.path.join(root, 'ucsfpro-helper.json')
    with open(info, 'w') as fh:
        json.dump({'port': port, 'token': token, 'started': time.strftime('%Y-%m-%d %H:%M:%S')}, fh)
    try:
        os.chmod(info, 0o600)
    except OSError:
        pass
    src = load_nmrpipe_env(a.init)
    missing = [t for t in TOOLS if not shutil.which(t)]
    print('UCSFViewer Pro helper %s on http://127.0.0.1:%d for %s' % (VERSION, port, root))
    print('NMRPipe tools missing from PATH: ' + ', '.join(missing) if missing else 'NMRPipe tools found (environment: %s).' % src)
    if 'nmrPipe' in missing:
        print('  -> start it from a terminal where nmrPipe works, or pass --init /path/to/nmrpipe/com/nmrInit.<platform>.com')
    print('Open the working folder in the app (or press "check"). Ctrl+C to stop.')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            os.remove(info)
        except OSError:
            pass


if __name__ == '__main__':
    main()
