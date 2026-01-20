#!/usr/bin/env python3
"""
convert LaTeX CV bibitem entries to BibTeX format
preserves PDF links from \href commands
"""

import re
import sys

def extract_bibitems(latex_file):
    """Extract all \bibitem entries from LaTeX CV"""
    with open(latex_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # find all bibitem entries
    # pattern: \bibitem{key} followed by text until next \bibitem or \subsubsection
    pattern = r'\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem\{|\\subsubsection\*\{|\\end\{document\})'
    matches = re.findall(pattern, content, re.DOTALL)

    return matches

def extract_pdf_link(text):
    """Extract PDF URL from \href{URL}{PDF} pattern"""
    pdf_match = re.search(r'\\href\{([^}]+)\}\{PDF\}', text)
    if pdf_match:
        return pdf_match.group(1)
    return None

def extract_doi(text):
    """Extract DOI from various formats"""
    # try \url{https://doi.org/...}
    doi_match = re.search(r'\\url\{https://doi\.org/([^}]+)\}', text)
    if doi_match:
        return doi_match.group(1)

    # try \href{https://doi.org/...}
    doi_match = re.search(r'\\href\{https://doi\.org/([^}]+)\}', text)
    if doi_match:
        return doi_match.group(1)

    # try DOI: format
    doi_match = re.search(r'DOI:\s*\\href\{[^}]*doi\.org/([^}]+)\}', text)
    if doi_match:
        return doi_match.group(1)

    return None

def clean_latex(text):
    """Remove LaTeX formatting commands"""
    # remove bold
    text = re.sub(r'\{\\bf\s+([^}]+)\}', r'\1', text)
    # remove textcolor
    text = re.sub(r'\\textcolor\{[^}]+\}\{([^}]+)\}', r'\1', text)
    # remove newblock
    text = text.replace('\\newblock', '')
    # remove emph
    text = re.sub(r'\\emph\{([^}]+)\}', r'\1', text)
    # remove tilde for non-breaking space
    text = text.replace('~', ' ')
    # clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def convert_to_bibtex(key, entry_text):
    """Convert bibitem entry to BibTeX format"""
    entry_text = clean_latex(entry_text)

    # extract components
    pdf_url = extract_pdf_link(entry_text)
    doi = extract_doi(entry_text)

    # basic structure - would need more sophisticated parsing for real conversion
    # for now, just create a misc entry with the raw text
    bib_entry = f"@misc{{{key},\n"
    bib_entry += f"  note = {{{entry_text}}}"

    if doi:
        bib_entry += f",\n  doi = {{{doi}}}"

    if pdf_url:
        bib_entry += f",\n  url = {{{pdf_url}}}"

    bib_entry += "\n}\n"

    return bib_entry

def main():
    latex_file = sys.argv[1] if len(sys.argv) > 1 else '/Users/joseph/v-project Dropbox/Joseph Bulbulia/00Bulbulia Pubs/cv/bulbulia-j-a-cv.tex'

    entries = extract_bibitems(latex_file)
    print(f"% Extracted {len(entries)} entries from LaTeX CV")
    print(f"% Note: This is a rough conversion - manual cleanup needed\n")

    for key, text in entries:
        bib_entry = convert_to_bibtex(key, text)
        print(bib_entry)

if __name__ == '__main__':
    main()
