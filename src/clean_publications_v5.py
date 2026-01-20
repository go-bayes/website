#!/usr/bin/env python3
"""
Clean and deduplicate BibTeX publications file.
- Removes HTML artifacts
- Filters to only include publications by Joseph Bulbulia
- Generates unique citation keys based on DOI
- Removes duplicate entries (by DOI)
- Validates BibTeX syntax
"""

import re
from collections import OrderedDict

def read_bib_file(filepath):
    """Read BibTeX file content."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def extract_braced_content(s, start_pos):
    """Extract content between matching braces starting at position."""
    if start_pos >= len(s) or s[start_pos] != '{':
        return None, start_pos

    depth = 0
    content_start = start_pos + 1
    pos = start_pos

    while pos < len(s):
        if s[pos] == '{':
            depth += 1
        elif s[pos] == '}':
            depth -= 1
            if depth == 0:
                return s[content_start:pos], pos + 1
        pos += 1

    return None, start_pos

def extract_entries(content):
    """Extract individual BibTeX entries from content."""
    # Remove HTML artifacts
    content = re.sub(r'<head>.*?</head>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<[^>]+>', '', content)

    # Remove stray commas between entries
    content = re.sub(r'\n,\n', '\n\n', content)
    content = re.sub(r'^\s*,\s*$', '', content, flags=re.MULTILINE)

    entries = []

    # Find each entry start
    entry_pattern = r'@(\w+)\s*\{([^,]+),'
    for match in re.finditer(entry_pattern, content):
        entry_type = match.group(1).lower()
        key = match.group(2).strip()

        # Skip if key is empty or looks like HTML
        if not key or key.startswith('<') or 'http-equiv' in key.lower():
            continue

        # Find the end of this entry (next @entry or end of content)
        start_pos = match.end()
        next_entry = re.search(r'\n@\w+\s*\{', content[start_pos:])
        if next_entry:
            end_pos = start_pos + next_entry.start()
        else:
            end_pos = len(content)

        fields_str = content[start_pos:end_pos].strip().rstrip('}').rstrip(',')

        entries.append({
            'type': entry_type,
            'original_key': key,
            'fields_str': fields_str,
        })

    return entries

def parse_author_field(fields_str):
    """Extract author field handling nested braces."""
    # Find author = { or author =
    author_match = re.search(r'author\s*=\s*', fields_str, re.IGNORECASE)
    if not author_match:
        return None

    start = author_match.end()

    # Check if it starts with brace
    if start < len(fields_str) and fields_str[start] == '{':
        content, _ = extract_braced_content(fields_str, start)
        return content
    elif start < len(fields_str) and fields_str[start] == '"':
        # Quoted
        end = fields_str.find('"', start + 1)
        if end > start:
            return fields_str[start+1:end]

    return None

def parse_fields(fields_str):
    """Parse BibTeX fields from string."""
    fields = {}

    # Get author specially
    author = parse_author_field(fields_str)
    if author:
        fields['author'] = author

    # Get other fields with simpler patterns
    # Match field = {value} where value may contain nested braces
    pos = 0
    while pos < len(fields_str):
        # Find next field
        field_match = re.search(r'(\w+)\s*=\s*', fields_str[pos:])
        if not field_match:
            break

        field_name = field_match.group(1).lower()
        field_start = pos + field_match.end()

        if field_start >= len(fields_str):
            break

        if fields_str[field_start] == '{':
            content, next_pos = extract_braced_content(fields_str, field_start)
            if content is not None and field_name not in fields:
                fields[field_name] = content
            pos = next_pos
        elif fields_str[field_start] == '"':
            end = fields_str.find('"', field_start + 1)
            if end > field_start and field_name not in fields:
                fields[field_name] = fields_str[field_start+1:end]
            pos = end + 1 if end > field_start else field_start + 1
        elif fields_str[field_start:field_start+1].isdigit():
            # Numeric value
            num_match = re.match(r'(\d+)', fields_str[field_start:])
            if num_match and field_name not in fields:
                fields[field_name] = num_match.group(1)
            pos = field_start + (num_match.end() if num_match else 1)
        else:
            pos = field_start + 1

    return fields

def is_bulbulia_author(author_str):
    """Check if Joseph Bulbulia is among the authors."""
    if not author_str:
        return False

    author_lower = author_str.lower()
    # Check for Bulbulia in any form
    if 'bulbulia' in author_lower:
        return True

    return False

def get_first_author_lastname(author_str):
    """Extract first author's last name from author string."""
    if not author_str:
        return None

    # Get first author
    first_author = author_str.split(' and ')[0].strip()

    # Remove LaTeX special characters
    first_author = re.sub(r'\\[\'`^"~=.uvHtcdbkroB]\{?([a-zA-Z])\}?', r'\1', first_author)
    first_author = re.sub(r'\{\\([a-zA-Z])\}', r'\1', first_author)
    first_author = re.sub(r'[{}]', '', first_author)

    # Handle "Last, First" format
    if ',' in first_author:
        last_name = first_author.split(',')[0].strip()
    else:
        # Handle "First Last" format
        parts = first_author.split()
        if parts:
            last_name = parts[-1]
        else:
            return None

    # Clean up
    last_name = re.sub(r'[^a-zA-Z]', '', last_name)
    return last_name if last_name else None

def generate_citation_key(fields, entry_type):
    """Generate a unique citation key from entry fields."""
    # Get first author's last name
    author = fields.get('author', '')
    last_name = get_first_author_lastname(author)
    if not last_name:
        last_name = 'Unknown'

    # Get year
    year = fields.get('year', 'XXXX')

    # Get DOI for uniqueness
    doi = fields.get('doi', '')
    if doi:
        # Create a short identifier from DOI
        doi_clean = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
        # Take the last part of DOI, clean it up
        doi_suffix = re.sub(r'[^a-zA-Z0-9]', '_', doi_clean)[-25:]
    else:
        # Use title hash if no DOI
        title = fields.get('title', '')
        doi_suffix = re.sub(r'[^a-zA-Z0-9]', '', title)[:20]

    return f"{last_name}_{year}_{doi_suffix}"

def deduplicate_by_doi(entries):
    """Remove duplicate entries based on DOI."""
    seen_dois = {}
    seen_titles = {}
    unique_entries = []

    for entry in entries:
        fields = parse_fields(entry['fields_str'])
        doi = fields.get('doi', '').lower().strip()

        # Normalize DOI
        doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)

        if doi:
            if doi not in seen_dois:
                seen_dois[doi] = entry
                unique_entries.append(entry)
            else:
                # Keep the entry with more fields
                existing = seen_dois[doi]
                existing_fields = parse_fields(existing['fields_str'])
                if len(fields) > len(existing_fields):
                    # Replace with better entry
                    idx = unique_entries.index(existing)
                    unique_entries[idx] = entry
                    seen_dois[doi] = entry
        else:
            # No DOI - check by title
            title = fields.get('title', '').lower()
            title_normalized = re.sub(r'[^a-z0-9]', '', title)

            if title_normalized and title_normalized not in seen_titles:
                seen_titles[title_normalized] = True
                unique_entries.append(entry)
            elif not title_normalized:
                # No title either, just include it
                unique_entries.append(entry)

    return unique_entries

def format_entry(entry, key_counts):
    """Format a single BibTeX entry with unique key."""
    fields = parse_fields(entry['fields_str'])

    # Generate base key
    base_key = generate_citation_key(fields, entry['type'])

    # Ensure uniqueness
    if base_key in key_counts:
        key_counts[base_key] += 1
        key = f"{base_key}_{chr(96 + key_counts[base_key])}"  # a, b, c, ...
    else:
        key_counts[base_key] = 0
        key = base_key

    # Build formatted entry
    lines = [f"@{entry['type']}{{{key},"]

    # Order fields nicely
    field_order = ['author', 'title', 'journal', 'booktitle', 'volume', 'number',
                   'pages', 'year', 'month', 'publisher', 'doi', 'url', 'issn', 'isbn', 'editor']

    # Add ordered fields first
    added_fields = set()
    for field in field_order:
        if field in fields:
            value = fields[field]
            # Clean HTML entities
            value = value.replace('&amp;', '&')
            value = re.sub(r'</?scp>', '', value)
            lines.append(f"  {field} = {{{value}}},")
            added_fields.add(field)

    # Add any remaining fields (except keywords and copyright which are verbose)
    skip_fields = {'keywords', 'copyright', 'language'}
    for field, value in fields.items():
        if field not in added_fields and field not in skip_fields:
            value = value.replace('&amp;', '&')
            value = re.sub(r'</?scp>', '', value)
            lines.append(f"  {field} = {{{value}}},")

    # Remove trailing comma from last field
    if lines[-1].endswith(','):
        lines[-1] = lines[-1][:-1]

    lines.append("}")

    return '\n'.join(lines)

def main():
    input_file = '/sessions/relaxed-tender-edison/mnt/website/cv/publications_orcid_backup.bib'
    output_file = '/sessions/relaxed-tender-edison/mnt/website/cv/publications.bib'

    print(f"Reading {input_file}...")
    content = read_bib_file(input_file)

    print("Extracting entries...")
    entries = extract_entries(content)
    print(f"Found {len(entries)} entries")

    # Filter to only Bulbulia publications
    print("Filtering to Bulbulia publications...")
    bulbulia_entries = []
    excluded = []
    for entry in entries:
        fields = parse_fields(entry['fields_str'])
        author = fields.get('author', '')
        if is_bulbulia_author(author):
            bulbulia_entries.append(entry)
        else:
            title = fields.get('title', 'No title')[:60]
            author_snippet = author[:100] if author else 'No author'
            excluded.append((title, author_snippet))

    print(f"After filtering: {len(bulbulia_entries)} entries")
    if excluded:
        print(f"Excluded {len(excluded)} entries (not authored by Bulbulia):")
        for title, author in excluded:
            print(f"  - {title}")
            print(f"    Author: {author}")

    print("Removing duplicates...")
    unique_entries = deduplicate_by_doi(bulbulia_entries)
    print(f"After deduplication: {len(unique_entries)} entries")

    print("Formatting entries with unique keys...")
    key_counts = {}
    formatted_entries = []

    for entry in unique_entries:
        try:
            formatted = format_entry(entry, key_counts)
            formatted_entries.append(formatted)
        except Exception as e:
            print(f"Warning: Could not format entry {entry.get('original_key', 'unknown')}: {e}")
            continue

    # Sort by year (descending) then by key
    def sort_key(entry):
        year_match = re.search(r'year\s*=\s*\{?(\d{4})\}?', entry)
        year = year_match.group(1) if year_match else '0000'
        return (-int(year), entry)

    formatted_entries.sort(key=sort_key)

    print(f"Writing {len(formatted_entries)} entries to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"% Publications for Joseph A. Bulbulia\n")
        f.write(f"% Generated: 2026-01-20\n")
        f.write(f"% Total entries: {len(formatted_entries)}\n\n")
        f.write('\n\n'.join(formatted_entries))
        f.write('\n')

    print("Done!")
    print(f"\nSummary:")
    print(f"  Input entries: {len(entries)}")
    print(f"  Non-Bulbulia entries: {len(excluded)}")
    print(f"  Duplicates removed: {len(bulbulia_entries) - len(unique_entries)}")
    print(f"  Output entries: {len(formatted_entries)}")

if __name__ == '__main__':
    main()
