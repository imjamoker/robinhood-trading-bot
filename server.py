#!/usr/bin/env python3
"""Local dashboard server — serves the trading dashboard and exposes a /run endpoint."""

import os, subprocess, json, secrets, threading
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, Response

BASE   = os.path.dirname(os.path.abspath(__file__))
DOCS   = os.path.join(BASE, 'docs')
LOGS   = os.path.join(BASE, 'logs')
TOKEN_FILE = os.path.expanduser('~/.robinhood_token')

app = Flask(__name__)

# ── Auth token ────────────────────────────────────────────────────────────────

def get_token():
    if os.path.exists(TOKEN_FILE):
        return open(TOKEN_FILE).read().strip()
    token = secrets.token_urlsafe(24)
    with open(TOKEN_FILE, 'w') as f:
        f.write(token)
    return token

def authorized():
    token = get_token()
    if request.headers.get('X-Token') == token:
        return True
    try:
        body = request.get_json(silent=True) or {}
        if body.get('token') == token:
            return True
    except Exception:
        pass
    return False

# ── Static dashboard ──────────────────────────────────────────────────────────

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not authorized():
            return jsonify({'error': 'unauthorized'}), 401
        return fn(*args, **kwargs)
    return wrapper

@app.route('/')
def index():
    return send_from_directory(DOCS, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(DOCS, filename)

# ── API ───────────────────────────────────────────────────────────────────────

@app.after_request
def cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'X-Token,Content-Type'
    return resp

@app.route('/api/signals')
@require_auth
def signals():
    path = os.path.join(LOGS, 'latest_signals.json')
    if not os.path.exists(path):
        return jsonify({}), 404
    return Response(open(path).read(), mimetype='application/json')

@app.route('/api/positions')
@require_auth
def positions():
    path = os.path.join(DOCS, 'positions.json')
    if not os.path.exists(path):
        return jsonify({'buying_power': 100, 'positions': []}), 200
    return Response(open(path).read(), mimetype='application/json')

@app.route('/api/tradelog')
@require_auth
def tradelog():
    path = os.path.join(LOGS, 'trade_log.md')
    if not os.path.exists(path):
        return '', 404
    return Response(open(path).read(), mimetype='text/plain')

_run_state = {'status': 'idle', 'started': None, 'output': ''}

@app.route('/api/status')
@require_auth
def status():
    log = os.path.join(LOGS, 'auto_run.log')
    last_line = ''
    if os.path.exists(log):
        lines = [l.strip() for l in open(log).readlines() if l.strip()]
        last_line = lines[-1] if lines else ''
    return jsonify({**_run_state, 'last_log_line': last_line})

@app.route('/api/tunnel')
@require_auth
def tunnel():
    path = os.path.join(LOGS, 'tunnel_url.txt')
    if os.path.exists(path):
        url = open(path).read().strip()
        return jsonify({'url': url})
    return jsonify({'url': None})

@app.route('/api/run', methods=['POST', 'OPTIONS'])
def run():
    if request.method == 'OPTIONS':
        return '', 204
    if not authorized():
        return jsonify({'error': 'unauthorized'}), 401
    if _run_state['status'] == 'running':
        return jsonify({'error': 'already running'}), 409

    def execute():
        _run_state['status'] = 'running'
        _run_state['started'] = datetime.utcnow().isoformat()
        _run_state['output'] = ''
        try:
            result = subprocess.run(
                ['/bin/bash', os.path.join(BASE, 'run_trade.sh')],
                capture_output=True, text=True, timeout=300
            )
            _run_state['output'] = result.stdout + result.stderr
            _run_state['status'] = 'success' if result.returncode == 0 else 'error'
        except Exception as e:
            _run_state['output'] = str(e)
            _run_state['status'] = 'error'

    threading.Thread(target=execute, daemon=True).start()
    return jsonify({'status': 'started'})

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    token = get_token()
    print()
    print('━' * 52)
    print('  Robinhood Trading Dashboard')
    print('  http://localhost:5001')
    print()
    print(f'  Password: {token}')
    print('━' * 52)
    print()
    app.run(host='127.0.0.1', port=5001, debug=False)
