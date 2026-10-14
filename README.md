# The submission checker for Word

Most people write papers in Word. This version of the journal
submission checker reads `.docx` files directly.

## Run it

```
> @agent-journal-submission-checker-word check @paper.docx
```

That is the whole workflow. The agent extracts the document itself and reports
back.

## Installing

```bash
git clone https://github.com/amontan6/journal-submission-checker-word.git
sh journal-submission-checker-word/install.sh
```

This copies the agent to `~/.claude/agents/` and the extractor to
`~/.claude/checker-word-kit/` (or under `$CLAUDE_CONFIG_DIR` if you set it).
Restart Claude Code afterwards. To update, `git pull` and re-run `install.sh`.

The extractor is **standard-library Python 3 only** —
no `pip install`, no pandoc, no `python-docx`. It was written that way on
purpose: a submission checker that needs a working Python environment first is
a checker people skip.

```bash
python3 -I docx_extract.py paper.docx -o paper-extracted.txt
```

Run it yourself any time you want to see what the agent sees. The output opens
with an inventory block — tracked changes, comments, field codes, hyperlinks,
tables, equations — then the body with inline markers.

## What it checks

The five areas, in the order the report comes back:

1. **Repository accessibility** — every GitHub/GitLab/Zenodo/OSF link fetched,
   display text compared against real target, README and license checked,
   database accessions (GenBank, PDB, SRA, GEO) confirmed public rather than
   held. Recommends a DOI-minted archive wherever only a bare repo link appears.
2. **Preprint publication status** — every bioRxiv/arXiv/medRxiv citation
   searched for a published version, **including whether the title changed**,
   which is the one that bites. A 2022 preprint title carrying a 2023 journal
   DOI will not match the record.
3. **Bibliographic completeness** — in-text citations against the reference list
   in both directions, missing fields, `et al.` truncation, and a missing DOI
   distinguished from a style that omits DOIs. Uses field codes to separate
   managed entries from hand-typed ones.
4. **Language and style** — "our work" → "our study", placeholders like
   `[co-authors]` and `TODO`, vague quantitative claims, mixed
   British/American spelling.
5. **Word-native integrity** — unaccepted tracked changes, unresolved comments,
   broken cross-references, and callouts pointing at tables or figures that do
   not exist.

Only section 5 needs the `.docx`. Hand it a `.txt` or PDF and it still runs
1–4, says section 5 was skipped, and offers to re-run.

## Formats

| Format | Works? |
| --- | --- |
| `.docx` | Yes, directly. Recommended. |
| `.dotx` (Word template) | Yes. |
| `.txt`, `.md`, PDF | Yes, but section 5 is skipped. |
| `.doc` (pre-2007 binary) | No — Save As `.docx` first. |
| Google Docs | Download as `.docx` (File → Download → Microsoft Word). |
| `.pages` | No — Export to Word first. |

**Google Docs users:** download as `.docx`, not plain text. The Google export
carries tracked changes ("suggestions") and comments into the `.docx`, so you
get all five checks.

> **One caution about exports, if you make one anyway.** If you use Zotero,
> Mendeley or EndNote, your citations are live field codes. Exporting to plain
> text flattens them. Harmless to the original as long as you *Save As* a new
> file — but do not save over your working document. Reading the `.docx`
> directly avoids the question.

## Files here

- `journal-submission-checker-word.md` — the agent
- `docx_extract.py` — the extractor the agent calls (stdlib only)
- `install.sh` — installs the agent and extractor for Claude Code
