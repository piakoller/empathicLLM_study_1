"""cleanup_user_study.py — tidy this folder, and nothing outside it.

Scope is this directory only. The benchmark repository next door is not touched,
not read and not reported on.

Two kinds of action, kept apart on purpose:

  remove   only `__pycache__` and loose `*.pyc`. Python rebuilds them from the
           source beside them, so parking them somewhere would be theatre.
  move     everything else — into `_attic/<date>/` for dead weight, into
           `docs/` for the three documents that are not the entry point.
           Nothing is deleted.

Every move states its reason. Each reason was checked against this folder, not
assumed: "referenced nowhere" means a grep over the .py files found no use, and
"identical" means the JSON was parsed and compared.

Usage
-----
    python cleanup_user_study.py            # dry run, changes nothing
    python cleanup_user_study.py --apply
"""

from __future__ import annotations

import argparse
import datetime
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Dead weight. Nothing in app.py, study_*.py or questionnaire_*.py reads any of
# these; checked by grepping this folder's .py files for the filenames and for
# the "data/" directory.
ATTIC = {
    "questionnaire_questions copy.json":
        "scratch draft, not valid JSON — it holds a commented-out 'Empathie (NURSE)' "
        "section, so it is a design idea, not a backup. questionnaire_questions.json is "
        "what questionnaire_data.py loads.",
    "data/uq_benchmark_20260703T123617.json":
        "1.0 MB, read by nothing here; identical JSON to the copy in the benchmark repo's "
        "results/archive/2026-06_07_benchmarks/ (only the whitespace differs)",
    "data/uq_benchmark_20260703T164603.json":
        "1.0 MB, read by nothing here; identical JSON to the copy in the benchmark repo's "
        "results/archive/2026-06_07_benchmarks/ (only the whitespace differs)",
    "data/psma_sample_questions.json":
        "byte-identical to the benchmark repo's data/psma_sample_questions.json, which is "
        "the copy the pipeline actually reads. The 20 questions in it are the 20 in the "
        "study bundle, so nothing is lost by keeping one copy.",
    "questions_SUPERSEDED_mixed_runs.json":
        "the study file used until 15 Sep 2026, built from two different inference "
        "backends. Kept as the record of what earlier participants saw.",
}

# Documents that are not the entry point. README.md stays at the top and points
# at them.
DOCS = {
    "README_questionnaire.md": "the questionnaire item list",
    "PATCH_NOTES.md": "why condition assignment moved into study_data.py",
    "PATIENT_ANSWERS_BEFORE_STUDY.md": "what is wrong with the generated answers",
}


def human(n: int) -> str:
    return f"{n / 1e6:.2f} MB" if n >= 1e5 else f"{n / 1e3:.1f} kB"


def tree_size(p: Path) -> int:
    return p.stat().st_size if p.is_file() else sum(
        f.stat().st_size for f in p.rglob("*") if f.is_file())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="actually change files")
    args = ap.parse_args()
    apply, stamp = args.apply, datetime.date.today().isoformat()

    print(f"folder : {HERE}")
    print(f"mode   : {'APPLY' if apply else 'dry run — nothing will change'}\n")

    # --- remove -------------------------------------------------------------
    caches = [p for p in HERE.rglob("__pycache__") if ".git" not in p.parts and p.is_dir()]
    loose = [p for p in HERE.rglob("*.pyc")
             if ".git" not in p.parts and not any(c in p.parents for c in caches)]
    targets = sorted(caches) + sorted(loose)
    print(f"remove  {len(targets)} compiled-bytecode items, "
          f"{human(sum(tree_size(p) for p in targets))}")
    for p in targets:
        print(f"    {'rm  ' if apply else 'would rm  '}{p.relative_to(HERE)}")
        if apply:
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)

    # --- park ---------------------------------------------------------------
    attic = HERE / "_attic" / stamp
    print(f"\nmove    dead weight into _attic/{stamp}/  (nothing deleted)")
    for rel, why in ATTIC.items():
        src = HERE / rel
        if not src.exists():
            print(f"    (gone already)  {rel}")
            continue
        print(f"    {'mv  ' if apply else 'would mv  '}{rel}   {human(src.stat().st_size)}")
        print(f"        why: {why}")
        if apply:
            attic.mkdir(parents=True, exist_ok=True)
            dest = attic / src.name
            if dest.exists():
                print("        SKIPPED: a file of that name is already in the attic")
                continue
            shutil.move(str(src), str(dest))

    # data/ exists only for the three files above
    data = HERE / "data"
    if data.is_dir() and not any(data.iterdir()):
        print(f"    {'rmdir  ' if apply else 'would rmdir  '}data/   (empty once the above moved)")
        if apply:
            data.rmdir()

    # --- docs ---------------------------------------------------------------
    docs = HERE / "docs"
    print("\nmove    documents into docs/,  README.md stays at the top")
    for name, what in DOCS.items():
        src = HERE / name
        if not src.exists():
            print(f"    (not here)  {name}")
            continue
        print(f"    {'mv  ' if apply else 'would mv  '}{name}  ->  docs/{name}     ({what})")
        if apply:
            docs.mkdir(exist_ok=True)
            dest = docs / name
            if dest.exists():
                print("        SKIPPED: already in docs/")
                continue
            shutil.move(str(src), str(dest))

    # --- report -------------------------------------------------------------
    print("\nnot decided here — these need a git command and a judgement\n")
    print("    .streamlit/secrets.toml  holds the MongoDB connection string.")
    print("       .gitignore covers it today, but that rule is dated 25 June and the")
    print("       repository starts 16 June, so check the window:")
    print("           git log --all -- .streamlit/secrets.toml")
    print("       If it was ever committed, rotate the password; deleting it now does")
    print("       not unpublish what was pushed.\n")
    print("    one object in .git is about 88 MB (25 June). Every clone carries it.")
    print("           git rev-list --objects --all \\")
    print("             | git cat-file --batch-check '%(objecttype) %(objectname) "
          "%(objectsize) %(rest)' \\")
    print("             | sort -k3 -n -r | head")
    print("       Removing it means rewriting history (git filter-repo) and force-pushing.")

    print("\ndone." if apply else "\ndry run only. Re-run with --apply to change anything.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
