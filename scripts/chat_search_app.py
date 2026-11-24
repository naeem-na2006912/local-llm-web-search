"""
Local chat page with optional web search.

Needs:  pip install flask ddgs requests
Run:    python chat_search_app.py
Open:   http://127.0.0.1:5000

llama-server must already be running on port 8080.
"""

from flask import Flask, request, jsonify, Response
from ddgs import DDGS
import requests

LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"
MAX_HISTORY = 12      # how many recent messages are sent to the model
MAX_RESULTS = 5       # how many search results to fetch
SNIPPET_CHARS = 500   # trim each result so the prompt stays small

app = Flask(__name__)

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Local AI Chat</title>
<style>
  :root { --bg:#ffffff; --fg:#1d1d1f; --user:#e8f0fe; --bot:#f3f3f5; --line:#d8d8dc; --accent:#2b6cb0; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#17181b; --fg:#ececec; --user:#23324d; --bot:#25262b; --line:#3a3b40; --accent:#6aa9ff; }
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--fg); font-family:system-ui, Segoe UI, sans-serif;
         display:flex; flex-direction:column; height:100vh; }
  header { padding:12px 16px; border-bottom:1px solid var(--line); display:flex; gap:12px; align-items:center; }
  header h1 { font-size:16px; margin:0; flex:1; }
  header label { font-size:14px; display:flex; gap:6px; align-items:center; cursor:pointer; }
  button { background:var(--accent); color:#fff; border:0; border-radius:8px; padding:8px 14px; cursor:pointer; font-size:14px; }
  button:disabled { opacity:.5; cursor:default; }
  button.secondary { background:transparent; color:var(--fg); border:1px solid var(--line); }
  #chat { flex:1; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:12px; }
  .msg { max-width:min(760px, 90%); padding:10px 14px; border-radius:12px; white-space:pre-wrap; line-height:1.5; }
  .user { align-self:flex-end; background:var(--user); }
  .assistant { align-self:flex-start; background:var(--bot); }
  .sources { margin-top:10px; padding-top:8px; border-top:1px solid var(--line); font-size:13px; white-space:normal; }
  .sources a { display:block; color:var(--accent); margin-top:3px; word-break:break-all; }
  footer { padding:12px 16px; border-top:1px solid var(--line); display:flex; gap:8px; }
  textarea { flex:1; resize:none; height:48px; padding:10px; border-radius:8px; border:1px solid var(--line);
             background:var(--bg); color:var(--fg); font:inherit; }
</style>
</head>
<body>
<header>
  <h1>Local AI Chat</h1>
  <label><input type="checkbox" id="search" checked> Search the web</label>
  <button class="secondary" id="reset">New chat</button>
</header>
<div id="chat"></div>
<footer>
  <textarea id="input" placeholder="Type a message. Enter to send, Shift+Enter for a new line."></textarea>
  <button id="send">Send</button>
</footer>
<script>
const chat = document.getElementById('chat');
const input = document.getElementById('input');
const sendBtn = document.getElementById('send');
const searchBox = document.getElementById('search');
let history = [];

function addMsg(role, text, sources) {
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.textContent = text;
  if (sources && sources.length) {
    const box = document.createElement('div');
    box.className = 'sources';
    box.appendChild(document.createTextNode('Sources:'));
    sources.forEach((src, i) => {
      if (!/^https?:\\/\\//.test(src.url)) return;
      const a = document.createElement('a');
      a.href = src.url;
      a.target = '_blank';
      a.rel = 'noopener';
      a.textContent = (i + 1) + '. ' + src.title;
      box.appendChild(a);
    });
    div.appendChild(box);
  }
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

async function send() {
  const text = input.value.trim();
  if (!text || sendBtn.disabled) return;
  input.value = '';
  addMsg('user', text);
  history.push({ role: 'user', content: text });
  const wait = addMsg('assistant', searchBox.checked ? 'Searching the web and thinking...' : 'Thinking...');
  sendBtn.disabled = true;
  try {
    const r = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: history, search: searchBox.checked })
    });
    const data = await r.json();
    wait.remove();
    if (data.error) {
      addMsg('assistant', 'Error: ' + data.error);
      history.pop();
    } else {
      addMsg('assistant', data.reply, data.sources);
      history.push({ role: 'assistant', content: data.reply });
    }
  } catch (e) {
    wait.remove();
    addMsg('assistant', 'Error: ' + e);
    history.pop();
  }
  sendBtn.disabled = false;
  input.focus();
}

sendBtn.addEventListener('click', send);
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});
document.getElementById('reset').addEventListener('click', () => { history = []; chat.innerHTML = ''; });
</script>
</body>
</html>
"""


@app.get("/")
def index():
    return Response(PAGE, mimetype="text/html")


@app.post("/chat")
def chat():
    data = request.get_json(force=True)
    messages = data.get("messages", [])[-MAX_HISTORY:]
    use_search = bool(data.get("search"))
    if not messages:
        return jsonify(error="No message received.")

    sources = []
    model_messages = [{"role": "system", "content": "You are a helpful assistant."}]
    model_messages += [dict(m) for m in messages]

    if use_search:
        question = messages[-1]["content"]
        try:
            results = DDGS().text(question, max_results=MAX_RESULTS)
        except Exception as e:
            return jsonify(error=f"Web search failed: {e}")

        blocks = []
        for i, r in enumerate(results, start=1):
            title = r.get("title", "")
            body = (r.get("body") or "")[:SNIPPET_CHARS]
            url = r.get("href", "")
            blocks.append(f"[{i}] {title}\n{body}")
            sources.append({"title": title, "url": url})

        if blocks:
            # Search text is added only to this request, not saved in the history.
            model_messages[-1]["content"] = (
                "Use the web search results below to answer the question. "
                "If they do not contain the answer, say so. "
                "Refer to sources by number like [1].\n\n"
                "Search results:\n" + "\n\n".join(blocks) +
                "\n\nQuestion: " + question
            )

    try:
        r = requests.post(LLAMA_URL, json={"messages": model_messages}, timeout=600)
        r.raise_for_status()
        reply = r.json()["choices"][0]["message"]["content"]
    except requests.exceptions.ConnectionError:
        return jsonify(error="Cannot reach llama-server on port 8080. Is it running?")
    except Exception as e:
        return jsonify(error=f"Model request failed: {e}")

    return jsonify(reply=reply, sources=sources)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
