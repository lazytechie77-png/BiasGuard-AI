# BiasGuard AI

### Evidence-Aware Editorial Auditing for Responsible Journalism

BiasGuard AI is an AI-assisted editorial auditing system designed to help journalists and student writers identify potentially subjective, loaded, unsupported, or overconfident framing before publication.

Rather than simply asking an LLM whether an article is "biased", BiasGuard analyzes how claims are constructed and provides an evidence-linked explanation for why a sentence may require editorial review.

---

##  Problem

Journalists and student writers can unintentionally introduce:

- Subjective or emotionally loaded language
- Opinions presented as facts
- Excessive certainty
- Unsupported causal claims
- Unattributed evaluations
- Uneven framing of different actors
- Ambiguous attribution inside quoted or reported statements

These issues can affect the neutrality and credibility of factual reporting.

---

## Our Approach

BiasGuard uses a multi-layer editorial audit pipeline:

```text
ARTICLE
   ↓
TEXT PARSER
   ↓
ATTRIBUTION / QUOTE ENGINE
   ↓
LANGUAGE ENGINE
   ↓
CLAIM ANALYZER
   ↓
EVIDENCE LINKER
   ↓
FRAMING AUDITOR
   ↓
FINDING FUSION
   ↓
EDITORIAL REVIEW
