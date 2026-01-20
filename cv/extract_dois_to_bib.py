#!/usr/bin/env python3
"""
extract DOIs from LaTeX CV and fetch BibTeX from doi.org
uses only standard library (no external dependencies)
"""

import re
import sys
import time
import urllib.request
import urllib.error

def extract_dois(latex_file):
    """Extract all DOIs from LaTeX CV"""
    with open(latex_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # match various DOI patterns
    doi_patterns = [
        r'doi\.org/([^\s\}]+)',  # https://doi.org/XXX
        r'DOI:\s*([0-9]{2}\.[0-9]{4,}/[^\s\}]+)',  # DOI: 10.xxxx/yyyy
        r'doi\s*=\s*\{([^\}]+)\}',  # doi = {XXX}
    ]

    dois = set()
    for pattern in doi_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            # clean up the DOI
            doi = match.strip()
            # remove trailing punctuation
            doi = re.sub(r'[,;.\}]+$', '', doi)
            # remove any remaining LaTeX commands
            doi = re.sub(r'\\[a-z]+\{', '', doi)
            doi = doi.replace('}', '')
            if doi and '10.' in doi:
                dois.add(doi)

    return sorted(list(dois))

def fetch_bibtex_from_doi(doi, retry=3):
    """Fetch BibTeX entry from doi.org using urllib"""
    url = f"https://doi.org/{doi}"

    req = urllib.request.Request(
        url,
        headers={
            'Accept': 'application/x-bibtex',
            'User-Agent': 'Python script for academic CV (mailto:joseph.bulbulia@vuw.ac.nz)'
        }
    )

    for attempt in range(retry):
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"% Warning: DOI not found: {doi}", file=sys.stderr)
                return None
            else:
                print(f"% Warning: HTTP {e.code} for {doi}", file=sys.stderr)
                if attempt < retry - 1:
                    time.sleep(2)
        except Exception as e:
            print(f"% Error fetching {doi}: {e}", file=sys.stderr)
            if attempt < retry - 1:
                time.sleep(2)

    return None

def main():
    latex_file = sys.argv[1] if len(sys.argv) > 1 else \
        '/Users/joseph/v-project Dropbox/Joseph Bulbulia/00Bulbulia Pubs/cv/bulbulia-j-a-cv.tex'

    output_file = sys.argv[2] if len(sys.argv) > 2 else \
        '/Users/joseph/GIT/website/cv/publications_from_dois.bib'

    print(f"extracting DOIs from {latex_file}...", file=sys.stderr)
    dois = extract_dois(latex_file)
    print(f"found {len(dois)} unique DOIs", file=sys.stderr)

    with open(output_file, 'w', encoding='utf-8') as out:
        out.write(f"% BibTeX entries fetched from DOIs\n")
        out.write(f"% Extracted from: {latex_file}\n")
        out.write(f"% Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        out.write(f"% Total entries: {len(dois)}\n\n")

        for i, doi in enumerate(dois, 1):
            print(f"fetching {i}/{len(dois)}: {doi}", file=sys.stderr)
            bibtex = fetch_bibtex_from_doi(doi)

            if bibtex:
                out.write(bibtex)
                if not bibtex.endswith('\n'):
                    out.write('\n')
                out.write('\n')

            # rate limiting - be polite to doi.org
            if i < len(dois):
                time.sleep(1)

    print(f"\nwrote BibTeX to {output_file}", file=sys.stderr)
    print(f"successfully fetched {len(dois)} entries", file=sys.stderr)

if __name__ == '__main__':
    main()
