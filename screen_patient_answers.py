"""Screen candidate answers before they are shown to a patient.

Why this exists
---------------
The poster measured empathy with a NURSE keyword count and reliability with U.
Neither of those notices the things that actually decide whether a patient can
use an answer: whether the answer to the question stands in the first sentence,
whether the text talks about its own sources, whether the words are readable.
This script checks those, one answer at a time, and prints what a human should
look at rather than a single score.

Nothing here is a model of patient experience. Every flag is a prompt to read
the answer yourself; FAIL means "read this one first", not "discard".

Usage
-----
    python screen_patient_answers.py user_study/questions.json
    python screen_patient_answers.py results/uq_tradeoff_direct_empathy_*.json
    python screen_patient_answers.py <file> --verbose      # print flagged texts

Reads either a study file (list of {patient_query, answer_text, _condition})
or a raw run file (results[].generation_meta.final_answer).
"""

from __future__ import annotations

import glob
import json
import re
import statistics as st
import sys
from pathlib import Path

# ----------------------------------------------------------------- thresholds
MAX_WORDS = 150          # the prompt asks for at most 150
MAX_SENT_WORDS = 20      # the prompt asks for 15; 20 is where a reader stumbles
MIN_FLESCH = 50.0        # German Amstad: 50-60 "mittelschwer", >60 "leicht"
MAX_LONG_SENT_SHARE = 15.0   # per cent of sentences above MAX_SENT_WORDS

VOWELS, DIPH = "aeiouäöüy", ("ei", "ie", "au", "eu", "äu")

# Second person: the patient must be spoken to, not spoken about.
YOU = re.compile(r"\b(Sie|Ihre?[nrms]?|Ihnen)\b")

# The answer talking about its own evidence layer. A patient did not ask what
# the documents say; this phrasing also reads as hedging.
META = re.compile(
    r"(bereitgestellt\w*|vorliegend\w+ Information\w*|laut den Unterlagen|"
    r"die Dokumente|in den Unterlagen|mir zur Verf[üu]gung|Kontext\w*|"
    r"Leitlinien empfehlen|Studien zeigen|die Quellen)", re.I)

# Letter furniture. Chat answers are not letters.
SALUT = re.compile(r"^\s*(Sehr geehrte|Liebe[rs]?\b|Guten Tag|Hallo\b|Antwort\s*:)", re.I)
CLOSING = re.compile(r"(Mit freundlichen Gr[üu][ßs]en|Ihr Behandlungsteam\s*$|"
                     r"Herzliche Gr[üu][ßs]e)", re.I)

# Gendered slash forms, which screen readers and patients both stumble over.
SLASH = re.compile(r"\b\w+/\w{1,4}\b")

# Substance and receptor names a patient cannot act on.
PHARMA = re.compile(
    r"\b(Ondansetron|Granisetron|Dexamethason|Pilocarpin|Antiemetik\w*|"
    r"5-HT.?.?-?Antagonist\w*|Serotoninrezeptor\w*|ARPI\w*|Aminos[äa]ureninfusion\w*)\b", re.I)

# Terms the prompt requires to be explained at first use.
NEEDS_GLOSS = {
    "mCRPC": r"\bmCRPC\b",
    "kastrationsresistent": r"kastrationsresistent\w*",
    "metastasiert": r"metastasiert\w*",
    "Remission": r"\bRemission\w*\b",
    "palliativ": r"\bpalliativ\w*\b",
    "Xerostomie": r"\bXerostomie\b",
    "Thrombozytopenie": r"\bThrombozytopenie\b",
    "Leukopenie": r"\bLeukopenie\b",
    "Anämie": r"\bAn[äa]mie\b",
    "Nephrotoxizität": r"\bNephrotoxizit[äa]t\b",
    "exprimieren": r"\bexprimier\w+\b",
    "prophylaktisch": r"\bprophylak\w+\b",
    "systemisch": r"\bsystemisch\w*\b",
}
# A gloss counts if a plain explanation follows within the same sentence,
# in brackets or after "also", "das heisst", "das bedeutet", "sogenannt".
GLOSS_NEAR = re.compile(r"(\([^)]{6,}\)|\bals[o]?\b|das hei[ßs]t|das bedeutet|sogenannt\w*|"
                        r"\bd\.\s?h\.)", re.I)


def syllables(word: str) -> int:
    w = word.lower().strip(",.!?()[]{};:\"'")
    n, i = 0, 0
    while i < len(w):
        if i < len(w) - 1 and w[i:i + 2] in DIPH:
            n, i = n + 1, i + 2
        elif w[i] in VOWELS:
            n, i = n + 1, i + 1
        else:
            i += 1
    return max(1, n)


def flesch_de(text: str) -> float:
    """Amstad's German adaptation: 180 - ASL - 58.5 * ASW. Same code as analyse.py."""
    words = [w for w in text.split() if w.strip(",.!?()[]{};:\"'")]
    if not words:
        return 0.0
    sents_n = max(1, len([s for s in re.split(r"[.!?]+", text) if s.strip()]))
    asl = len(words) / sents_n
    asw = sum(syllables(w) for w in words) / len(words)
    return max(0.0, min(100.0, 180.0 - asl - 58.5 * asw))


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.replace("\n", " ")) if s.strip()]


def screen(answer: str) -> dict:
    """Return the flags for one answer. Keys are the reasons, values True = problem."""
    ss = sentences(answer)
    sl = [len(s.split()) for s in ss] or [0]
    words = len(answer.split())
    long_share = 100.0 * sum(1 for n in sl if n > MAX_SENT_WORDS) / len(sl)

    ungloss = []
    for term, pat in NEEDS_GLOSS.items():
        for m in re.finditer(pat, answer, re.I):
            host = next((s for s in ss if m.group(0) in s), "")
            if not GLOSS_NEAR.search(host):
                ungloss.append(term)
            break

    return {
        "words": words,
        "sentences": len(ss),
        "mean_sentence": st.mean(sl),
        "longest_sentence": max(sl),
        "long_sentence_share": long_share,
        "flesch": flesch_de(answer),
        "unglossed": sorted(set(ungloss)),
        "flags": {
            "no answer to the patient in sentence 1": not YOU.search(ss[0]) if ss else True,
            "talks about its own sources": bool(META.search(answer)),
            "letter salutation or closing": bool(SALUT.search(answer) or CLOSING.search(answer)),
            "slash form": bool(SLASH.search(answer)),
            "drug or receptor names": bool(PHARMA.search(answer)),
            f"longer than {MAX_WORDS} words": words > MAX_WORDS,
            f"over {MAX_LONG_SENT_SHARE:.0f}% long sentences": long_share > MAX_LONG_SENT_SHARE,
            f"Flesch below {MIN_FLESCH:.0f}": flesch_de(answer) < MIN_FLESCH,
            "unexplained technical terms": bool(ungloss),
        },
    }


def load(path: Path) -> list[tuple[str, str, str]]:
    """-> [(condition, question, answer)] from a study bundle, a legacy study
    file or a raw run file."""
    d = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(d, dict) and "questions" in d:          # bundle: every condition
        return [(cond, q.get("patient_query", ""), ans)
                for q in d["questions"]
                for cond, ans in q.get("answers", {}).items()]
    if isinstance(d, list):
        return [(x.get("_condition", "?"), x.get("patient_query", ""),
                 x.get("answer_text", "")) for x in d]
    cond = d.get("metadata", {}).get("prompt_mode", path.stem)
    if not d.get("metadata", {}).get("no_rag", True):
        cond += " (RAG)"
    out = []
    for r in d.get("results", []):
        a = (r.get("generation_meta", {}).get("final_answer") or "")
        out.append((cond, r.get("question", ""), a.split("VERBAL_CONFIDENCE:")[0].strip()))
    return out


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    verbose = "--verbose" in argv
    if not args:
        print(__doc__)
        return 2

    paths = [Path(p) for a in args for p in sorted(glob.glob(a))]
    if not paths:
        print("no such file")
        return 2

    for path in paths:
        items = load(path)
        print(f"\n{'=' * 78}\n{path.name}   {len(items)} answers")
        by_cond: dict[str, list] = {}
        for cond, question, answer in items:
            by_cond.setdefault(cond, []).append((question, answer))

        for cond, rows in by_cond.items():
            reports = [screen(a) for _, a in rows]
            print(f"\n--- {cond}   (n={len(rows)})")
            print(f"    words {st.mean(r['words'] for r in reports):5.0f}"
                  f"   Flesch {st.mean(r['flesch'] for r in reports):5.1f}"
                  f"   mean sentence {st.mean(r['mean_sentence'] for r in reports):4.1f} w"
                  f"   longest {max(r['longest_sentence'] for r in reports)} w")
            counts: dict[str, int] = {}
            for r in reports:
                for k, v in r["flags"].items():
                    counts[k] = counts.get(k, 0) + bool(v)
            for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
                bar = "#" * round(20 * v / len(rows))
                print(f"      {v:3d}/{len(rows)}  {bar:<20}  {k}")

            worst = sorted(range(len(rows)),
                           key=lambda i: -sum(reports[i]["flags"].values()))
            print("    most flagged:")
            for i in worst[:3]:
                q, a = rows[i]
                n = sum(reports[i]["flags"].values())
                print(f"      [{n} flags] {q[:62]}")
                if reports[i]["unglossed"]:
                    print(f"                unexplained: {', '.join(reports[i]['unglossed'])}")
                if verbose:
                    print("      " + a.replace("\n", "\n      ")[:900] + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
