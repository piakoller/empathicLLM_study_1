"""
build_questions.py — builds the study bundle for the Phase-I patient study.

Writes questions.json in BUNDLE format: every condition's answer for every
question. Which condition a given participant sees is decided at runtime in
`study_data.assign_items()`, so that condition is crossed with question across
the sample instead of being fixed to a subset of questions. A flat list of
pre-assigned items would silently disable that — `study_data.load_bundle()`
accepts one for backwards compatibility, but then every participant sees the
same assignment and question difficulty is confounded with condition.

    {"meta": {"conditions": ["clinical_only", "direct_empathy"], ...},
     "questions": [{"question_index": 1,
                    "patient_query": "...",
                    "answers": {"clinical_only": "...", "direct_empathy": "..."}}]}

Usage
-----
    python build_questions.py --list-runs                  # what is available
    python build_questions.py --run 20260909               # two conditions
    python build_questions.py --run 20260909 --include-twostage
    python build_questions.py                              # newest per condition

Also writes questions_provenance.json — the same provenance as the bundle's
meta block, as a standalone record for the study documentation.

Why the run check exists
------------------------
Until 15 Sep 2026 the study file held Clinical Only answers from a LMDeploy run
of 20 Aug and Direct Empathy answers from a HuggingFace 4-bit run of 13 Aug.
Two arms, two inference stacks, one of them quantised — so a difference in
patient ratings could have come from the backend rather than from the prompting
strategy, with no way to separate the two afterwards. Selecting files by name
sorting did not notice. This script compares the runs' own metadata and refuses
to build a bundle whose arms do not match.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys

BASE_DIR = pathlib.Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR.parent / "uq_medgemma_benchmark" / "results"
OUT_BUNDLE = BASE_DIR / "questions.json"
OUT_PROVENANCE = BASE_DIR / "questions_provenance.json"

# Slugs must match study_data.CONDITION_LABELS.
CONDITIONS = {
    "clinical_only": "uq_tradeoff_clinical_only_20*.json",
    "direct_empathy": "uq_tradeoff_direct_empathy_20*.json",
    "two_stage": "uq_tradeoff_two_stage_20*.json",
}
# The "_norag_" runs are a separate factor and never enter the patient study;
# the patterns above exclude them, since the timestamp follows the mode directly.

# results/ is sorted by sort_results.py into current/, superseded/<date_backend>/,
# incomplete/, derived/ and archive/, so the search has to be recursive. Two of
# those folders must never supply a study answer: incomplete/ holds aborted and
# --limit runs, archive/ holds the older uq_benchmark_* generation.
SKIP_DIRS = {"incomplete", "archive", "derived"}

COMPARE_KEYS = ("mode", "n_candidates", "max_tokens", "threshold_tau")


def strip_verbal_confidence(text: str) -> str:
    """Remove the VERBAL_CONFIDENCE tag. It is in every delivered answer by
    design — it is the verbalized-confidence measurement — and must never reach
    a participant."""
    if not text:
        return ""
    return text.split("VERBAL_CONFIDENCE:", 1)[0].strip()


def runs_for(condition: str) -> list[tuple[str, pathlib.Path, dict]]:
    """(generated_at, path, data) for every run of one condition, oldest first.

    Searches results/ recursively, because sort_results.py files runs into
    subfolders. A file that exists in more than one place is taken from
    current/ if it is there, so a stale copy cannot shadow the live one.
    """
    by_name: dict[str, tuple[str, pathlib.Path, dict]] = {}
    for p in sorted(RESULTS_DIR.rglob(CONDITIONS[condition])):
        if SKIP_DIRS & set(part.lower() for part in p.relative_to(RESULTS_DIR).parts[:-1]):
            continue
        if p.name in by_name and by_name[p.name][1].parent.name == "current":
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:                      # a half-written run file
            print(f"[SKIP] {p.name}: {exc}", file=sys.stderr)
            continue
        by_name[p.name] = (data.get("metadata", {}).get("generated_at", ""), p, data)
    return sorted(by_name.values())


def list_runs() -> None:
    for cond in CONDITIONS:
        print(f"\n{cond}")
        rows = runs_for(cond)
        if not rows:
            print(f"  (none found under {RESULTS_DIR})")
        for when, path, data in rows:
            meta = data.get("metadata", {})
            where = path.parent.relative_to(RESULTS_DIR)
            print(f"  {when[:19]:<19}  n={len(data.get('results', [])):<3} "
                  f"{meta.get('mode', '?')}")
            print(f"  {'':19}  {where}\\{path.name}")


def pick_run(condition: str, pin: str | None) -> tuple[pathlib.Path, dict]:
    candidates = runs_for(condition)
    if pin:
        candidates = [c for c in candidates if pin in c[1].name]
        if not candidates:
            raise SystemExit(f"[ABORT] no {condition} run matching '{pin}'. "
                             f"Try --list-runs.")
    if not candidates:
        raise SystemExit(f"[ABORT] no run files for {condition} in {RESULTS_DIR}")
    _, path, data = candidates[-1]
    return path, data


def check_same_setup(chosen: dict[str, tuple[pathlib.Path, dict]], allow_mixed: bool) -> None:
    """Every arm must come from the same inference setup, or the study is confounded."""
    metas = {c: d.get("metadata", {}) for c, (_, d) in chosen.items()}
    ref_cond = next(iter(metas))
    ref = metas[ref_cond]
    problems = []
    for cond, meta in metas.items():
        if cond == ref_cond:
            continue
        for k in COMPARE_KEYS:
            if meta.get(k) != ref.get(k):
                problems.append(f"{k}: {ref_cond}={ref.get(k)!r} vs {cond}={meta.get(k)!r}")
        day_a, day_b = str(ref.get("generated_at"))[:10], str(meta.get("generated_at"))[:10]
        if day_a != day_b:
            problems.append(f"generated on different days: {ref_cond}={day_a} vs {cond}={day_b}")

    if not problems:
        return
    msg = "The arms would not come from the same run setup:\n  - " + "\n  - ".join(problems)
    if allow_mixed:
        print(f"[WARN] {msg}\n[WARN] continuing because --allow-mixed-backend was given.",
              file=sys.stderr)
        return
    raise SystemExit(
        f"[ABORT] {msg}\n\n"
        "Participants would be comparing the generation setup as much as the\n"
        "prompting strategy. Pin one run with --run <timestamp prefix>, or pass\n"
        "--allow-mixed-backend if you have a reason and will report it."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the study bundle questions.json")
    ap.add_argument("--list-runs", action="store_true", help="show available runs and exit")
    ap.add_argument("--run", metavar="PREFIX",
                    help="pin a run by a substring of its filename, e.g. 20260909")
    ap.add_argument("--include-twostage", action="store_true",
                    help="add the two-stage condition as a third arm")
    ap.add_argument("--allow-mixed-backend", action="store_true",
                    help="build even if the arms come from different run setups")
    args = ap.parse_args()

    if args.list_runs:
        list_runs()
        return

    wanted = ["clinical_only", "direct_empathy"]
    if args.include_twostage:
        wanted.append("two_stage")

    chosen = {c: pick_run(c, args.run) for c in wanted}
    for cond, (path, data) in chosen.items():
        meta = data.get("metadata", {})
        print(f"[LOAD] {cond:<15} {path.name}")
        print(f"       {meta.get('generated_at', '?')}   {meta.get('mode', '?')}")

    check_same_setup(chosen, args.allow_mixed_backend)

    # Questions must be the same set in every arm, and are indexed in the order
    # of the first arm's run file, which is the order they were asked in.
    per_cond: dict[str, dict[str, str]] = {}
    for cond, (path, data) in chosen.items():
        answers = {}
        for r in data.get("results", []):
            q = (r.get("question") or "").strip()
            a = strip_verbal_confidence(str(r.get("generation_meta", {}).get("final_answer") or ""))
            if not q:
                continue
            if not a:
                raise SystemExit(f"[ABORT] no delivered answer for '{q[:60]}' in {path.name}")
            answers[q] = a
        per_cond[cond] = answers

    shared = set.intersection(*(set(a) for a in per_cond.values()))
    for cond, answers in per_cond.items():
        missing = set(answers) ^ shared
        if missing:
            raise SystemExit(f"[ABORT] {cond} does not cover the same questions as the "
                             f"others; first difference: {sorted(missing)[0][:70]}")

    order = [q.strip() for q in
             ((r.get("question") or "") for r in chosen[wanted[0]][1]["results"])
             if q.strip() in shared]

    questions = [{"question_index": i,
                  "patient_query": q,
                  "answers": {c: per_cond[c][q] for c in wanted}}
                 for i, q in enumerate(order, start=1)]

    provenance = {
        "built_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "conditions": wanted,
        "n_questions": len(questions),
        "runs": {c: {"file": p.name, "metadata": d.get("metadata", {})}
                 for c, (p, d) in chosen.items()},
        "assignment": ("decided per participant in study_data.assign_items(); "
                       "condition(question i) = conditions[(i - 1 + offset_p) mod C]"),
    }
    bundle = {"meta": {"backend": chosen[wanted[0]][1]["metadata"].get("mode", "?"),
                       **provenance},
              "questions": questions}

    OUT_BUNDLE.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_PROVENANCE.write_text(json.dumps(provenance, indent=2, ensure_ascii=False),
                              encoding="utf-8")

    print(f"\n[OK] {len(questions)} questions x {len(wanted)} conditions -> {OUT_BUNDLE.name}")
    print(f"     conditions: {', '.join(wanted)}")
    print(f"     provenance -> {OUT_PROVENANCE.name}")
    print("\nNext: python screen_patient_answers.py questions.json")


if __name__ == "__main__":
    main()
