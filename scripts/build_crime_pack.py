"""Build the criminal-law demo pack (data/demo_crime/) from public Indian Act text.

Source: the IndiaLaw.db SQLite file in the public GitHub repository
civictech-India/Indian-Law-Penal-Code-Json (section-by-section text of Indian Acts
taken from India Code). Clone it first:

    git clone --depth 1 https://github.com/civictech-India/Indian-Law-Penal-Code-Json
    python scripts/build_crime_pack.py Indian-Law-Penal-Code-Json/IndiaLaw.db

Each selected chapter is written in the statute format the SAC parser reads
(src/ingestion/structure.py): a title line, "CHAPTER <roman> — <name>",
"Section <n>. <title>." and the section text. The wording of every section is the
source text, unchanged apart from whitespace and the
source website's amendment footnotes, which are removed.

The source text has lost the official (1)/(a) labels inside sections, so sections
are not split by their sub-sections. A section longer than MAX_WORDS is split at
paragraph (or, failing that, sentence) boundaries into parts written as
"Clause (a): …", "Clause (b): …". These letters number the parts in order; they
are not the Act's own clause labels. Keeping every chunk short matters: the
embedding model reads about 256 tokens and the NLI model at most 512.
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "demo_crime"
MAX_WORDS = 180

# (file name, header lines, table, [(chapter numeral, chapter name, [section ids])])
PACK = [
    (
        "indian_penal_code_1860_crimes.txt",
        ["THE INDIAN PENAL CODE (ACT NO. 45 OF 1860)", "Jurisdiction: India", "Enacted: 6 October 1860"],
        "IPC",
        [
            ("IV", "GENERAL EXCEPTIONS", ("76", "106")),
            ("XVI", "OF OFFENCES AFFECTING THE HUMAN BODY", ("299", "311")),
            ("XVI", "OF OFFENCES AFFECTING THE HUMAN BODY: OF HURT", ("319", "338")),
            ("XVI", "OF OFFENCES AFFECTING THE HUMAN BODY: OF WRONGFUL RESTRAINT AND WRONGFUL CONFINEMENT", ("339", "348")),
            ("XVI", "OF OFFENCES AFFECTING THE HUMAN BODY: OF CRIMINAL FORCE AND ASSAULT", ("349", "358")),
            ("XVI", "OF OFFENCES AFFECTING THE HUMAN BODY: OF KIDNAPPING, ABDUCTION, SLAVERY AND FORCED LABOUR", ("359", "374")),
            ("XVII", "OF OFFENCES AGAINST PROPERTY", ("378", "462")),
            ("XX", "OF OFFENCES RELATING TO MARRIAGE (WITH CHAPTER XX-A, OF CRUELTY BY HUSBAND OR RELATIVES OF HUSBAND)", ("493", "498A")),
            ("XXI", "OF DEFAMATION", ("499", "502")),
            ("XXII", "OF CRIMINAL INTIMIDATION, INSULT AND ANNOYANCE", ("503", "510")),
            ("XXIII", "OF ATTEMPTS TO COMMIT OFFENCES", ("511", "511")),
        ],
    ),
    (
        "code_of_criminal_procedure_1973_arrest_fir_bail.txt",
        ["THE CODE OF CRIMINAL PROCEDURE, 1973 (ACT NO. 2 OF 1974)", "Jurisdiction: India", "Enacted: 25 January 1974"],
        "CRPC",
        [
            ("V", "ARREST OF PERSONS", ("41", "60A")),
            ("XII", "INFORMATION TO THE POLICE AND THEIR POWERS TO INVESTIGATE", ("154", "176")),
            ("XXXIII", "PROVISIONS AS TO BAIL AND BONDS", ("436", "450")),
        ],
    ),
    (
        "negotiable_instruments_act_1881_cheque_bounce.txt",
        ["THE NEGOTIABLE INSTRUMENTS ACT, 1881 (ACT NO. 26 OF 1881)", "Jurisdiction: India", "Enacted: 9 December 1881"],
        "NIA",
        [
            ("XVII", "OF PENALTIES IN CASE OF DISHONOUR OF CERTAIN CHEQUES FOR INSUFFICIENCY OF FUNDS IN THE ACCOUNTS", ("138", "148")),
        ],
    ),
]

COLUMNS = {
    "IPC": ("Section", "section_title", "section_desc"),
    "CRPC": ("section", "section_title", "section_desc"),
    "NIA": ("section", "section_title", "section_desc"),
}


# The source carries the website's amendment footnotes: a digit glued to a word
# ("thirty1 days") and a note line ("1 Criminal Law (Amendment) Act, 2018"). They
# are not part of the Act's text, so both are removed.
_FOOTNOTE_MARK = re.compile(r"\b([A-Za-z]{3,})\d{1,2}\b")
_FOOTNOTE_LINE = re.compile(r"^\d{1,2}\s+(?:.*\b(?:Amendment|Ordinance)\b.*|Changed from .*|This .*)$")


def section_key(number: str) -> tuple[int, str]:
    m = re.fullmatch(r"(\d+)([A-Z]*)", number)
    return (int(m.group(1)), m.group(2)) if m else (10**9, number)


def paragraphs(text: str) -> list[str]:
    """Non-empty lines with whitespace collapsed; a lone label line such as
    "(1)" is joined to the line after it."""
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.replace("\r", "").split("\n")]
    lines = [_FOOTNOTE_MARK.sub(r"\1", ln) for ln in lines if ln and not _FOOTNOTE_LINE.match(ln)]
    out: list[str] = []
    for ln in lines:
        if out and re.fullmatch(r"\([0-9a-z]+\)", out[-1]):
            out[-1] = f"{out[-1]} {ln}"
        else:
            out.append(ln)
    return out


def split_long(paragraph: str) -> list[str]:
    """A paragraph over MAX_WORDS, cut at sentence ends (or ';' / ':')."""
    if len(paragraph.split()) <= MAX_WORDS:
        return [paragraph]
    pieces = re.split(r"(?<=[.;:])\s+", paragraph)
    out, cur = [], ""
    for piece in pieces:
        candidate = f"{cur} {piece}".strip()
        if cur and len(candidate.split()) > MAX_WORDS:
            out.append(cur)
            cur = piece
        else:
            cur = candidate
    if cur:
        out.append(cur)
    return out


def parts(text: str) -> list[str]:
    """Group a section's paragraphs into parts of at most MAX_WORDS words."""
    out, cur = [], ""
    for para in paragraphs(text):
        for piece in split_long(para):
            candidate = f"{cur} {piece}".strip()
            if cur and len(candidate.split()) > MAX_WORDS:
                out.append(cur)
                cur = piece
            else:
                cur = candidate
    if cur:
        out.append(cur)
    return out


def section_lines(number: str, title: str, text: str) -> list[str]:
    title = re.sub(r"\s+", " ", title).strip().rstrip(".")
    lines = [f"Section {number}. {title}."]
    chunks = parts(text)
    if not chunks:
        return []
    # The first part is the section body. If it starts with a label such as "(1)",
    # the parser reads it as that sub-section, which is what the label says.
    lines.append(chunks[0])
    for i, chunk in enumerate(chunks[1:]):
        lines.append(f"Clause ({chr(ord('a') + i)}): {chunk}")
    return lines


def build(db_path: Path) -> None:
    con = sqlite3.connect(db_path)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for file_name, header, table, chapters in PACK:
        num_col, title_col, text_col = COLUMNS[table]
        rows = {
            str(r[0]): (r[1], r[2])
            for r in con.execute(f'SELECT "{num_col}", "{title_col}", "{text_col}" FROM {table}')
        }
        out = header + [""]
        written = 0
        for numeral, name, (first, last) in chapters:
            lo, hi = section_key(first), section_key(last)
            numbers = sorted((n for n in rows if lo <= section_key(n) <= hi), key=section_key)
            out += [f"CHAPTER {numeral} — {name}", ""]
            for n in numbers:
                title, text = rows[n]
                lines = section_lines(n, title or "", text or "")
                if lines:
                    out += lines + [""]
                    written += 1
        (OUT_DIR / file_name).write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
        print(f"{file_name}: {written} sections")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/build_crime_pack.py path/to/IndiaLaw.db")
    build(Path(sys.argv[1]))
