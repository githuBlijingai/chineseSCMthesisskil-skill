# Literature And PDF Workflow

Use this reference when a thesis needs literature review, related work, citation cleanup, citation placement, or reference extraction from PDF papers.

## Inputs

Preferred inputs:

- PDF papers in one folder
- thesis title, abstract, keywords, chapter outline, or `thesis-ai-spec.yaml`
- school reference style requirement
- existing reference list, if any

## CNKI Literature Search (Auto)

The workbench intelligently manages literature sources:

1. **If references >= 25**: Uses existing references, skips CNKI
2. **If references < 25**: Auto-enables CNKI to supplement literature pool
3. **Explicit control**: Set `literature.cnki.enabled: true/false` in `thesis-ai-spec.yaml` to override auto-detection

This ensures the thesis has adequate literature support regardless of user input.

### Configuration

```yaml
literature:
  cnki:
    enabled: true
    server_command: "uvx --from git+https://github.com/h-lu/cnki-mcp cnki-mcp"
    custom_terms: []  # Optional: override search keywords
    max_results: 10
    min_citations: 0
    year_range: [2020, 2026]
```

### Search Keyword Priority

1. `literature.cnki.custom_terms` - User-defined keywords (highest priority)
2. `thesis.keywords` - Thesis keywords from spec
3. Auto-extracted from `thesis.title` - Fallback if no keywords set

### Manual Trigger

```powershell
# Build CNKI literature pool
python .\scripts\literature\build_cnki_pool.py `
  --spec .\thesis-ai-standard\templates\thesis-ai-spec.yaml `
  --output .\paper-context\literature\

# Or use auto-build (checks config)
python .\scripts\literature\auto_build_literature.py `
  --spec .\thesis-ai-standard\templates\thesis-ai-spec.yaml
```

### Outputs

```text
paper-context/literature/
  cnki-pool.json           # Full paper metadata
  cnki-references.txt      # GB/T 7714 formatted references
  citation-registry.json   # Citation tracking (generated during writing)
```

### Citation Management

During `draft_chapters`, the workbench uses `CitationManager` to:

1. Load `cnki-pool.json`
2. Match papers to paragraph content by keyword similarity
3. Insert citation marks like `[1]`, `[2,3]` in body text
4. Generate final reference list in GB/T 7714 format

```python
from scripts.literature import CitationManager

manager = CitationManager(pool_path)
matched = manager.match_papers(paragraph_text)
for paper in matched:
    mark = manager.generate_citation_mark(paper)  # e.g., "[1]"
references = manager.generate_references_list()  # Final list
```

## PDF Reference Extraction

Run:

```powershell
python .\scripts\literature\extract_pdf_references.py .\papers --out .\paper-context\literature
```

Outputs:

```text
paper-context/literature/
  reference-extraction.json
  reference-extraction.md
```

The script extracts candidate reference sections. Treat output as raw evidence. Verify bibliographic fields manually or with trusted sources before final formatting.

## Citation Cross-References

If a topic outline exists, create a citation cross-reference index:

`paper-context/topics.md` is a lightweight topic file. It can be drafted from the confirmed outline, `thesis-ai-spec.yaml`, or user-provided keywords. Use one topic per bullet; include methods, domain terms, chapter names, and known acronyms that should guide citation placement.

Example:

```markdown
# Thesis Topics

- Chapter 1: research background; domestic and international status; problem definition
- Chapter 2: key theories; core technologies; evaluation methods
- Chapter 3: requirement analysis; system architecture; database design
- Chapter 4: implementation modules; algorithms; user workflow
- Chapter 5: testing; experiment results; comparison baseline
- Keywords: recommender system; collaborative filtering; Vue; Spring Boot
```

```powershell
python .\scripts\literature\build_literature_crossrefs.py .\paper-context\literature\reference-extraction.json --topics .\paper-context\topics.md --out .\paper-context\literature\citation-crossrefs.md --json-out .\paper-context\literature\citation-crossrefs.json
```

Cross-reference rules:

- Match references to claims by overlap with topic terms, methods, domain words, and known acronyms.
- Prefer recent and directly relevant papers for research status sections.
- Prefer method papers for method/theory sections.
- Prefer system/application papers for design comparison sections.
- Do not cite a paper merely because a keyword appears once.
- Mark weak matches as `needs_check`.

After generating cross-references, update `thesis-ai-standard/templates/citation-crossref-register.yaml` or a project copy of it. The register is the closure layer:

- body claim -> citation candidate
- citation candidate -> verified reference-list entry
- reference-list entry -> body citation location
- unresolved candidate -> `needs_check`, `rejected`, or `missing_source`

## Writing Literature Review

Structure by theme, not by one-paper-per-paragraph:

1. Define the research or engineering problem.
2. Group literature into 2-4 themes.
3. Compare methods, data, systems, or conclusions.
4. Identify the gap that the thesis addresses.
5. Connect the gap to the thesis work.

Avoid:

- fabricated author/year/venue
- references not cited in body text
- body citations missing from final reference list
- DOI or URL hallucination
- "AI found" or "the uploaded paper says" wording

## Final Checks

- Every cited source appears in the reference list.
- Every reference-list item is cited, unless school rules allow uncited background references.
- `citation-crossref-register.yaml` or equivalent notes record the body/reference closure.
- Reference format follows `standard-profile.yaml`.
- Extraction uncertainty is resolved before final submission.
