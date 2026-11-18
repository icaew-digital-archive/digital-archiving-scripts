"""One-off: authorise the Gmail account and save gmail_token.json for python_emailer.py.

Run on a machine with a browser (not the droplet):
    python3 gmail_authorise.py client_secret.json
Then copy gmail_token.json next to python_emailer.py on the droplet.
"""
import json
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

SCOPE = 'https://www.googleapis.com/auth/gmail.send'  # send-only; can't read the mailbox

# Load the Desktop app client downloaded from Google Cloud Console
with open(sys.argv[1] if len(sys.argv) > 1 else 'client_secret.json') as f:
    client = json.load(f)['installed']

# Local server to catch Google's redirect back with the authorisation code
captured = {}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        captured.update(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Authorised - you can close this tab.')

    def log_message(self, *args):
        pass

server = HTTPServer(('127.0.0.1', 0), Handler)
redirect_uri = f'http://localhost:{server.server_port}'  # must match the client's registered redirect_uris
state = secrets.token_urlsafe(16)

auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
    'client_id': client['client_id'],
    'redirect_uri': redirect_uri,
    'response_type': 'code',
    'scope': SCOPE,
    'access_type': 'offline',  # ask for a refresh token
    'prompt': 'consent',       # force a new refresh token even if previously authorised
    'state': state,
})
print('Opening browser. If it does not open, visit:\n' + auth_url, flush=True)
webbrowser.open(auth_url)
while 'code' not in captured and 'error' not in captured:
    server.handle_request()

if 'error' in captured or captured.get('state', [''])[0] != state:
    sys.exit(f"Authorisation failed: {captured.get('error', ['state mismatch'])[0]}")

# Exchange the code for a refresh token
data = urllib.parse.urlencode({
    'code': captured['code'][0],
    'client_id': client['client_id'],
    'client_secret': client['client_secret'],
    'redirect_uri': redirect_uri,
    'grant_type': 'authorization_code',
}).encode()
with urllib.request.urlopen('https://oauth2.googleapis.com/token', data) as resp:
    tokens = json.load(resp)

if 'refresh_token' not in tokens:
    sys.exit(f'No refresh token returned: {tokens}')

with open('gmail_token.json', 'w') as f:
    json.dump({
        'client_id': client['client_id'],
        'client_secret': client['client_secret'],
        'refresh_token': tokens['refresh_token'],
    }, f, indent=4)
print('Saved gmail_token.json')
