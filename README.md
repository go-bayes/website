# Joseph A. Bulbulia - Academic Website

**Under Construction**
(Still needs to be checked; needs better LaTeX styling)

## Website Structure

```
website/
├── _quarto.yml          # Quarto configuration (site settings, navigation)
├── index.qmd            # Homepage
├── cv/
│   ├── cv.qmd           # CV page (pulls from publications.bib)
│   ├── publications.bib # Master bibliography file (single source of truth)
│   └── publications_orcid_backup.bib  # Raw ORCID export (backup)
├── research/            # Research pages
├── posts/               # Blog posts (if any)
├── resources/           # Static resources
├── styles/              # Custom CSS styles
├── src/                 # Python scripts for bibliography management
│   ├── README.md        # Documentation for scripts
│   ├── clean_publications_v5.py
│   └── merge_pdfs_v3.py
├── _site/               # Generated website (do not edit directly)
└── .quarto/             # Quarto cache
```

## How the CV Works

The CV (`cv/cv.qmd`) automatically pulls all publications from `cv/publications.bib`:

```yaml
bibliography: publications.bib
nocite: '@*'  # include all entries, even if not cited
csl: apa-cv.csl  # citation style
```

**To update publications:**
1. Edit `cv/publications.bib` directly, OR
2. Run the Python scripts in `src/` to process ORCID exports
3. Import Google Scholar BibTeX in one command:
```bash
python3 src/clean_publications_v5.py --input cv/scholar_export.bib --output cv/publications.bib
```
4. Merge Google Scholar BibTeX with your current bibliography:
```bash
python3 src/clean_publications_v5.py --input cv/scholar_export.bib --output cv/publications.bib --merge-existing
```

**To add a new publication:**
Add a BibTeX entry to `cv/publications.bib`:
```bibtex
@article{Author_Year_identifier,
  author = {Bulbulia, Joseph A. and ...},
  title = {Title of the paper},
  journal = {Journal Name},
  year = {2025},
  doi = {10.xxxx/xxxxx},
  url = {https://...},
  file = {https://link-to-pdf.pdf},  # Optional PDF link
}
```

## Building the Website

### Prerequisites

- [Quarto](https://quarto.org/docs/get-started/) (install via `brew install quarto` on macOS)
- Python 3.x (for bibliography scripts)

### Commands

```bash
# render the entire website
quarto render

# render just the CV
quarto render cv/cv.qmd

# Preview with live reload
quarto preview

# render to PDF (requires LaTeX)
quarto render cv/cv.qmd --to pdf
```

### Output

The rendered website is generated in `_site/`. This folder can be deployed to:
- GitHub Pages
- Netlify (TBA)
- Any static web host

## Bibliography Management

See `src/README.md` for details on the Python scripts.

### Quick workflow:

```bash
# 1. Clean ORCID export and merge PDF links
python3 src/clean_publications_v5.py
python3 src/merge_pdfs_v3.py

# 2. Render
quarto render
```

## Links

- **ORCID:** [0000-0002-5861-2056](https://orcid.org/0000-0002-5861-2056)
- **ACCEPT at VUW:** [https://go-bayes.github.io/accept/](https://go-bayes.github.io/accept/)
