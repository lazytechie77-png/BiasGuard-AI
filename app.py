# ======================================================================
# BiasGuard AI  -  ONE FILE VERSION  (save as app.py)
# Run:  python -m streamlit run app.py
# Pages: 1 Audit  ->  2 Verify  ->  3 Reconstruct
# ======================================================================
import re, json, html, hashlib, datetime
import requests
import pandas as pd
import streamlit as st

# lexicon.py  -- each rule: (regex, category, severity, reason, suggestion)
# severity: 3 = strong, 2 = medium, 1 = mild. Regex is matched case-insensitively
# on whole words, so "slam" also catches slams/slammed via the optional endings.

EMO = "Emotional language"
JUDGE = "Subjective judgment"
CERT = "Unwarranted certainty"
EXAG = "Exaggeration / framing"
PRAISE = "Unsupported praise"
PRED = "Prediction as fact"
GEN = "Overgeneralisation"

ENGLISH_RULES = [
    # --- Emotional / sensational ---
    (r"catastroph(?:e|es|ic)", EMO, 3, "Sensationalist wording.", "Describe the measurable impact, e.g. 'downturn', 'failure'."),
    (r"disastrous(?:ly)?|disaster", EMO, 3, "Strong negative evaluation.", "State the concrete damage or outcome."),
    (r"shock(?:ing|ingly|ed)", EMO, 2, "Tells the reader how to feel.", "State the facts plainly."),
    (r"outrage(?:ous|d)?", EMO, 3, "Emotional framing.", "Say who objected and what they said."),
    (r"horrif(?:ic|ying|ied)|terrifying|appalling|devastating", EMO, 3, "Emotional framing.", "Describe what happened, with figures."),
    (r"chaos|chaotic|mayhem|havoc", EMO, 2, "Dramatic wording.", "Describe the disruption specifically."),
    (r"tragic(?:ally)?|heartbreaking|heart-wrenching", EMO, 2, "Emotional framing.", "State the facts; let readers react."),
    (r"slam(?:s|med|ming)?", EMO, 2, "Sensationalist framing.", "Use 'criticised' or 'opposed'."),
    (r"blast(?:s|ed|ing)?", EMO, 2, "Sensationalist framing.", "Use 'criticised'."),
    (r"lash(?:es|ed|ing)? out", EMO, 2, "Sensationalist framing.", "Use 'criticised' or 'responded'."),
    (r"fume[sd]?|fuming|erupt(?:s|ed)?", EMO, 2, "Emotional framing.", "Report what was said."),
    (r"bombshell|explosive|stunning|jaw-dropping", EMO, 2, "Hype wording.", "State what was announced."),
    (r"crisis|meltdown|collapse[sd]?|plunge[sd]?|plummet(?:s|ed)?|skyrocket(?:s|ed)?|soar(?:s|ed)?", EXAG, 2, "Dramatic verb; may overstate the change.", "Give the actual figure or percentage."),
    # --- Subjective judgment / labels ---
    (r"draconian", JUDGE, 3, "Subjective judgment.", "Use 'strict' or describe the rule."),
    (r"incompetent|inept|clueless|hopeless", JUDGE, 3, "Subjective label.", "Describe the specific failure."),
    (r"irresponsible|reckless(?:ly)?|negligent", JUDGE, 3, "Implies intent / judges conduct.", "Describe the specific action or risk."),
    (r"corrupt|crooked|shady|sleazy", JUDGE, 3, "Accusatory label.", "Cite the allegation, court finding or source."),
    (r"foolish(?:ly)?|stupid(?:ity)?|idiotic|absurd|ridiculous|pathetic|laughable", JUDGE, 3, "Insulting / subjective label.", "Describe the action and attribute any criticism."),
    (r"controversial", JUDGE, 2, "Loaded label.", "Name who disputes it and why."),
    (r"scheme|regime", JUDGE, 2, "Negative connotation.", "Use 'plan', 'proposal' or 'government'."),
    (r"ignor(?:ed|es|ing)", JUDGE, 2, "Implies intent.", "Say what was not addressed."),
    (r"refus(?:ed|es|ing)", JUDGE, 1, "Implies stubbornness.", "Use 'declined' if that is accurate."),
    (r"admit(?:ted|s)?", JUDGE, 2, "Implies guilt.", "Use 'said' or 'acknowledged'."),
    (r"rush(?:ed|ing)", JUDGE, 2, "Subjective judgment of pace.", "Give the actual timeline."),
    (r"botch(?:ed)?|bungl(?:ed|ing)|fiasco|debacle", JUDGE, 3, "Subjective judgment.", "Describe what went wrong."),
    (r"failed|failure", JUDGE, 1, "Evaluative; needs a measurable standard.", "State the target and what was achieved."),
    (r"so-called|self-styled|infamous|notorious", JUDGE, 2, "Dismissive / loaded label.", "Use the neutral name or title."),
    (r"radical|extremist|fanatic(?:al)?|hardline", JUDGE, 2, "Loaded political label.", "Describe the positions held."),
    (r"cruel|heartless|ruthless|brutal(?:ly)?|vicious", JUDGE, 2, "Emotional judgment.", "Describe the action."),
    (r"dubious|questionable|suspicious|sinister", JUDGE, 2, "Insinuates without evidence.", "State the specific concern and who raised it."),
    (r"hypocri(?:sy|tical|te)", JUDGE, 3, "Accusatory label.", "Attribute the accusation."),
    (r"\bclaims?\b|\bclaimed\b|\balleges?\b", JUDGE, 1, "'Claim' can cast doubt; use consistently.", "Use 'said' unless doubt is established."),
    (r"insist(?:s|ed)?", JUDGE, 1, "Implies defensiveness.", "Use 'said'."),
    (r"\bmere(?:ly)?\b|\bjust\b|\bonly\b", JUDGE, 1, "Minimising word.", "Give the figure and let readers judge."),
    # --- Praise ---
    (r"groundbreaking|revolutionary|game-changing|landmark|unprecedented", PRAISE, 2, "Unsupported praise.", "Describe what is new, with evidence."),
    (r"historic", PRAISE, 2, "Evaluative label.", "State why it is significant, with a source."),
    (r"ambitious", PRAISE, 2, "Subjective judgment.", "Describe the scope or target."),
    (r"heroic|hero|brave(?:ly)?|courageous|inspiring|stellar|brilliant|masterful|visionary", PRAISE, 2, "Subjective praise.", "State the specific action."),
    (r"major success|huge success|great success|resounding success|triumph(?:ant)?|landslide|flawless(?:ly)?", PRAISE, 2, "Unsupported praise.", "Cite the measurable result."),
    (r"brighter future|better tomorrow|golden era", PRAISE, 2, "Unsupported promise.", "Cite evidence or attribute it to a source."),
    (r"massive|huge|enormous|tremendous|staggering|colossal", EXAG, 1, "Size exaggeration.", "Give the number."),
    # --- Certainty / opinion as fact ---
    (r"obvious(?:ly)?", CERT, 2, "Unwarranted certainty.", "State the facts and let readers conclude."),
    (r"clear(?:ly)?(?=,| that| the| to)", CERT, 1, "Asserts certainty.", "Present the evidence."),
    (r"undoubted(?:ly)?|undeniabl[ey]|unquestionabl[ey]|indisputabl[ey]|without (?:a )?doubt|beyond (?:any )?doubt", CERT, 3, "Unwarranted certainty.", "Present the evidence instead."),
    (r"of course|needless to say|it goes without saying|everyone knows|as we all know|nobody can deny", CERT, 3, "Presumes agreement.", "Remove or support with a source."),
    (r"certainly|definitely|surely|inevitabl[ey]|inevitable", CERT, 2, "Asserts certainty.", "Attribute or qualify the claim."),
    (r"in fact|the truth is|the reality is|let's be honest", CERT, 2, "Frames opinion as fact.", "Present the evidence."),
    # --- Predictions ---
    (r"will (?:obviously |definitely |surely )?(?:transform|destroy|ruin|harm|devastate|revolutionise|revolutionize|fail|succeed|collapse|solve|eliminate|end)", PRED, 2, "Prediction stated as fact.", "Attribute: 'X expects / critics warn that...'."),
    # --- Generalisation ---
    (r"everyone|nobody|no one|always|never|all (?:politicians|critics|experts)|the people (?:want|demand)", GEN, 1, "Overgeneralisation.", "Give the number or the specific group."),
    (r"innocent (?:citizens|people|victims)|ordinary (?:citizens|people)|hard-working", GEN, 1, "Emotional framing of a group.", "Use a neutral description such as 'residents'."),
]

# Hindi: Devanagari has no capitalisation; these are matched as plain substrings
# bounded by non-Devanagari characters.
HINDI_RULES = [
    (r"विनाशकारी", EMO, 3, "Sensationalist (disastrous).", "वास्तविक प्रभाव का वर्णन करें।"),
    (r"तबाही|बर्बादी|त्रासदी", EMO, 3, "Sensationalist wording.", "आँकड़ों के साथ नुकसान बताएं।"),
    (r"चौंकाने वाला|चौंकाने वाली|हैरान करने वाला|हैरान करने वाली|सनसनीखेज", EMO, 2, "Emotional framing (shocking).", "तथ्य सीधे लिखें।"),
    (r"तानाशाही|तानाशाह", JUDGE, 3, "Subjective (dictatorial).", "'कठोर' या सटीक नियम का वर्णन करें।"),
    (r"बेवकूफी|बेवकूफ|मूर्खतापूर्ण|नाकारा|निकम्मा|निकम्मी", JUDGE, 3, "Subjective label.", "कार्य का वर्णन करें।"),
    (r"भ्रष्ट|घोटालेबाज|धोखेबाज", JUDGE, 3, "Accusatory label.", "आरोप का स्रोत या अदालत का निष्कर्ष बताएं।"),
    (r"लापरवाह|गैर-ज़िम्मेदार|गैर-जिम्मेदार", JUDGE, 2, "Judges conduct.", "विशिष्ट कार्य या जोखिम बताएं।"),
    (r"विवादास्पद|विवादित", JUDGE, 2, "Loaded label.", "बताएं कौन असहमत है और क्यों।"),
    (r"जल्दबाज़ी|जल्दबाजी", JUDGE, 2, "Subjective judgment.", "वास्तविक समय-सीमा बताएं।"),
    (r"ऐतिहासिक", PRAISE, 2, "Evaluative label (historic).", "स्रोत के साथ महत्व बताएं।"),
    (r"क्रांतिकारी|अभूतपूर्व|शानदार|जबरदस्त|ज़बरदस्त|महान", PRAISE, 2, "Unsupported praise.", "मापने योग्य परिणाम बताएं।"),
    (r"बहादुर|वीर|साहसी", PRAISE, 2, "Subjective praise.", "विशिष्ट कार्य बताएं।"),
    (r"ज़ाहिर है(?: कि)?|जाहिर है(?: कि)?|साफ़ है कि|साफ है कि|निस्संदेह|बेशक|बिना शक|सब जानते हैं|हर कोई जानता है", CERT, 3, "Unwarranted certainty.", "तथ्य और स्रोत दें।"),
    (r"भारी भरकम|बेहद|अत्यंत", EXAG, 1, "Intensifier.", "संख्या दें।"),
    (r"घुटने टेक|मुंह की खानी|करारा जवाब|धज्जियाँ उड़ा|धज्जियां उड़ा", EMO, 2, "Sensationalist idiom.", "'आलोचना की' जैसे तटस्थ शब्द लिखें।"),
]

RULES = {"english": ENGLISH_RULES, "hindi": HINDI_RULES}

# Phrases that signal "someone else is saying this" -> the loaded word is attributed,
# so we show it as "attributed – verify" rather than as the journalist's own bias.
ATTRIBUTION_CUES = {
    "english": [
        r"said", r"says", r"say", r"argue[sd]?", r"insist(?:s|ed)?", r"claim(?:s|ed)?", r"describe[sd]?",
        r"call(?:s|ed)?", r"according to", r"warn(?:s|ed)?", r"told", r"stated?", r"added",
        r"believe[sd]?", r"allege[sd]?", r"maintain(?:s|ed)?", r"described", r"labell?ed", r"saw it as", r"expects?|expected",
        r"critics", r"supporters", r"opponents",
    ],
    "hindi": [r"कहा", r"कहते", r"कहती", r"बताया", r"के अनुसार", r"का कहना", r"आरोप", r"दावा", r"बोले", r"ने कहा", r"मानते"],
}
# core_engine.py

# Quotes: straight "..." and curly “...” / ‘...’ / Hindi-style. Straight single quote = apostrophe, ignored.
QUOTE_PATTERN = re.compile(r'"[^"\n]*"|“[^”]*”|‘[^’]*’')
DEV = "ऀ-ॿ"
WORD = rf"[\w{DEV}]"
SENT_SPLIT = re.compile(r"(?<=[.!?।])\s+|(?<=[.!?।][\"”’])\s+|\n+")


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


# ======================================================================
# AUTO-REPLACEMENTS used by the offline "neutral newsroom" draft
# "" means: delete the word. Humans must still review the result.
# ======================================================================
REPLACEMENTS = [
    (r"slam(?:s|med|ming)?", "criticised"), (r"blast(?:s|ed|ing)?", "criticised"),
    (r"lash(?:es|ed|ing)? out", "criticised"), (r"draconian", "strict"),
    (r"catastroph(?:e|es|ic)", "downturn"), (r"disastrous(?:ly)?", ""),
    (r"admit(?:ted|s)?", "said"), (r"insist(?:s|ed)?", "said"), (r"refus(?:ed|es|ing)", "declined"),
    (r"scheme", "plan"), (r"regime", "government"),
    (r"groundbreaking|revolutionary|game-changing|landmark|unprecedented", ""),
    (r"historic|ambitious|controversial|shocking(?:ly)?|reckless(?:ly)?|irresponsible|incompetent|obvious(?:ly)?", ""),
    (r"major success|huge success|great success|resounding success", "success"),
    (r"brighter future", "future"), (r"innocent (?:citizens|people|victims)", "residents"),
    (r"ordinary (?:citizens|people)", "residents"), (r"ignor(?:ed|es|ing)", "did not address"),
    (r"rush(?:ed|ing)", ""), (r"massive|huge|enormous|tremendous|staggering|colossal", "large"),
    (r"तानाशाही", "कठोर"),
    (r"विनाशकारी|ऐतिहासिक|चौंकाने वाला|चौंकाने वाली|ज़ाहिर है(?: कि)?|जाहिर है(?: कि)?", ""),
]

EVENT_VERBS = r"announced|resigned|signed|launched|passed|approved|arrested|died|began|started|ended|unveiled|appointed|introduced|released|dismissed|elected"
MONTHS = r"January|February|March|April|May|June|July|August|September|October|November|December"
WEEKDAYS = r"Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
DATE_RE = re.compile(rf"\b(?:\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MONTHS})|(?:{MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?|{WEEKDAYS})\b", re.I)
CAUSAL_RE = re.compile(r"\b(?:caused|causing|led to|resulted in|because of|due to|as a result|triggered|forced|destroyed|ruined|wiped out|responsible for)\b", re.I)
NUM_RE = re.compile(r"\d")
PRED_RE = re.compile(r"\b(?:will|expected to|is set to|going to|would)\b", re.I)
STOP_NOUNS = set("of in and to the a an on at for by with from as is are was were that this".split()) | set(MONTHS.lower().split("|")) | set(WEEKDAYS.lower().split("|"))


# ======================================================================
# PAGE 1 helpers: claims, evidence needs, consistency
# ======================================================================
def extract_claims(text, flags, quote_spans, language):
    """Local (no-AI) claim extraction. Returns a list of dicts."""
    claims = []
    for s, e in sentence_spans(text):
        sent = text[s:e].strip()
        if len(sent.split()) < 5:
            continue
        in_quote = any(qs <= s and e <= qe + 1 for qs, qe in quote_spans)
        types = []
        if NUM_RE.search(sent): types.append("Numeric")
        if CAUSAL_RE.search(sent): types.append("Causal")
        if DATE_RE.search(sent) or re.search(EVENT_VERBS, sent, re.I): types.append("Event/Date")
        if PRED_RE.search(sent): types.append("Prediction")
        own = [f for f in flags if s <= f["Start"] < e and f["Voice"].startswith("Journalist")]
        if own: types.append("Evaluative")
        if not types:
            continue
        cue = is_attributed(sent, len(sent), language)
        if in_quote:
            who, status = "Quoted speaker", "Attributed"
        elif cue:
            who, status = "Attributed to a source", "Attributed - verify source"
        else:
            who, status = "Journalist (no attribution)", "Needs source"
        need = []
        if "Numeric" in types: need.append("cite where the figure comes from")
        if "Causal" in types: need.append("show evidence that A caused B")
        if "Event/Date" in types: need.append("confirm date/event with an official source")
        if "Prediction" in types: need.append("say who expects this")
        if "Evaluative" in types: need.append("remove opinion or attribute it")
        claims.append({"Claim": sent, "Type": ", ".join(types), "Voice": who, "Status": status,
                       "Evidence needed": "; ".join(need)})
    return claims


def consistency_check(text):
    """Looks for contradictions INSIDE the article. Never says an event is 'impossible'."""
    issues = []
    by_verb = {}
    for s, e in sentence_spans(text):
        sent = text[s:e]
        dates = {d.lower() for d in DATE_RE.findall(sent)}
        for v in re.findall(rf"\b({EVENT_VERBS})\b", sent, re.I):
            for d in dates:
                by_verb.setdefault(v.lower(), []).append((d, sent.strip()))
    for v, items in by_verb.items():
        if len({d for d, _ in items}) > 1:
            issues.append({"Type": "Date conflict", "Detail": f"'{v}' is linked to different dates: " +
                           ", ".join(sorted({d for d, _ in items})),
                           "Evidence": " || ".join(sn[:90] for _, sn in items[:2])})
    nums = {}
    for m in re.finditer(r"(\d[\d,\.]*)\s*(%|percent|lakh|crore|million|billion|thousand)?\s+(?:of\s+)?(?:the\s+)?([A-Za-z]+)", text):
        val, unit, noun = m.group(1).rstrip(".,"), (m.group(2) or ""), m.group(3).lower()
        if noun in STOP_NOUNS:
            continue
        nums.setdefault((unit, noun), set()).add(val)
    for (unit, noun), vals in nums.items():
        if len(vals) > 1:
            issues.append({"Type": "Possible number conflict",
                           "Detail": f"Different figures given for '{noun}': {', '.join(sorted(vals))}",
                           "Evidence": "Check whether they refer to the same thing."})
    return issues


def dot_escape(s, n=48):
    s = re.sub(r"\s+", " ", s).replace('"', "'").replace("\\", "")
    return s if len(s) <= n else s[:n] + "..."


def claim_graph(claims):
    colors = {"Needs source": "#ffb3b3", "Attributed": "#b7e4c7", "Attributed - verify source": "#ffe08a"}
    lines = ['digraph G {rankdir=LR; node [shape=box, style="rounded,filled", fontsize=11];',
             'A [label="ARTICLE", fillcolor="#cfe8ff"];']
    for i, c in enumerate(claims[:10]):
        lines.append(f'C{i} [label="{dot_escape(c["Claim"])}", fillcolor="white"];')
        lines.append(f'W{i} [label="{c["Voice"]}", fillcolor="#eeeeee"];')
        lines.append(f'S{i} [label="{c["Status"]}", fillcolor="{colors.get(c["Status"], "#eeeeee")}"];')
        lines.append(f"A -> C{i} -> W{i} -> S{i};")
    return "\n".join(lines) + "}"


STATUS_STYLE = {"SUPPORTED": ("✅", "#b7e4c7"), "PARTIAL": ("🟡", "#ffe08a"), "ATTRIBUTED": ("🔵", "#cfe8ff"),
                "INSUFFICIENT": ("⚪", "#eeeeee"), "CONTRADICTED": ("🔴", "#ffb3b3")}


def evidence_graph(items):
    lines = ['digraph G {rankdir=LR; node [shape=box, style="rounded,filled", fontsize=11];',
             'A [label="ARTICLE", fillcolor="#cfe8ff"];']
    for i, it in enumerate(items[:8]):
        st_ = it.get("status", "INSUFFICIENT").upper()
        icon, col = STATUS_STYLE.get(st_, STATUS_STYLE["INSUFFICIENT"])
        lines.append(f'C{i} [label="{dot_escape(it.get("claim", ""))}", fillcolor="white"];')
        lines.append(f'E{i} [label="{dot_escape(it.get("finding", ""), 60)}", fillcolor="#f5f5f5"];')
        lines.append(f'S{i} [label="{icon} {st_}", fillcolor="{col}"];')
        lines.append(f"A -> C{i} -> E{i} -> S{i};")
    return "\n".join(lines) + "}"


def offline_rewrite(text, flags):
    """Rule-based neutral draft. Only touches the journalist's own voice."""
    out, log, pos, cap = [], [], 0, False
    def chunk(t):
        nonlocal cap
        if cap:
            t = re.sub(r"^[,;:\s]+", "", t)
            t = t[:1].upper() + t[1:]
            cap = False
        return t
    for f in sorted([x for x in flags if x["Voice"].startswith("Journalist")], key=lambda x: x["Start"]):
        if f["Start"] < pos:
            continue
        rep = None
        for rx, r in REPLACEMENTS:
            if re.fullmatch(rx, f["Phrase"], flags=re.I):
                rep = r
                break
        if rep is None:
            continue
        out.append(chunk(text[pos:f["Start"]]))
        cur = "".join(out)
        if rep == "":
            nxt = text[f["End"]:].lstrip(" ,")[:1]
            m = re.search(r"\b(a|an)\s$", cur, flags=re.I)
            if m and nxt:
                art = "an" if nxt.lower() in "aeiou" else "a"
                out[-1] = out[-1][:m.start()] + (art.capitalize() if m.group(1)[0].isupper() else art) + " "
            if cur.strip() == "" or re.search(r"(?:[.!?।]|\n)\s*$", cur):
                cap = True
        elif cur.strip() == "" or re.search(r"(?:[.!?]|\n)\s*$", cur):
            rep = rep[:1].upper() + rep[1:]
        out.append(rep)
        pos = f["End"]
        log.append({"Original": f["Phrase"], "Changed to": rep if rep else "(removed)",
                    "Why": f["Reason"], "Needs human check": "Yes" if not rep else "Quick check"})
    out.append(chunk(text[pos:]))
    new = "".join(out)
    new = re.sub(r"[ \t]{2,}", " ", new)
    new = re.sub(r"\s+([,.;:])", r"\1", new)
    return new, log


# ======================================================================
# Gemini helpers (model auto-detected from YOUR key; AI output verified)
# ======================================================================
BASE = "https://generativelanguage.googleapis.com/v1beta"


def ranked_models(api_key):
    r = requests.get(f"{BASE}/models", params={"key": api_key, "pageSize": 200}, timeout=20)
    r.raise_for_status()
    names = [m["name"].split("/")[-1] for m in r.json().get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    bad = ("tts", "image", "embed", "live", "audio", "vision", "robotics", "computer", "gemma", "learnlm", "aqa")
    names = [n for n in names if not any(b in n.lower() for b in bad)]
    def rank(n):
        s = n.lower()
        return (0 if "flash" in s and "lite" not in s else 1 if "flash" in s else 2,
                1 if ("preview" in s or "exp" in s) else 0, n)
    return sorted(names, key=rank)


def gemini(prompt, api_key, search=False):
    """Returns (model, text, sources). Tries up to 3 models."""
    errs = []
    for m in ranked_models(api_key)[:3]:
        body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}
        if search:
            body["tools"] = [{"google_search": {}}]
        else:
            body["generationConfig"]["responseMimeType"] = "application/json"
        try:
            r = requests.post(f"{BASE}/models/{m}:generateContent", params={"key": api_key}, json=body, timeout=90)
        except Exception as e:
            errs.append(f"{m}: {e}")
            continue
        if r.status_code == 200:
            try:
                cand = r.json()["candidates"][0]
                text = "".join(p.get("text", "") for p in cand["content"]["parts"])
                gm = cand.get("groundingMetadata", {})
                srcs = [{"title": c["web"].get("title", ""), "url": c["web"].get("uri", "")}
                        for c in gm.get("groundingChunks", []) if "web" in c]
                return m, text, srcs
            except Exception as e:
                errs.append(f"{m}: bad response ({e})")
        else:
            errs.append(f"{m}: HTTP {r.status_code} {r.text[:120]}")
    raise RuntimeError(" | ".join(errs) or "no model available")


def parse_json(raw):
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    a = min([i for i in (raw.find("["), raw.find("{")) if i != -1], default=-1)
    b = max(raw.rfind("]"), raw.rfind("}"))
    if a == -1 or b == -1:
        raise ValueError("AI did not return JSON")
    return json.loads(raw[a:b + 1])


AUDIT_PROMPT = """You are a strict news editor. Read the article ({lang}). Find wording where the JOURNALIST'S OWN VOICE
shows subjective judgment, emotional framing, opinion stated as fact, unsupported predictions, loaded labels, or vague
attribution ("experts say"). Ignore text inside quotation marks.
Return ONLY a JSON array. Each item: {{"phrase": "<EXACT words copied from the article, 1-8 words>",
"category": "<short label>", "reason": "<one sentence>", "suggestion": "<neutral wording that adds NO new facts>"}}
If the article is neutral return [].
ARTICLE:
{text}"""

VERIFY_PROMPT = """Today is {today}. You are a careful fact-checking research assistant. USE GOOGLE SEARCH.
From the article below pick up to 5 of the most important CHECKABLE factual claims (events, dates, figures, who did what).
Skip opinions. For each, look for independent reporting and compare.
Return ONLY a JSON array, no other text. Each item:
{{"claim": "<claim in the article>",
 "status": "SUPPORTED | PARTIAL | ATTRIBUTED | INSUFFICIENT | CONTRADICTED",
 "finding": "<one sentence: what the sources say and any mismatch in figure/date/cause>"}}
Rules: "No evidence found" must be INSUFFICIENT, never CONTRADICTED. Use CONTRADICTED only if a source directly says
otherwise. Never invent sources, quotes or numbers.
ARTICLE:
{text}"""

REWRITE_PROMPT = """You are a newsroom copy editor. Rewrite the article ({lang}) in two versions.
RULES: add NO new facts, figures, sources or quotes. Keep all quotations exactly as they are. Where a claim lacks support,
write [SOURCE NEEDED] instead of inventing one. Keep the same language as the article.
1) "evidence_aligned": keep claims the verification supports, attribute or soften unsupported ones, mark gaps with [SOURCE NEEDED].
2) "neutral": remove loaded words and opinion; keep only plain reporting wording.
Return ONLY JSON: {{"evidence_aligned": "...", "neutral": "...", "changes": ["<short change note>", "..."]}}
VERIFICATION RESULTS (may be empty):
{ver}
ARTICLE:
{text}"""


def verify_ai_phrases(items, text, quote_spans, rule_flags):
    out, taken = [], [(f["Start"], f["End"]) for f in rule_flags]
    for it in items:
        ph = str(it.get("phrase", "")).strip()
        if not ph:
            continue
        for m in re.finditer(re.escape(ph), text, flags=re.I):
            s, e = m.start(), m.end()
            if any(qs <= s < qe for qs, qe in quote_spans) or any(s < te and e > ts for ts, te in taken):
                continue
            taken.append((s, e))
            out.append({"Phrase": text[s:e], "Category": it.get("category", "Contextual"), "Severity": 2,
                        "Voice": "Journalist's own voice", "Reason": it.get("reason", ""),
                        "Suggestion": it.get("suggestion", ""), "Source": "Gemini (phrase verified in text)",
                        "Start": s, "End": e})
            break
    return out


# ======================================================================
# SAMPLE ARTICLES (for the live demo)
# ======================================================================
SAMPLES = {
 "1. Education policy (loaded + attributed)": """Government Announces a New Education Policy

The government has unveiled a groundbreaking education policy that officials describe as a historic achievement. Supporters insist that the ambitious reform will transform schools and create a brighter future for millions of students. However, critics argue that the administration has ignored serious problems facing classrooms.

The controversial policy introduces changes to the curriculum, teacher training and assessment methods. Government representatives say these changes will modernize the education system and improve learning outcomes. Opponents warn that the rushed plan could place additional pressure on teachers and students.

Several teachers have expressed concern about insufficient training and limited classroom resources. Education officials maintain that implementation will take place in phases. The policy is expected to begin in selected schools next academic year.

Although the government has presented the reform as a major success, its actual effect on student performance remains uncertain. Independent evaluations will be needed to determine whether the changes deliver the promised benefits.""",
 "2. Mayor story (own voice + quotes + conflicts)": """The incompetent mayor's reckless plan was slammed by residents on Monday. The council announced the budget on 12 March, but the mayor announced it again on 14 March. The disastrous scheme caused 20% job losses and destroyed the local market. Senator Rao said, "This policy is draconian and shocking." Everyone knows the plan will obviously fail. Officials said 20% of shops closed, while another report said 35% of shops closed.""",
 "3. Neutral council report (should stay clean)": """The city council approved the 2026 budget on Tuesday by a vote of 7 to 2. The budget totals 4.1 billion rupees and allocates 18 percent to road maintenance. Councillor Mehta said, "We need more time to review the figures." The budget takes effect on 1 April.""",
 "4. Hindi sample": """सरकार ने एक विनाशकारी नीति लागू की है। ज़ाहिर है कि यह नीति विफल होगी। मंत्री ने कहा, "यह नीति ऐतिहासिक है।" विपक्ष ने इसे तानाशाही बताया।""",
}

COLORS = {"Journalist's own voice": "#ffb3b3", "Attributed - verify source": "#ffe08a"}


def highlight(text, flags, quote_spans):
    marks = [(f["Start"], f["End"], f) for f in flags] + [(s, e, None) for s, e in quote_spans]
    marks.sort(key=lambda x: x[0])
    out, pos = [], 0
    for s, e, f in marks:
        if s < pos:
            continue
        out.append(html.escape(text[pos:s]))
        seg = html.escape(text[s:e])
        if f is None:
            out.append(f"<span style='background:#cfe8ff;color:#111;border-radius:3px;padding:1px 2px' title='Protected quote'>{seg}</span>")
        else:
            tip = html.escape(f"{f['Category']}: {f['Reason']} Suggestion: {f['Suggestion']}", quote=True)
            out.append(f"<mark style='background:{COLORS[f['Voice']]};color:#111;border-radius:3px;padding:1px 3px' title=\"{tip}\">{seg}</mark>")
        pos = e
    out.append(html.escape(text[pos:]))
    return "<div style='line-height:1.9;font-size:16px;white-space:pre-wrap'>" + "".join(out) + "</div>"


def key_of(*parts):
    return hashlib.md5("||".join(parts).encode("utf-8")).hexdigest()


# ======================================================================
# STREAMLIT APP
# ======================================================================
def main():
    st.set_page_config(page_title="BiasGuard AI", layout="wide", page_icon="📰")
    ss = st.session_state

    with st.sidebar:
        st.title("📰 BiasGuard AI")
        st.caption("Evidence-aware editorial intelligence")
        page = st.radio("Page", ["1 · Audit", "2 · Verify", "3 · Reconstruct"], key="page")
        language = st.selectbox("Article language", ["English", "Hindi"]).lower()
        api_key = st.text_input("Gemini API key (optional)", type="password")
        st.caption("Page 1 and the offline rewrite work with NO key. Pages 2 and AI rewrite need a key.")
        st.markdown("---")
        st.markdown("**Pipeline**\n1. Quote protector\n2. Rule engine (EN + HI)\n3. Attribution check\n4. Claim extraction\n5. Consistency check\n6. Search-grounded verification\n7. Safe rewrite")

    # ---------- article input (kept in session so every page can use it) ----------
    if page.startswith("1"):
        st.header("Page 1 · Audit: how is the article written?")
        opts = list(SAMPLES.keys()) + ["(my own text)"]
        pick = st.selectbox("Load a sample", opts, index=opts.index(ss.get("last_pick", opts[0])))
        if "article_box" not in ss:
            ss["article_box"] = ss.get("article_saved", SAMPLES[opts[0]])
        if ss.get("last_pick") != pick:
            ss["last_pick"] = pick
            if pick in SAMPLES:
                ss["article_box"] = SAMPLES[pick]
        art = st.text_area("Article draft", height=260, key="article_box")
        ss["article_saved"] = art
    text = ss.get("article_saved", "")
    if not text.strip():
        st.warning("Paste an article on Page 1 first.")
        return
    if language == "hindi" and pick_is_english(text):
        st.info("Language is set to Hindi but the text looks English. Check the sidebar.")

    # ---------- engine (instant, free) ----------
    flags, quotes = scan_for_bias(text, language)
    qspans = find_quote_spans(text)
    tkey = key_of(text, language)

    # ====================== PAGE 1 ======================
    if page.startswith("1"):
        if st.button("➕ Add AI contextual review (1 API call)"):
            if not api_key:
                st.error("Enter a Gemini API key in the sidebar.")
            else:
                with st.spinner("Asking Gemini..."):
                    try:
                        m, raw, _ = gemini(AUDIT_PROMPT.format(lang=language, text=text), api_key)
                        items = [d for d in parse_json(raw) if isinstance(d, dict)]
                        ss["ai_audit"] = {"key": tkey, "model": m, "items": items}
                    except Exception as e:
                        ss["ai_audit"] = {"key": tkey, "error": str(e)[:300]}
        ai = ss.get("ai_audit")
        if ai and ai.get("key") == tkey:
            if "error" in ai:
                st.warning(f"AI unavailable: {ai['error']}. Showing rule-engine results only.")
            else:
                extra = verify_ai_phrases(ai["items"], text, qspans, flags)
                flags = sorted(flags + extra, key=lambda f: f["Start"])
                st.success(f"AI layer ran on {ai['model']}: {len(ai['items'])} suggestions, {len(extra)} verified in the text.")

        claims = extract_claims(text, flags, qspans, language)
        issues = consistency_check(text)
        rate, uniq, total = flagged_rate(flags, text, quotes)
        own = [f for f in flags if f["Voice"].startswith("Journalist")]
        att = [f for f in flags if f["Voice"].startswith("Attributed")]
        unsourced = [c for c in claims if c["Status"] == "Needs source"]

        c = st.columns(5)
        c[0].metric("Flagged phrase rate", f"{rate:.1f}%", help="Unique own-voice flagged phrases / words outside quotes. NOT a validated bias score.")
        c[1].metric("Own-voice flags", len(own))
        c[2].metric("Attributed - verify", len(att))
        c[3].metric("Claims needing a source", len(unsourced))
        c[4].metric("Consistency issues", len(issues))

        if not flags:
            st.info("Nothing flagged. That does not prove neutrality: framing, omission and source choice are not checked.")
        st.markdown("🟥 journalist's own voice &nbsp; 🟨 attributed, verify the source &nbsp; 🟦 protected quote. Hover a highlight for the reason.")
        st.markdown(highlight(text, flags, qspans), unsafe_allow_html=True)

        t1, t2, t3, t4 = st.tabs(["Flags", "Claims & evidence needed", "Consistency check", "Claim map"])
        with t1:
            if flags:
                df = pd.DataFrame(flags).drop(columns=["Start", "End"])
                st.dataframe(df)
                st.bar_chart(df["Category"].value_counts())
            else:
                st.write("No flags.")
        with t2:
            st.caption("Claims are found with local rules (numbers, dates, causes, predictions, opinions). Page 2 checks them against outside reporting.")
            st.dataframe(pd.DataFrame(claims)) if claims else st.write("No checkable claims found.")
        with t3:
            st.caption("Looks only for contradictions INSIDE the article. It never declares an event impossible.")
            if issues:
                for i in issues:
                    st.warning(f"**{i['Type']}**: {i['Detail']}\n\n_{i['Evidence']}_")
            else:
                st.success("No internal date or number conflicts found.")
        with t4:
            if claims:
                st.graphviz_chart(claim_graph(claims))
            else:
                st.write("No claims to map.")
        ss["audit"] = {"flags": flags, "claims": claims}
        return

    # ====================== PAGE 2 ======================
    if page.startswith("2"):
        st.header("Page 2 · Verify: what independent reporting supports these claims?")
        st.info("Statuses: ✅ Supported · 🟡 Partial · 🔵 Attributed · ⚪ Insufficient evidence · 🔴 Contradicted. "
                "**No evidence found does not mean false.**")
        with st.expander("Article being checked"):
            st.write(text)
        if st.button("🔎 Verify claims with Google Search (1 API call)", type="primary"):
            if not api_key:
                st.error("Enter a Gemini API key in the sidebar.")
            else:
                with st.spinner("Searching and comparing..."):
                    try:
                        prompt = VERIFY_PROMPT.format(today=datetime.date.today().isoformat(), text=text)
                        m, raw, srcs = gemini(prompt, api_key, search=True)
                        items = [d for d in parse_json(raw) if isinstance(d, dict) and d.get("claim")]
                        ss["verify"] = {"key": tkey, "model": m, "items": items, "sources": srcs}
                    except Exception as e:
                        ss["verify"] = {"key": tkey, "error": str(e)[:400]}
        v = ss.get("verify")
        if not v or v.get("key") != tkey:
            st.write("Press the button to start. Each press uses one API call, so results are saved.")
            return
        if "error" in v:
            st.error(f"Verification unavailable: {v['error']}")
            st.write("The rest of the app still works. Page 1 shows which claims need sources.")
            return
        items, srcs = v["items"], v["sources"]
        st.success(f"Checked with {v['model']} using Google Search grounding. {len(srcs)} web sources were retrieved.")
        rows = []
        for it in items:
            s_ = str(it.get("status", "INSUFFICIENT")).upper().split()[0].strip("|")
            if s_ not in STATUS_STYLE:
                s_ = "INSUFFICIENT"
            it["status"] = s_
            rows.append({"": STATUS_STYLE[s_][0], "Status": s_, "Claim": it.get("claim", ""), "What sources say": it.get("finding", "")})
        st.dataframe(pd.DataFrame(rows))
        st.subheader("Evidence & claim graph")
        st.graphviz_chart(evidence_graph(items))
        st.subheader("Sources retrieved by the search tool")
        if srcs:
            seen = set()
            for s in srcs:
                if s["url"] in seen:
                    continue
                seen.add(s["url"])
                st.markdown(f"- [{s['title'] or s['url']}]({s['url']})")
        else:
            st.write("No web sources were returned, so every status above should be read as low confidence.")
        st.caption("A human must open the sources and confirm. The tool does not decide truth.")
        return

    # ====================== PAGE 3 ======================
    st.header("Page 3 · Reconstruct: make it publication-ready")
    audit = ss.get("audit", {})
    new_text, log = offline_rewrite(text, flags)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Original")
        st.markdown(highlight(text, flags, qspans), unsafe_allow_html=True)
    with c2:
        st.subheader("Neutral draft (offline rules)")
        st.markdown(f"<div style='line-height:1.9;font-size:16px;white-space:pre-wrap;background:#d8f3dc;color:#111;padding:10px;border-radius:6px'>{html.escape(new_text)}</div>", unsafe_allow_html=True)
    st.caption("Quotes are never touched. Removing a word can leave awkward grammar: a human must read it.")
    st.subheader("Editorial change log")
    st.dataframe(pd.DataFrame(log)) if log else st.write("No automatic changes were needed.")

    st.markdown("---")
    st.subheader("AI versions: evidence-aligned and neutral newsroom")
    if st.button("✍️ Generate with AI (1 API call)", type="primary"):
        if not api_key:
            st.error("Enter a Gemini API key in the sidebar.")
        else:
            with st.spinner("Writing..."):
                try:
                    v = ss.get("verify")
                    ver = json.dumps(v["items"], ensure_ascii=False) if v and v.get("key") == tkey and "items" in v else "[]"
                    m, raw, _ = gemini(REWRITE_PROMPT.format(lang=language, text=text, ver=ver), api_key)
                    ss["rewrite"] = {"key": tkey, "model": m, "data": parse_json(raw)}
                except Exception as e:
                    ss["rewrite"] = {"key": tkey, "error": str(e)[:300]}
    rw = ss.get("rewrite")
    if rw and rw.get("key") == tkey:
        if "error" in rw:
            st.warning(f"AI unavailable: {rw['error']}. The offline neutral draft above is still valid.")
        else:
            d = rw["data"]
            a, b = st.columns(2)
            a.subheader("Evidence-aligned")
            a.write(d.get("evidence_aligned", ""))
            b.subheader("Neutral newsroom")
            b.write(d.get("neutral", ""))
            if d.get("changes"):
                st.markdown("**Changes made**\n" + "\n".join(f"- {x}" for x in d["changes"]))
            st.caption(f"Generated by {rw['model']}. [SOURCE NEEDED] marks claims you must support. Review before publishing.")
    st.download_button("Download offline neutral draft (.txt)", new_text, "neutral_draft.txt")


def pick_is_english(text):
    letters = re.findall(r"[A-Za-z]", text)
    dev = re.findall(r"[ऀ-ॿ]", text)
    return len(letters) > 3 * max(len(dev), 1) and len(letters) > 40


main()