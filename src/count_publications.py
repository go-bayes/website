#!/usr/bin/env python3
"""count publications by type from tagged LaTeX CV and cross-check against website bib.

reads `% @type{...}` tags from the LaTeX CV and compares entries with
the website's publications.bib using normalised title matching.
"""

import re
import unicodedata
from pathlib import Path

CV_PATH = Path(
    "/Users/joseph/v-project Dropbox/Joseph Bulbulia/00Bulbulia Pubs/cv/bulbulia-j-a-cv.tex"
)
BIB_PATH = Path("/Users/joseph/GIT/website/cv/publications.bib")


def normalise_title(title: str) -> str:
    """normalise a title for fuzzy matching: lowercase, strip punctuation/braces/latex."""
    # remove latex commands
    t = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", title)
    t = re.sub(r"\\[a-zA-Z]+", "", t)
    # remove braces, quotes
    t = t.replace("{", "").replace("}", "").replace('"', "").replace("'", "")
    # normalise unicode
    t = unicodedata.normalize("NFKD", t)
    # lowercase
    t = t.lower()
    # strip non-alphanumeric (keep spaces)
    t = re.sub(r"[^a-z0-9\s]", "", t)
    # collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extract_cv_entries(cv_path: Path) -> list[dict]:
    """extract entries from tagged LaTeX CV with type and title."""
    text = cv_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    entries = []
    pending_type = None
    i = 0

    while i < len(lines):
        line = lines[i]

        type_match = re.match(r"% @type\{(\S+)\}", line)
        if type_match:
            pending_type = type_match.group(1)
            i += 1
            continue

        bib_match = re.match(r"\s*\\bibitem\{([^}]+)\}", line)
        if bib_match and pending_type and not line.strip().startswith("%"):
            key = bib_match.group(1)
            # collect lines until next bibitem or section
            entry_lines = []
            j = i + 1
            while j < len(lines):
                l = lines[j]
                if re.match(r"\s*\\bibitem\{", l) or re.match(r"% @type\{", l):
                    break
                if re.search(r"\\(?:sub)*section\*?\{", l) and not l.strip().startswith("%"):
                    break
                entry_lines.append(l)
                j += 1

            # extract title from \newblock lines
            content = " ".join(entry_lines)
            # first \newblock typically contains the title
            newblocks = re.findall(r"\\newblock\s+(.*?)(?=\\newblock|$)", content)
            title = newblocks[0].strip() if newblocks else ""
            # clean up title
            title = re.sub(r"\\href\{[^}]*\}\{[^}]*\}", "", title)
            title = re.sub(r"\\url\{[^}]*\}", "", title)

            entries.append({
                "key": key,
                "type": pending_type,
                "title": title,
                "norm_title": normalise_title(title),
            })
            pending_type = None
            i = j
            continue

        i += 1

    return entries


def extract_bib_entries(bib_path: Path) -> list[dict]:
    """extract entries from a .bib file with type and title."""
    text = bib_path.read_text(encoding="utf-8")
    # split into entries
    entry_pattern = re.compile(r"@(\w+)\{([^,]+),\s*(.*?)\n\}", re.DOTALL)
    entries = []

    for match in entry_pattern.finditer(text):
        entry_type = match.group(1).lower()
        key = match.group(2).strip()
        body = match.group(3)

        # extract title field
        title_match = re.search(r"title\s*=\s*\{(.*?)\}", body, re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""

        entries.append({
            "key": key,
            "type": entry_type,
            "title": title,
            "norm_title": normalise_title(title),
        })

    return entries


def print_table(counts: dict[str, int], title: str):
    """print a formatted table of counts."""
    print(f"\n{'=' * 40}")
    print(f"  {title}")
    print(f"{'=' * 40}")
    for pub_type in sorted(counts.keys()):
        print(f"  {pub_type:20s} {counts[pub_type]:>5d}")
    print(f"  {'─' * 26}")
    print(f"  {'total':20s} {sum(counts.values()):>5d}")


def main():
    # --- LaTeX CV ---
    if not CV_PATH.exists():
        print(f"tagged CV not found at {CV_PATH}")
        print("run tag_cv.py first to generate it.")
        return

    cv_entries = extract_cv_entries(CV_PATH)
    cv_counts: dict[str, int] = {}
    for e in cv_entries:
        cv_counts[e["type"]] = cv_counts.get(e["type"], 0) + 1
    print_table(cv_counts, "LaTeX CV (tagged)")

    # --- website bib ---
    if not BIB_PATH.exists():
        print(f"\nwebsite bib not found at {BIB_PATH}")
        return

    bib_entries = extract_bib_entries(BIB_PATH)
    bib_counts: dict[str, int] = {}
    for e in bib_entries:
        bib_counts[e["type"]] = bib_counts.get(e["type"], 0) + 1
    print_table(bib_counts, "Website publications.bib")

    # --- title-based cross-check ---
    # use first 6 words of normalised title as match key (reduces false negatives
    # from subtitle differences, truncation, and minor wording variants)
    def title_key(norm_title: str) -> str:
        words = norm_title.split()
        return " ".join(words[:6])

    cv_by_key: dict[str, dict] = {}
    for e in cv_entries:
        if e["norm_title"]:
            k = title_key(e["norm_title"])
            cv_by_key[k] = e

    bib_by_key: dict[str, dict] = {}
    for e in bib_entries:
        if e["norm_title"]:
            k = title_key(e["norm_title"])
            bib_by_key[k] = e

    cv_keys_set = set(cv_by_key.keys())
    bib_keys_set = set(bib_by_key.keys())

    matched = cv_keys_set & bib_keys_set
    cv_only = cv_keys_set - bib_keys_set
    bib_only = bib_keys_set - cv_keys_set

    print(f"\n{'=' * 40}")
    print(f"  cross-check (first 6 words of title)")
    print(f"{'=' * 40}")
    print(f"  LaTeX CV entries:    {len(cv_entries)}")
    print(f"  Website bib entries: {len(bib_entries)}")
    print(f"  matched by title:    {len(matched)}")

    if cv_only:
        print(f"\n  in CV but NOT on website ({len(cv_only)}):")
        for k in sorted(cv_only):
            e = cv_by_key[k]
            print(f"    [{e['type']:12s}] {e['key']}")
            print(f"                  {e['title'][:100]}")

    if bib_only:
        print(f"\n  on website but NOT in CV ({len(bib_only)}):")
        for k in sorted(bib_only):
            e = bib_by_key[k]
            print(f"    [{e['type']:12s}] {e['key']}")
            print(f"                  {e['title'][:100]}")


if __name__ == "__main__":
    main()
