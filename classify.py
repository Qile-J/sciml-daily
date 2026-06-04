# classify.py
import json
import logging
import os
import time
import config

# We disable thinking below for speed; this also silences the SDK's benign
# "non-text parts in the response" warning (defensive — keeps logs clean either way).
logging.getLogger("google_genai.types").setLevel(logging.ERROR)

def load_instruction():
    """The fixed system-instruction block from prompts/classify.md."""
    t = config.PROMPT.read_text(encoding="utf-8")
    block = t[t.index("## SYSTEM INSTRUCTION"):t.index("## USER MESSAGE")]
    return block.split("\n", 1)[1].strip()           # drop the header line

def build_message(batch):
    lines = ['Classify each paper. Return a JSON array, one object per paper, '
             'in the same order, each with its "id".', ""]
    for i, p in enumerate(batch, 1):
        lines += [f"[{i}]", f"Title: {p['title']}", f"Abstract: {p['abstract']}",
                  f"Categories: {', '.join(p['categories'])}", ""]
    return "\n".join(lines)

def _apply(item, p):
    valid = set(config.TAGS)
    in_scope = bool(item.get("in_scope"))
    tags = [t for t in (item.get("tags") or []) if t in valid] if in_scope else []
    return {**p, "in_scope": in_scope, "tags": tags, "reason": str(item.get("reason", ""))[:300]}

def classify(papers, generate, instruction=None, sleep=time.sleep):
    """Return classified papers (in + out) for as many as the request cap allows.
    Papers we never reach simply aren't returned — they stay unseen and retry next run."""
    instruction = instruction or load_instruction()
    done, used = [], 0
    for i in range(0, len(papers), config.BATCH_SIZE):
        if used >= config.MAX_REQUESTS:
            print(f"[classify] request cap hit; deferring {len(papers) - i} papers")
            break
        batch = papers[i:i + config.BATCH_SIZE]
        try:
            data = json.loads(generate(instruction, build_message(batch)))
            by_id = {int(x["id"]): x for x in data if "id" in x}
        except Exception as e:                        # bad JSON / API error: skip, retry next run
            print(f"[classify] batch failed: {e}")
            used += 1
            sleep(config.REQUEST_DELAY)
            continue
        for j, p in enumerate(batch, 1):
            if j in by_id:
                done.append(_apply(by_id[j], p))
        used += 1
        sleep(config.REQUEST_DELAY)
    return done

def gemini_generate(instruction, message):
    """Real Gemini call (not exercised by unit tests)."""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model=config.GEMINI_MODEL, contents=message,
        config=types.GenerateContentConfig(
            system_instruction=instruction,
            response_mime_type="application/json", temperature=0.0,
            thinking_config=types.ThinkingConfig(thinking_budget=0)))  # no thinking: faster
    return resp.text
