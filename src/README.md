# Source Code Documentation

This folder contains Python scripts for managing the publications bibliography.

## Scripts

### `clean_publications_v5.py`

**Purpose:** Cleans and deduplicates BibTeX entries from the ORCID backup file.

**What it does:**
1. Reads `cv/publications_orcid_backup.bib` (raw export from ORCID)
2. Removes HTML artifacts and malformed entries
3. Filters to only include publications authored by Joseph Bulbulia
4. Removes duplicate entries (by DOI or title)
5. Generates unique citation keys in format `Author_Year_DOI`
6. Outputs cleaned entries to `cv/publications.bib`

**Usage:**
```bash
cd /path/to/website
python3 src/clean_publications_v5.py
```

### `merge_pdfs_v3.py`

**Purpose:** Merges PDF links from the LaTeX CV into the BibTeX file.

**What it does:**
1. Reads the original LaTeX CV file (`bulbulia-j-a-cv.tex`)
2. Extracts PDF links from `\href{URL}{PDF}` patterns
3. Matches entries by DOI or title to the cleaned publications.bib
4. Adds `file = {URL}` field to matched entries
5. Outputs updated `cv/publications.bib`

**Usage:**
```bash
cd /path/to/website
python3 src/merge_pdfs_v3.py
```

## Workflow

To update publications:

1. **Update ORCID backup** (if needed):
   - Export publications from [ORCID](https://orcid.org/0000-0002-5861-2056)
   - Save as `cv/publications_orcid_backup.bib`

2. **Clean and process:**
   ```bash
   python3 src/clean_publications_v5.py
   python3 src/merge_pdfs_v3.py
   ```

3. **Add any manual entries** (software, book chapters, etc.) directly to `cv/publications.bib`

4. **Render the website:**
   ```bash
   quarto render
   ```

## Dependencies

- Python 3.x
- bibtexparser (`pip install bibtexparser`)
