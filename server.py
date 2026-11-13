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
REASONING_EFFORT = "low"
MAX_TOKENS = 16000
UPSTREAM_TIMEOUT = 110
HEADERS = {"User-Agent": "prompt-refiner-local/1.0"}


TOKEN_LIMIT_MSG = "The model ran out of output space while reasoning. Try again, or shorten your prompt."


def upstream_error(body: str):
    if "output_token_limit_exceeded" in body:
        return TOKEN_LIMIT_MSG
    return None


def call_upstream(prompt: str):
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "reasoning_effort": REASONING_EFFORT,
        "max_tokens": MAX_TOKENS,
    }
    req = urllib.request.Request(
        API, data=json.dumps(payload).encode(), headers={**HEADERS, "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=UPSTREAM_TIMEOUT) as r:
            text = r.read().decode("utf-8", "replace").strip()
            if text.startswith('{"success":false') or text.startswith('{"success": false'):
                return 502, {"error": upstream_error(text) or "The text service reported an error."}
            return 200, {"text": text}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if e.code in (402, 429):
            m = re.search(r"wait (\d+) second", body)
            return 429, {"error": "Free limit reached (one reply every 45 seconds).", "retry_after": int(m.group(1)) if m else 45}
        return e.code, {"error": upstream_error(body) or f"The text service returned HTTP {e.code}."}
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
