# The submission checker for Word and Google Docs

Most people write papers in Word or Google Docs. This version of the journal
submission checker reads `.docx` files directly — no export step.

## Run it

```
> @agent-journal-submission-checker-word check @paper.docx
```

That is the whole workflow. The agent extracts the document itself and reports
back.

## Why not just export to text first

That was the old advice, and it works, but it throws away the checks that
matter most on the day you submit. A `.docx` is a zip of XML; a plain-text
export is the visible words and nothing else. Four things vanish:

| Lost in export | Why you care |
| --- | --- |
| **Tracked changes** | Submitting with live revisions hands the editor your internal editing history. The journal's conversion may silently accept or reject them. |
| **Comments** | "Is this accession public yet?" is both an embarrassment and a real unanswered question. |
| **Field codes** | Whether a citation came from Zotero or was typed by hand is the single best predictor of which reference entries are wrong. |
| **Hyperlink targets** | A link reading `github.com/lab/project` can point at a private working copy. Both render as plain text identically. |

The last one is worth dwelling on. In `paper-tracked.docx` the Methods and Data
availability sections both contain a link displaying
`github.com/montano-lab/scfv-binding-oracle`. One targets that repository. The
other targets `github.com/amontano-private/scfv-oracle-WORKING-COPY`. Export to
`.txt` and the two are indistinguishable; the agent reading the archive flags it
immediately.

Heading structure survives too, so the agent knows which section a finding is in
and can tell you where to look.

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

- `paper.docx` — test manuscript with eleven planted problems that survive a text export
- `paper-tracked.docx` — test manuscript with six **Word-native** planted problems that do not
- `make_docx.py` — rebuilds `paper.docx` (needs `python-docx`)
- `make_docx_word_native.py` — rebuilds `paper-tracked.docx` (stdlib only)
- `docx_extract.py` — the extractor the agent calls (stdlib only)
- `journal-submission-checker-word.md` — the agent
- `install.sh` — installs the agent and extractor for Claude Code
- `paper.txt`, `paper.md` — old exports, kept so you can compare what they lose

### The Word-native planted problems

In `paper-tracked.docx`, for grading a run:

| # | Problem | Where |
| --- | --- | --- |
| W1 | Unaccepted tracked replacement: "useful" deleted, "state-of-the-art" inserted | Abstract |
| W2 | Unaccepted tracked deletion, "Nobody has attempted this for scFvs." | Introduction |
| W3 | Two unresolved comments, one asking whether the accession is public | Introduction, Methods |
| W4 | Hyperlink displaying the public repo, targeting a private working copy | Data availability |
| W5 | Broken cross-reference, "Error! Reference source not found." | Methods, Binding assay |
| W6 | Live Zotero field code for a reference absent from the list | Data availability |

W6 is the interesting one: Koenig et al. (2017) is cited through a real Zotero
field and has no entry in the reference list. The field code proves the citation
was inserted from a library, which tells the author exactly where to look.

W1 is a del/ins **pair**, which is what Word writes when you replace a word
rather than add one. A grader should expect both halves reported, and should
expect the agent to notice that accepting the insertion leaves an unsupported
"state-of-the-art" claim with no comparator in the paper.

A good run also catches two things not in this table, because they emerge from
the content rather than the markup: GenBank MZ457891 resolves to an unrelated
rRNA sequence, and the inline equation reports `AUC = 0.78 ± 0.04` while Table 1
gives 0.78 with no spread.

The eleven problems planted in `paper.docx` are listed in the README of the
LaTeX version of this checker, which is not part of this repository.
