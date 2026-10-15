# core_engine.py
import re
from lexicon import RULES, ATTRIBUTION_CUES

# Quotes: straight "..." and curly “...” / ‘...’ / Hindi-style. Straight single quote = apostrophe, ignored.
QUOTE_PATTERN = re.compile(r'"[^"\n]*"|“[^”]*”|‘[^’]*’')
DEV = "ऀ-ॿ"
WORD = rf"[\w{DEV}]"
SENT_SPLIT = re.compile(r"(?<=[.!?।])\s+|\n+")


def find_quote_spans(text):
    return [(m.start(), m.end()) for m in QUOTE_PATTERN.finditer(text)]


def mask_quotes(text):
    """Replace quotes with spaces of equal length so positions stay valid."""
    return QUOTE_PATTERN.sub(lambda m: " " * len(m.group()), text)


def sentence_spans(text):
    spans, last = [], 0
    for m in SENT_SPLIT.finditer(text):
        spans.append((last, m.start()))
        last = m.end()
    spans.append((last, len(text)))
    return [(s, e) for s, e in spans if e > s]


def is_attributed(sentence_text, flag_start_in_sentence, language):
    """True if an attribution cue appears in the same sentence BEFORE the flagged word."""
    before = sentence_text[:flag_start_in_sentence]
    for cue in ATTRIBUTION_CUES.get(language, []):
        if re.search(rf"(?<!{WORD}){cue}(?!{WORD})", before, flags=re.IGNORECASE):
            return True
    return False


def scan_for_bias(text, language="english"):
    """Returns (flags, quotes). Each flag has position, category, severity, reason, suggestion, voice."""
    language = language if language in RULES else "english"
    quotes = [text[s:e] for s, e in find_quote_spans(text)]
    safe = mask_quotes(text)
    sents = sentence_spans(text)

    found = []
    for regex, cat, sev, reason, sugg in RULES[language]:
        pat = re.compile(rf"(?<!{WORD})(?:{regex})(?!{WORD})", re.IGNORECASE)
        for m in pat.finditer(safe):
            found.append((m.start(), m.end(), cat, sev, reason, sugg))

    # remove overlaps: keep longer match, then higher severity
    found.sort(key=lambda f: (f[0], -(f[1] - f[0]), -f[3]))
    flags, last_end = [], -1
    for s, e, cat, sev, reason, sugg in found:
        if s < last_end:
            continue
        last_end = e
        sent = next(((a, b) for a, b in sents if a <= s < b), (0, len(text)))
        attributed = is_attributed(text[sent[0]:sent[1]], s - sent[0], language)
        flags.append({
            "Phrase": text[s:e], "Category": cat, "Severity": sev,
            "Voice": "Attributed - verify source" if attributed else "Journalist's own voice",
            "Reason": reason, "Suggestion": sugg,
            "Source": "Rule engine", "Start": s, "End": e,
        })
    return flags, quotes


def flagged_rate(flags, text, quotes):
    """Unique flagged phrases (journalist voice only) / words outside quotes * 100."""
    q_words = sum(len(q.split()) for q in quotes)
    total = max(len(text.split()) - q_words, 1)
    uniq = {f["Phrase"].lower() for f in flags if f["Voice"].startswith("Journalist")}
    return len(uniq) / total * 100, len(uniq), total