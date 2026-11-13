# Say It Better

Turn a rough prompt into a complete one. Paste a prompt and it is checked against seven elements: Role, Goal, Context, Task, Method, Format and Validation. You answer a few quick questions (radio buttons, checkboxes, short text), then get a structured final prompt with a Copy button.

Text generation uses the free [Pollinations](https://text.pollinations.ai) API.

## Run locally

```bash
python3 server.py 5188
```

Open http://127.0.0.1:5188. The local server forwards requests to Pollinations, because that service rejects browser requests coming from `localhost`.

## GitHub Pages

The same files work as a static site. When the page is not served from localhost, the browser calls Pollinations directly and no server is needed.

## Notes

- The free tier allows one reply per 45 seconds per IP. The app shows a countdown and retries automatically.
- Prompts are sent to text.pollinations.ai. Do not paste secrets or personal data.
- Review generated prompts before using them in customer-facing or official material.
