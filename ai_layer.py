# ai_layer.py -- Gemini call that (1) finds a working model from YOUR key, (2) asks for JSON,
# (3) verifies every phrase really exists in the article (no hallucinated flags).
import json, re, requests

BASE = "https://generativelanguage.googleapis.com/v1beta"


def pick_model(api_key):
    r = requests.get(f"{BASE}/models", params={"key": api_key, "pageSize": 200}, timeout=20)
    r.raise_for_status()
    names = [m["name"].split("/")[-1] for m in r.json().get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    def rank(n):
        s = n.lower()
        return (0 if "flash" in s else 1 if "pro" in s else 2, 0 if "lite" not in s else 1, 0 if "preview" not in s and "exp" not in s else 1, n)
    names = sorted(names, key=rank)
    names = [n for n in names if not any(x in n.lower() for x in ("tts", "image", "embed", "live", "audio", "vision", "robotics"))]
    if not names:
        raise RuntimeError("No text model available for this key")
    return names[0]


PROMPT = """You are a strict news editor. Read the article ({lang}) and find wording where the JOURNALIST'S OWN VOICE
shows subjective judgment, emotional framing, opinion stated as fact, unsupported predictions, loaded labels, or
claims with no named source. Ignore text inside quotation marks. Also note when an opinion is attributed to a source
that is vague (e.g. "experts say", "many believe").

Return ONLY a JSON array (no markdown). Each item:
{{"phrase": "<EXACT words copied from the article, 1-8 words>",
  "category": "<Emotional language | Subjective judgment | Opinion as fact | Exaggeration / framing | Prediction as fact | Vague attribution | Missing evidence>",
  "reason": "<one sentence>",
  "missing_evidence": "<what the writer must add: a number, a named source, a date...>",
  "suggestion": "<neutral wording that adds NO new facts>"}}
If the article is genuinely neutral return [].

ARTICLE:
{text}"""


def ask_gemini(text, api_key, language="english"):
    model = pick_model(api_key)
    body = {"contents": [{"parts": [{"text": PROMPT.format(lang=language, text=text)}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}}
    r = requests.post(f"{BASE}/models/{model}:generateContent", params={"key": api_key}, json=body, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"{model}: HTTP {r.status_code} {r.text[:200]}")
    raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    return model, parse_items(raw)


def parse_items(raw):
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    data = json.loads(raw)
    if isinstance(data, dict):
        data = data.get("items") or data.get("flags") or []
    return [d for d in data if isinstance(d, dict) and d.get("phrase")]


def verify_items(items, text, quote_spans, rule_flags):
    """Keep only phrases that exist in the text, outside quotes, and not already found by rules."""
    out, taken = [], [(f["Start"], f["End"]) for f in rule_flags]
    for it in items:
        ph = it["phrase"].strip()
        for m in re.finditer(re.escape(ph), text, flags=re.IGNORECASE):
            s, e = m.start(), m.end()
            if any(qs <= s < qe for qs, qe in quote_spans):
                continue
            if any(s < te and e > ts for ts, te in taken):
                continue
            taken.append((s, e))
            out.append({"Phrase": text[s:e], "Category": it.get("category", "Contextual"), "Severity": 2,
                        "Voice": "Journalist's own voice", "Reason": it.get("reason", ""),
                        "Suggestion": it.get("suggestion", ""), "Missing": it.get("missing_evidence", ""),
                        "Source": "Gemini (verified in text)", "Start": s, "End": e})
            break
    return out 