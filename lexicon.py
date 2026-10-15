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
    (r"ज़ाहिर है|जाहिर है|साफ़ है कि|साफ है कि|निस्संदेह|बेशक|बिना शक|सब जानते हैं|हर कोई जानता है", CERT, 3, "Unwarranted certainty.", "तथ्य और स्रोत दें।"),
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