#!/usr/bin/env python3
"""Extract the reviewable content of a .docx, including what an export destroys.

A .docx is a zip of XML. A plain-text export flattens it and throws away the
four things a submission check most wants to see: tracked changes, comments,
reference-manager field codes, and hyperlink targets. This reads them straight
out of the archive.

Usage:
    python3 -I docx_extract.py paper.docx [-o out.txt]

Standard library only -- no python-docx, no pandoc. Works on .docx and .dotx.
"""
import argparse
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def tag(el):
    """Local name of an element, namespace stripped."""
    return el.tag.rsplit("}", 1)[-1] if isinstance(el.tag, str) else ""


def att(el, name, ns=W):
    return el.get(ns + name)


def flat(el, t=W + "t"):
    """All text under el, whitespace collapsed."""
    return " ".join("".join(x.text or "" for x in el.iter(t)).split())


def load(z, part):
    """Root of an archive part, or [] if the part is absent."""
    try:
        return ET.fromstring(z.read(part))
    except KeyError:
        return []


def load_rels(z):
    """Map relationship id -> target, for hyperlink resolution."""
    return {r.get("Id"): r.get("Target", "")
            for r in load(z, "word/_rels/document.xml.rels") if r.get("Id")}


def load_comments(z):
    return {att(c, "id"): {"author": att(c, "author") or "unknown",
                           "date": att(c, "date") or "", "text": flat(c)}
            for c in load(z, "word/comments.xml") if tag(c) == "comment"}


def load_notes(z, part):
    """Map footnote/endnote id -> text, skipping the separator pseudo-notes."""
    out = {}
    for n in load(z, part):
        if tag(n) in ("footnote", "endnote") and att(n, "id") not in ("-1", "0"):
            text = " ".join(filter(None, (flat(p) for p in n.iter(W + "p"))))
            if text:
                out[att(n, "id")] = text
    return out


def heading_prefix(style):
    """Render Word heading styles as Markdown hashes."""
    s = style.lower().replace(" ", "")
    m = re.fullmatch(r"heading(\d)", s)
    level = {"title": 1, "subtitle": 2}.get(s) or (m and min(int(m[1]) + 1, 6))
    return "#" * level + " " if level else ""


def run_text(run, stats, want):
    """Text of a single w:r. `want` is 't' normally, 'delText' inside w:del."""
    pieces = []
    for child in run:
        t = tag(child)
        if t == want:
            pieces.append(child.text or "")
        elif t in ("tab", "br", "cr", "noBreakHyphen"):
            pieces.append({"tab": "\t", "noBreakHyphen": "-"}.get(t, "\n"))
        elif t == "instrText":
            stats["fields"] += 1
            pieces.append(f"[FIELD {' '.join((child.text or '').split())}]")
        elif t in ("drawing", "pict", "object"):
            stats["images"] += 1
            pieces.append("[IMAGE]")
        elif t in ("footnoteReference", "endnoteReference"):
            pieces.append(f"[{t[:-9].upper()} {att(child, 'id')}]")
    return "".join(pieces)


def walk_para(el, ctx, out, mode="t"):
    """Recursive descent over paragraph content, preserving document order."""
    rels, comments, stats = ctx["rels"], ctx["comments"], ctx["stats"]

    def inner(m=mode):
        parts = []
        walk_para(child, ctx, parts, m)
        return "".join(parts)

    for child in el:
        t = tag(child)
        if t == "r":
            out.append(run_text(child, stats, mode))
        elif t == "hyperlink":
            rid, anchor, text = att(child, "id", R), att(child, "anchor"), inner()
            if rid in rels:
                stats["hyperlinks"] += 1
                target, shown = rels[rid], text.strip()
                # Only annotate when the display text hides the real target.
                hidden = shown and shown.rstrip("/") != target.rstrip("/")
                out.append(f"{text}[LINK -> {target}]" if hidden else text)
            elif rid:
                stats["broken_refs"] += 1
                out.append(f"{text}[LINK -> MISSING RELATIONSHIP {rid}]")
            else:
                out.append(f"{text}[INTERNAL LINK -> #{anchor}]" if anchor else text)
        elif t in ("ins", "del", "moveFrom", "moveTo"):
            text = inner("delText" if t in ("del", "moveFrom") else mode)
            if text:
                who = att(child, "author") or "unknown"
                if t == "ins":
                    stats["insertions"] += 1
                    out.append(f"[TRACKED INSERT by {who}: {text}]")
                elif t == "del":
                    stats["deletions"] += 1
                    out.append(f"[TRACKED DELETE by {who}: {text}]")
                else:
                    stats["moves"] += 1
                    out.append(f"[TRACKED {t.upper()}: {text}]")
        elif t == "fldSimple":
            instr = " ".join((att(child, "instr") or "").split())
            shown = inner().strip()
            stats["fields"] += 1
            if "REF" in instr.upper() and "Error!" in shown:
                stats["broken_refs"] += 1
            out.append(f"{shown}[FIELD {instr}]")
        elif t == "commentRangeStart" and att(child, "id") in comments:
            out.append(f"[COMMENT {att(child, 'id')} START]")
        elif t == "commentRangeEnd" and att(child, "id") in comments:
            cid = att(child, "id")
            out.append(f"[COMMENT {cid} END -> {comments[cid]['author']}: "
                       f"{comments[cid]['text']}]")
        elif t == "oMath":
            stats["equations"] += 1
            out.append(f"[EQUATION: {flat(child, M + 't')}]")
        elif t in ("oMathPara", "smartTag", "sdt", "sdtContent", "bookmarkStart"):
            walk_para(child, ctx, out, mode)
        elif t == "pPr":
            stats["format_changes"] += sum(
                tag(g) in ("pPrChange", "rPrChange") for g in child)


def para_to_text(p, ctx):
    out = []
    walk_para(p, ctx, out)
    # Collapse runs of spaces but keep deliberate newlines from <w:br/>.
    text = re.sub(r"[ \t]+", " ", "".join(out)).strip()
    ps = p.find(f"{W}pPr/{W}pStyle")
    style = (att(ps, "val") or "") if ps is not None else ""
    if heading_prefix(style):
        return heading_prefix(style) + text
    return f"[CAPTION] {text}" if style.lower() == "caption" and text else text


def table_to_text(tbl, ctx, number):
    ctx["stats"]["tables"] += 1
    lines = [f"[TABLE {number} START]"]
    for row in tbl.findall(W + "tr"):
        cells = []
        for cell in row.findall(W + "tc"):
            bits = [para_to_text(b, ctx) if tag(b) == "p" else "[NESTED TABLE]"
                    for b in cell if tag(b) in ("p", "tbl")]
            cells.append(" ".join(filter(None, bits)).replace("|", "\\|"))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append(f"[TABLE {number} END]")
    return "\n".join(lines)


def extract_body(z, ctx):
    body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    blocks = []
    for el in body if body is not None else []:
        t = tag(el)
        if t == "p":
            blocks.append(para_to_text(el, ctx))
        elif t == "tbl":
            blocks.append(table_to_text(el, ctx, ctx["stats"]["tables"] + 1))
        elif t == "sdt":
            blocks += [para_to_text(p, ctx) for p in el.iter(W + "p")]
    return blocks


def by_id(items):
    return sorted(items, key=lambda kv: int(kv[0]) if kv[0].lstrip("-").isdigit() else 0)


def render(path, ctx, blocks, notes):
    s, comments = ctx["stats"], ctx["comments"]
    L = [f"=== DOCX EXTRACTION: {path}", "",
         "This is a structural extraction, not a flattened export. Tracked",
         "changes, comments, field codes and hyperlink targets ARE visible",
         "below and must be checked, not disclaimed.", "",
         "--- INVENTORY ---",
         f"tracked insertions: {s['insertions']}",
         f"tracked deletions: {s['deletions']}",
         f"tracked moves: {s['moves']}",
         f"formatting revisions: {s['format_changes']}",
         f"comments: {len(comments)}",
         f"reference-manager / other field codes: {s['fields']}",
         f"hyperlinks with resolved targets: {s['hyperlinks']}",
         f"broken cross-references / missing link targets: {s['broken_refs']}",
         f"tables: {s['tables']}",
         f"images: {s['images']}",
         f"equations: {s['equations']}",
         f"footnotes: {len(notes['footnotes'])}",
         f"endnotes: {len(notes['endnotes'])}"]
    unresolved = sum("MISSING RELATIONSHIP" in b for b in blocks)
    if unresolved:
        L.append(f"WARNING: {unresolved} paragraph(s) link to a missing relationship")
    L += ["", "--- BODY ---", ""]
    blank = False
    for b in blocks:
        if b:
            L += [b, ""]
        elif not blank:
            L.append("")
        blank = not b
    if comments:
        L += ["--- COMMENTS (full text) ---", ""]
        for cid, c in by_id(comments.items()):
            stamp = f" on {c['date']}" if c["date"] else ""
            L.append(f"[{cid}] {c['author']}{stamp}: {c['text']}")
        L.append("")
    for kind, found in notes.items():
        if found:
            L += [f"--- {kind.upper()} ---", ""]
            L += [f"[{nid}] {txt}" for nid, txt in by_id(found.items())] + [""]
    return "\n".join(L).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docx", help="path to a .docx or .dotx file")
    ap.add_argument("-o", "--out", help="write here instead of stdout")
    args = ap.parse_args()

    try:
        z = zipfile.ZipFile(args.docx)
    except (zipfile.BadZipFile, FileNotFoundError, IsADirectoryError) as e:
        sys.exit(f"error: cannot open {args.docx} as a .docx archive: {e}")

    with z:
        if "word/document.xml" not in z.namelist():
            sys.exit(f"error: {args.docx} has no word/document.xml -- "
                     "is it really a Word file? (.doc and .pages are different formats)")
        ctx = {"rels": load_rels(z), "comments": load_comments(z), "stats": Counter()}
        blocks = extract_body(z, ctx)
        notes = {kind: load_notes(z, f"word/{kind}.xml")
                 for kind in ("footnotes", "endnotes")}
        text = render(args.docx, ctx, blocks, notes)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {args.out} ({len(text)} chars)")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
