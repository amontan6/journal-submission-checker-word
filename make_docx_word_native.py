"""Build paper-tracked.docx: a manuscript with Word-NATIVE planted problems.

paper.docx tests problems that survive a plain-text export. This one tests the
six that do NOT (W1-W6 in the README): tracked changes, unresolved comments, a
hyperlink whose target is not its display text, a broken cross-reference, and a
live Zotero field for a reference missing from the list.

Writes the OOXML by hand because python-docx cannot author tracked changes or
comments. Standard library only.

Usage:
    python3 -I make_docx_word_native.py [-o paper-tracked.docx]
"""
import argparse
import zipfile
from xml.sax.saxutils import escape

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
MNS = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006"
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
WML = "application/vnd.openxmlformats-officedocument.wordprocessingml"
AUTHOR = "R. Reviewer"
DATE = "2026-10-10T09:00:00Z"
REV = f'w:author="{AUTHOR}" w:date="{DATE}"'
PUBLIC_REPO = "github.com/montano-lab/scfv-binding-oracle"


def esc(s):
    return escape(s, {'"': "&quot;"})


def run(text, bold=False):
    props = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return f'<w:r>{props}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def para(*inner, style=None):
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{ppr}{''.join(inner)}</w:p>"


def heading(text, level):
    return para(run(text), style="Title" if level == 0 else f"Heading{level}")


def ins(text, rid):
    return f'<w:ins w:id="{rid}" {REV}>{run(text)}</w:ins>'


def dele(text, rid):
    """Deleted text lives in w:delText, not w:t."""
    return (f'<w:del w:id="{rid}" {REV}><w:r><w:delText xml:space="preserve">'
            f"{esc(text)}</w:delText></w:r></w:del>")


def commented(text, cid):
    return (f'<w:commentRangeStart w:id="{cid}"/>{run(text)}'
            f'<w:commentRangeEnd w:id="{cid}"/>'
            f'<w:r><w:commentReference w:id="{cid}"/></w:r>')


def hyperlink(text, rid):
    return f'<w:hyperlink r:id="{rid}">{run(text)}</w:hyperlink>'


def broken_ref():
    """A cross-reference whose bookmark is gone."""
    return (f'<w:fldSimple w:instr=" REF _Ref88412007 \\h ">'
            f'{run("Error! Reference source not found.")}</w:fldSimple>')


def zotero_field():
    instr = (' ADDIN ZOTERO_ITEM CSL_CITATION {"citationID":"a1b2c3",'
             '"properties":{"formattedCitation":"(Koenig et al., 2017)"},'
             '"citationItems":[{"id":4417,"uris":["http://zotero.org/users/local/items/4417"]}]} ')
    fld = lambda kind: f'<w:r><w:fldChar w:fldCharType="{kind}"/></w:r>'
    return (f'{fld("begin")}<w:r><w:instrText xml:space="preserve">{esc(instr)}'
            f'</w:instrText></w:r>{fld("separate")}'
            f'{run("(Koenig et al., 2017)")}{fld("end")}')


def table(rows, total=9360):
    """w:tblGrid is required by the spec -- without it Word offers to repair."""
    width = total // max(len(r) for r in rows)
    grid = f'<w:gridCol w:w="{width}"/>' * max(len(r) for r in rows)
    border = lambda side: f'<w:{side} w:val="single" w:sz="4" w:color="auto"/>'
    tblpr = (f'<w:tblPr><w:tblW w:w="{total}" w:type="dxa"/><w:tblBorders>'
             f'{border("top")}{border("bottom")}</w:tblBorders></w:tblPr>')
    trs = "".join(
        "<w:tr>" + "".join(
            f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/></w:tcPr>'
            f"<w:p>{run(c, bold=(i == 0))}</w:p></w:tc>" for c in row) + "</w:tr>"
        for i, row in enumerate(rows))
    return f"<w:tbl>{tblpr}<w:tblGrid>{grid}</w:tblGrid>{trs}</w:tbl>"


REFS = [
    "Dauparas, J., Anishchenko, I., Bennett, N., et al. (2022). Robust deep "
    "learning based protein sequence design using ProteinMPNN. bioRxiv.",
    "Watson, J. L., Juergens, D., Bennett, N. R., et al. (2022). Broadly "
    "applicable and accurate protein design by integrating structure "
    "prediction networks and diffusion generative models. bioRxiv.",
    "Olsen, T. H., Moal, I. H., & Deane, C. M. (2022). AbLang: an antibody "
    "language model for completing antibody sequences. bioRxiv.",
    "Shuai, R. W., Ruffolo, J. A., & Gray, J. J. (2021). Generative language "
    "modeling for antibody design. bioRxiv.",
    "Makowski, E. K., Wu, L., Desai, A. A., & Tessier, P. M. (2022). "
    "Optimization of therapeutic antibodies for reduced self-association and "
    "non-specific binding. Protein Engineering, Design and Selection.",
    "Harvey, E. P., Shin, J.-E., Skiba, M. A., et al. (2022). An in silico "
    "method to assess antibody fragment polyreactivity. Nature "
    "Communications, 13.",
]


def document_xml():
    body = [
        heading("A sequence-based oracle for scFv binding and developability", 0),
        para(run("A. Montano Romero, [co-authors]")),
        heading("Abstract", 1),
        para(run("We present an oracle that predicts binding and developability "
                 "properties of single-chain variable fragments (scFvs) from sequence "
                 "alone. Trained on a 30-member library characterised by a NanoBiT "
                 "split-luciferase assay, our work achieves "),
             # W1: replacing a word in Word yields a del/ins PAIR, not a bare insert.
             dele("useful ", 202), ins("state-of-the-art ", 102),
             run("ranking performance on held-out clonal lineages. We release all "
                 "code and data.")),
        heading("Introduction", 1),
        para(run("Deep generative methods have transformed protein design over the "
                 "past five years (Dauparas et al., 2022; Watson et al., 2022). "),
             dele("Nobody has attempted this for scFvs. ", 201),  # W2
             run("Antibody-specific language models have followed (Olsen et al., "
                 "2022; Shuai et al., 2021). Property prediction, however, remains "
                 "the bottleneck in most campaigns (Makowski et al., 2022).")),
        para(run("Earlier work established that developability properties can be "
                 "co-optimised with affinity (Harvey et al., 2022), though the "
                 "trade-offs are "),
             commented("library-specific", 1), run(".")),  # W3
        heading("Methods", 1),
        heading("Library design and expression", 2),
        para(run("Constructs were expressed in Expi293 cells. Full construct maps "
                 "are deposited under GenBank accession "),
             commented("MZ457891", 2), run(".")),  # W3
        heading("Binding assay", 2),
        para(run("Binding was measured with a NanoBiT split-luciferase reporter. "
                 "Raw plate data are available in the repository described in "),
             broken_ref(), run(".")),  # W5
        heading("Oracle training", 2),
        para(run("Descriptors were computed per sequence and a random forest "
                 "trained with lineage-disjoint cross-validation. Code is available "
                 "at "),
             hyperlink(PUBLIC_REPO, "rIdPub"), run(".")),
        heading("Results", 1),
        para(run("Our work recovers known binders at a rate well above the "
                 "lineage-only baseline, "),
             "<m:oMath><m:r><m:t>AUC = 0.78 ± 0.04</m:t></m:r></m:oMath>",
             run(". The full comparison appears in Table 1.")),
        table([["Model", "AUC", "Spearman"],
               ["Lineage-only baseline", "0.61", "0.29"],
               ["Descriptor random forest", "0.78", "0.52"]]),
        para(run("Table 1. Held-out ranking performance."), style="Caption"),
        heading("Data availability", 1),
        para(run("All code, trained models and processed assay data are available "
                 "at "),
             hyperlink(PUBLIC_REPO, "rIdPriv"),  # W4
             run(". Analysis notebooks depend on the pipeline tooling described in "),
             zotero_field(), run(".")),  # W6
        heading("References", 1),
        *(para(run(r)) for r in REFS),
    ]
    sect = ('<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
            '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>'
            "</w:sectPr>")
    return (f"{XML}<w:document {W} {R} {MNS}><w:body>{''.join(body)}{sect}</w:body>"
            f"</w:document>")


def comments_xml():
    items = [
        (1, "Is this still true for the IgG4 lineage? Please check before we "
            "submit."),
        (2, "@A. Montano Romero -- is this accession public yet? It was on hold "
            "last I checked."),
    ]
    out = "".join(f'<w:comment w:id="{cid}" w:author="{AUTHOR}" w:initials="RR" '
                  f'w:date="{DATE}">{para(run(text))}</w:comment>'
                  for cid, text in items)
    return f"{XML}<w:comments {W}>{out}</w:comments>"


def styles_xml():
    defs = [("Title", "Title", 0), ("Heading1", "heading 1", 1),
            ("Heading2", "heading 2", 2), ("Caption", "caption", None)]
    out = "".join(
        f'<w:style w:type="paragraph" w:styleId="{sid}">'
        f'<w:name w:val="{name}"/><w:basedOn w:val="Normal"/><w:pPr>'
        + (f'<w:outlineLvl w:val="{lvl}"/>' if lvl is not None else "")
        + "</w:pPr><w:rPr><w:b/></w:rPr></w:style>"
        for sid, name, lvl in defs)
    return (f'{XML}<w:styles {W}><w:style w:type="paragraph" w:default="1" '
            f'w:styleId="Normal"><w:name w:val="Normal"/></w:style>{out}</w:styles>')


def rels_xml(*rels):
    """rels: (id, type, target, external)."""
    out = "".join(f'<Relationship Id="{rid}" Type="{REL}/{typ}" Target="{esc(target)}"'
                  + (' TargetMode="External"' if ext else "") + "/>"
                  for rid, typ, target, ext in rels)
    return f'{XML}<Relationships xmlns="{PKG}/relationships">{out}</Relationships>'


def content_types():
    part = lambda name, typ: (f'<Override PartName="/word/{name}.xml" '
                              f'ContentType="{WML}.{typ}+xml"/>')
    return (f'{XML}<Types xmlns="{PKG}/content-types">'
            f'<Default Extension="rels" ContentType="application/vnd.'
            f'openxmlformats-package.relationships+xml"/>'
            f'<Default Extension="xml" ContentType="application/xml"/>'
            f'{part("document", "document.main")}{part("styles", "styles")}'
            f'{part("comments", "comments")}</Types>')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--out", default="paper-tracked.docx")
    args = ap.parse_args()

    parts = {
        "[Content_Types].xml": content_types(),
        "_rels/.rels": rels_xml(("rId1", "officeDocument", "word/document.xml", False)),
        "word/document.xml": document_xml(),
        "word/_rels/document.xml.rels": rels_xml(
            ("rIdPub", "hyperlink", f"https://{PUBLIC_REPO}", True),
            # W4: both links DISPLAY the public repo; this one targets a private fork.
            ("rIdPriv", "hyperlink",
             "https://github.com/amontano-private/scfv-oracle-WORKING-COPY", True),
            ("rId10", "styles", "styles.xml", False),
            ("rId11", "comments", "comments.xml", False)),
        "word/styles.xml": styles_xml(),
        "word/comments.xml": comments_xml(),
    }
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
