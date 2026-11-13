import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API = "https://text.pollinations.ai/"
MAX_GET_URL = 6000
UPSTREAM_TIMEOUT = 85
HEADERS = {"User-Agent": "prompt-refiner-local/1.0"}


def call_upstream(prompt: str):
    url = API + urllib.parse.quote(prompt, safe="")
    if len(url) <= MAX_GET_URL:
        req = urllib.request.Request(url, headers=HEADERS)
    else:
        body = json.dumps({"messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(API, data=body, headers={**HEADERS, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=UPSTREAM_TIMEOUT) as r:
            return 200, {"text": r.read().decode("utf-8", "replace").strip()}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if e.code in (402, 429):
            m = re.search(r"wait (\d+) second", body)
            return 429, {"error": "Free limit reached (one reply every 45 seconds).", "retry_after": int(m.group(1)) if m else 45}
        return e.code, {"error": f"The text service returned HTTP {e.code}."}
    except (urllib.error.URLError, TimeoutError) as e:
        return 502, {"error": f"Could not reach the text service ({getattr(e, 'reason', e)})."}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self):
        if self.path != "/api/llm":
            return self.send_error(404)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            prompt = json.loads(self.rfile.read(n))["prompt"]
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError
        except (ValueError, KeyError, json.JSONDecodeError):
            return self.reply(400, {"error": "Invalid request."})
        status, payload = call_upstream(prompt)
        self.reply(status, payload)

    def reply(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s\n" % (fmt % args))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5188
    print(f"Say It Better on http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
