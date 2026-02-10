#!/usr/bin/env python3
"""auto-tag LaTeX CV entries with publication type comments.

inserts `% @type{article}` (or chapter, software, etc.) before each \\bibitem.
uses section headers and content heuristics to classify.

types: article, chapter, edited-book, proceeding, preprint, software, dissertation, review
"""

import re
import sys
from pathlib import Path

CV_PATH = Path(
    "/Users/joseph/v-project Dropbox/Joseph Bulbulia/00Bulbulia Pubs/cv/bulbulia-j-a-cv.tex"
)


def detect_section(line: str) -> str | None:
    """return section name if this line is a section header, else None."""
    line_stripped = line.strip()
    # skip commented-out headers
    if line_stripped.startswith("%"):
        return None
    section_patterns = [
        (r"\\subsection\*\{Software\}", "software"),
        (r"\\subsubsection\*\{Pre-prints\}", "preprint"),
        (r"\\subsubsection\*\{Edited Books\}", "edited-book"),
        (r"\\subsubsection\*\{Dissertation\}", "dissertation"),
        (r"\\subsubsection\*\{\d{4}\}", "year"),
        (r"\\subsubsection\*\{pre-\d{4}\}", "year"),
    ]
    for pattern, name in section_patterns:
        if re.search(pattern, line_stripped):
            return name
    return None


def classify_entry(lines: list[str], section: str) -> str:
    """classify a bibitem entry based on section context and content."""
    # section-based classification takes priority for these
    if section in ("software", "preprint", "edited-book", "dissertation"):
        return section

    # join content for heuristic matching (strip newlines so regex . works)
    text = " ".join(line.rstrip("\n") for line in lines)

    # book reviews
    if re.search(r"[Bb]ook review|Review of \{", text):
        return "review"

    # conference proceedings (actual conference, not journal name)
    # look for "conference" + "(proceedings)" pattern but NOT "Proceedings of the X" journal
    if re.search(r"\(proceedings\)", text, re.IGNORECASE):
        return "proceeding"

    # book chapters: multiple patterns
    # 1. "In <names> (Eds.)" or "(Ed.)" — allow any chars including braces
    if re.search(r"\bIn\b.{1,200}\(Eds?\.\)", text):
        return "chapter"
    # 2. "edited by" following "In {\em"
    if re.search(r"\bIn\b.{1,200}\bedited by\b", text, re.IGNORECASE):
        return "chapter"
    # 3. "\newblock In {\em <title>}" followed by publisher (no volume/issue)
    #    distinguishes chapters from "In press, {\em Journal}"
    if re.search(
        r"\\newblock\s+In\s+\{\\em\b",
        text,
    ) and not re.search(r"In press", text, re.IGNORECASE):
        return "chapter"

    # default: article
    return "article"


def collect_entry_lines(lines: list[str], start_idx: int) -> tuple[list[str], int]:
    """collect all lines belonging to a bibitem entry starting at start_idx.
    returns (entry_lines, end_idx)."""
    entry_lines = [lines[start_idx]]
    i = start_idx + 1
    while i < len(lines):
        line = lines[i]
        # stop at next bibitem, section header, or end of bibliography
        if re.match(r"\s*\\bibitem\{", line):
            break
        if re.search(r"\\(?:sub)*section\*?\{", line) and not line.strip().startswith("%"):
            break
        if re.search(r"\\end\{thebibliography\}", line):
            break
        entry_lines.append(line)
        i += 1
    return entry_lines, i


def tag_cv(input_path: Path, output_path: Path | None = None, dry_run: bool = False):
    """read the cv, classify each bibitem, insert type tags."""
    text = input_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    current_section = "year"  # default before any section header
    in_bibliography = False
    tagged_lines: list[str] = []
    counts: dict[str, int] = {}
    entries: list[dict] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # track bibliography environment
        if r"\begin{thebibliography}" in line:
            in_bibliography = True
            tagged_lines.append(line)
            i += 1
            continue
        if r"\end{thebibliography}" in line:
            in_bibliography = False
            tagged_lines.append(line)
            i += 1
            continue

        if not in_bibliography:
            tagged_lines.append(line)
            i += 1
            continue

        # check for section headers
        sec = detect_section(line)
        if sec is not None:
            current_section = sec
            tagged_lines.append(line)
            i += 1
            continue

        # check for bibitem (skip commented-out entries)
        bibitem_match = re.match(r"\s*\\bibitem\{([^}]+)\}", line)
        if bibitem_match and not line.strip().startswith("%"):
            cite_key = bibitem_match.group(1)
            entry_lines, end_idx = collect_entry_lines(lines, i)
            pub_type = classify_entry(entry_lines, current_section)

            counts[pub_type] = counts.get(pub_type, 0) + 1
            entries.append({"key": cite_key, "type": pub_type, "section": current_section})

            # check if there's already a @type tag on the previous line
            if tagged_lines and re.match(r"% @type\{", tagged_lines[-1]):
                # replace existing tag
                tagged_lines[-1] = f"% @type{{{pub_type}}}\n"
            else:
                # insert new tag
                tagged_lines.append(f"% @type{{{pub_type}}}\n")

            # add all entry lines
            for el in entry_lines:
                tagged_lines.append(el)
            i = end_idx
            continue

        tagged_lines.append(line)
        i += 1

    # print summary
    print("=== publication type counts ===")
    for pub_type in sorted(counts.keys()):
        print(f"  {pub_type:15s}: {counts[pub_type]}")
    print(f"  {'total':15s}: {sum(counts.values())}")

    # print each entry for review
    print("\n=== entry classifications ===")
    for entry in entries:
        print(f"  [{entry['type']:12s}] {entry['key']}")

    if dry_run:
        print("\n[dry run] no file written.")
        return counts, entries

    out = output_path or input_path
    out.write_text("".join(tagged_lines), encoding="utf-8")
    print(f"\ntagged file written to: {out}")
    return counts, entries


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    # tag the original file in-place
    tag_cv(CV_PATH, output_path=CV_PATH, dry_run=dry_run)
