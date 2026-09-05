"""
DishIQ Phase 5.2 — Ingredient Intelligence
Core parser pipeline.

The parser is fully deterministic — no LLMs or ML models.
Pipeline stages:
  1. clean_text
  2. detect_to_taste
  3. detect_optional
  4. resolve_fractions
  5. extract_quantity
  6. extract_unit
  7. extract_preparation_note
  8. normalize_ingredient  (now returns alias + source)
  9. get_category
  10. compute_confidence_score

New in 5.2:
  • ParsedIngredient gains display_name, matched_alias,
    normalization_source, parser_version, category
  • PARSER_VERSION and confidence constants centralised in constants.py
  • normalize_ingredient() returns a NormResult namedtuple
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional, NamedTuple, Tuple, Dict, List

from app.ingredient_intelligence.constants import (
    CONFIDENCE_KNOWN_BASE,
    CONFIDENCE_QUANTITY_BONUS,
    CONFIDENCE_TO_TASTE,
    CONFIDENCE_UNIT_BONUS,
    CONFIDENCE_UNKNOWN_BASE,
    NORMALIZATION_SOURCE_DICTIONARY,
    NORMALIZATION_SOURCE_UNKNOWN,
    PARSER_VERSION,
)
from app.ingredient_intelligence.normalization import (
    INGREDIENT_NORMALIZATION,
    KNOWN_INGREDIENTS,
    OPTIONAL_MARKERS,
    PREPARATION_NOTES,
    TO_TASTE_MARKERS,
    UNIT_NORMALIZATION,
)
from app.ingredient_intelligence.categories import get_category


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class NormResult(NamedTuple):
    canonical_name: str
    matched_alias: Optional[str]
    normalization_source: str


@dataclass
class ParsedIngredient:
    raw_text: str
    display_name: str               # cleaned name before normalisation, title-cased
    canonical_name: str
    category: Optional[str]         # from categories.py; None for unknown
    quantity: Optional[float]
    unit: Optional[str]
    preparation_note: Optional[str]
    optional: bool
    to_taste: bool
    confidence_score: float
    matched_alias: Optional[str]    # alias that triggered normalisation
    normalization_source: str       # "dictionary" | "unknown"
    parser_version: str             # from constants.PARSER_VERSION


# ---------------------------------------------------------------------------
# Internal regex helpers
# ---------------------------------------------------------------------------

# Unicode fraction → decimal
_UNICODE_FRACTIONS: Dict[str, float] = {
    "½": 0.5,
    "⅓": 1 / 3,
    "⅔": 2 / 3,
    "¼": 0.25,
    "¾": 0.75,
    "⅛": 0.125,
    "⅜": 0.375,
    "⅝": 0.625,
    "⅞": 0.875,
    "⅙": 1 / 6,
    "⅚": 5 / 6,
    "⅕": 0.2,
    "⅖": 0.4,
    "⅗": 0.6,
    "⅘": 0.8,
}

_UNICODE_FRAC_RE = re.compile(
    r"(?P<whole>\d+)?\s*(?P<ufrac>[½⅓⅔¼¾⅛⅜⅝⅞⅙⅚⅕⅖⅗⅘])"
)
_TEXT_FRAC_RE = re.compile(r"(?P<num>\d+)\s*/\s*(?P<den>\d+)")
_NUMBER_RE = re.compile(r"(?<!\w)(\d+(?:\.\d+)?)")
_PAREN_RE = re.compile(r"\(([^)]*)\)")


# ---------------------------------------------------------------------------
# Non-numeric quantity prefix pattern definitions
# ---------------------------------------------------------------------------
_NON_NUMERIC_PREFIXES = [
    re.compile(r"^(?:a\s+)?pinch\s+of\s+", re.IGNORECASE),
    re.compile(r"^(?:a\s+)?dash\s+of\s+", re.IGNORECASE),
    re.compile(r"^(?:a\s+)?handful\s+of\s+", re.IGNORECASE),
    re.compile(r"^(?:a\s+)?touch\s+of\s+", re.IGNORECASE),
    re.compile(r"^(?:a\s+)?bit\s+of\s+", re.IGNORECASE),
    re.compile(r"^(?:a\s+)?drop\s+of\s+", re.IGNORECASE),
    re.compile(r"^(?:a\s+)?sprig\s+of\s+", re.IGNORECASE),
    re.compile(r"^sprigs?\s+of\s+", re.IGNORECASE),
    re.compile(r"^(?:a\s+)?few\s+", re.IGNORECASE),
    re.compile(r"^(?:a\s+)?piece\s+of\s+", re.IGNORECASE),
    re.compile(r"^(?:a\s+)?slice\s+of\s+", re.IGNORECASE),
    re.compile(r"^(?:a\s+)?head\s+of\s+", re.IGNORECASE),
    re.compile(r"^(?:a\s+)?clove\s+of\s+", re.IGNORECASE),
    re.compile(r"^a\s+pinch\b", re.IGNORECASE),
]


def clean_non_numeric_prefixes(text: str) -> str:
    cleaned = text.strip()
    for pattern in _NON_NUMERIC_PREFIXES:
        if pattern.search(cleaned):
            cleaned = pattern.sub("", cleaned).strip()
            break
    return cleaned


# ---------------------------------------------------------------------------
# Stage 1 – Text cleaning
# ---------------------------------------------------------------------------

def clean_text(raw: str) -> str:
    """Normalise whitespace and unicode; return a clean string."""
    text = raw.strip()
    # Use NFC to preserve vulgar fractions (½, ¼, ¾) as single characters
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"\s+", " ", text)
    return text


# ---------------------------------------------------------------------------
# Stage 2 – To-taste detection
# ---------------------------------------------------------------------------

def detect_to_taste(text: str) -> Tuple[bool, str]:
    """
    Detect "to taste" phrases and strip them from the ingredient text.
    Returns (is_to_taste, cleaned_text).
    """
    is_to_taste = False
    cleaned = text
    for marker in sorted(TO_TASTE_MARKERS, key=len, reverse=True):
        pattern = re.compile(r"\b" + re.escape(marker) + r"\b", re.IGNORECASE)
        if pattern.search(cleaned):
            is_to_taste = True
            cleaned = pattern.sub("", cleaned).strip()
    return is_to_taste, cleaned


# ---------------------------------------------------------------------------
# Stage 3 – Optional detection
# ---------------------------------------------------------------------------

def detect_optional(text: str) -> Tuple[bool, str]:
    """Return (is_optional, cleaned_text)."""
    is_optional = False
    cleaned = text

    parens = _PAREN_RE.findall(text)
    for content in parens:
        if any(m in content.lower() for m in OPTIONAL_MARKERS):
            is_optional = True
            cleaned = _PAREN_RE.sub("", cleaned, count=1).strip()

    if not is_optional:
        lc = cleaned.lower()
        for m in OPTIONAL_MARKERS:
            if m in lc:
                is_optional = True
                cleaned = re.sub(re.escape(m), "", cleaned, flags=re.IGNORECASE).strip()
                break

    return is_optional, cleaned


# ---------------------------------------------------------------------------
# Stage 4 – Fraction resolution
# ---------------------------------------------------------------------------

def resolve_fractions(text: str) -> Tuple[Optional[float], str]:
    """Parse the first fraction expression near the start of the string."""
    m = _UNICODE_FRAC_RE.search(text)
    if m and m.start() < 15:
        whole = int(m.group("whole")) if m.group("whole") else 0
        frac = _UNICODE_FRACTIONS.get(m.group("ufrac"), 0.0)
        value = whole + frac
        remainder = (text[: m.start()] + text[m.end() :]).strip()
        return value, remainder

    m = _TEXT_FRAC_RE.search(text)
    if m and m.start() < 15:
        num, den = int(m.group("num")), int(m.group("den"))
        value = num / den if den != 0 else 0.0
        remainder = (text[: m.start()] + text[m.end() :]).strip()
        return value, remainder

    return None, text


# ---------------------------------------------------------------------------
# Stage 5 – Quantity extraction
# ---------------------------------------------------------------------------

def extract_quantity(text: str) -> Tuple[Optional[float], str]:
    """Extract the leading numeric quantity; return (value, remainder)."""
    frac_val, remainder = resolve_fractions(text)
    if frac_val is not None:
        return frac_val, remainder

    m = _NUMBER_RE.search(text)
    if m and m.start() < 10:
        value = float(m.group(1))
        remainder = (text[: m.start()] + text[m.end() :]).strip()
        return value, remainder

    return None, text


# ---------------------------------------------------------------------------
# Stage 6 – Unit extraction and normalisation
# ---------------------------------------------------------------------------

def extract_unit(text: str) -> Tuple[Optional[str], str]:
    """Match a unit token at the start of the remaining text."""
    sorted_units = sorted(UNIT_NORMALIZATION.keys(), key=len, reverse=True)
    pattern = r"^(?P<unit>" + "|".join(re.escape(u) for u in sorted_units) + r")\b\.?"
    m = re.match(pattern, text.strip(), re.IGNORECASE)
    if m:
        raw_unit = m.group("unit").lower().rstrip(".")
        canonical = UNIT_NORMALIZATION.get(raw_unit, raw_unit)
        remainder = text[m.end() :].strip().lstrip(",").strip()
        return canonical, remainder
    return None, text


# ---------------------------------------------------------------------------
# Stage 7 – Preparation note extraction
# ---------------------------------------------------------------------------

def extract_preparation_note(text: str) -> Tuple[Optional[str], str]:
    """Detect and extract a preparation descriptor."""
    sorted_notes = sorted(PREPARATION_NOTES, key=len, reverse=True)
    for note in sorted_notes:
        pattern = re.compile(re.escape(note), re.IGNORECASE)
        m = pattern.search(text)
        if m:
            note_str = m.group().lower()
            remainder = (text[: m.start()] + text[m.end() :]).strip().strip(",").strip()
            return note_str, remainder
    return None, text


# ---------------------------------------------------------------------------
# Stage 8 – Ingredient name normalisation  (Phase 5.2 returns NormResult)
# ---------------------------------------------------------------------------

def normalize_ingredient(name: str) -> NormResult:
    """
    Map a raw ingredient name to its canonical form.
    Returns a NormResult with canonical_name, matched_alias, and source.
    """
    key = name.strip().lower()

    # Direct lookup
    if key in INGREDIENT_NORMALIZATION:
        return NormResult(
            canonical_name=INGREDIENT_NORMALIZATION[key],
            matched_alias=key,
            normalization_source=NORMALIZATION_SOURCE_DICTIONARY,
        )

    # Plurality strip ('s')
    if key.endswith("s") and key[:-1] in INGREDIENT_NORMALIZATION:
        return NormResult(
            canonical_name=INGREDIENT_NORMALIZATION[key[:-1]],
            matched_alias=key[:-1],
            normalization_source=NORMALIZATION_SOURCE_DICTIONARY,
        )

    # Partial / substring match (longest alias first for precision)
    for alias, canonical in sorted(
        INGREDIENT_NORMALIZATION.items(), key=lambda x: len(x[0]), reverse=True
    ):
        if key.startswith(alias) or alias in key:
            return NormResult(
                canonical_name=canonical,
                matched_alias=alias,
                normalization_source=NORMALIZATION_SOURCE_DICTIONARY,
            )

    # No match → return raw name as canonical
    return NormResult(
        canonical_name=key,
        matched_alias=None,
        normalization_source=NORMALIZATION_SOURCE_UNKNOWN,
    )


# ---------------------------------------------------------------------------
# Stage 9 – Confidence scoring
# ---------------------------------------------------------------------------

def compute_confidence(
    canonical: str,
    quantity: Optional[float],
    unit: Optional[str],
    to_taste: bool,
) -> float:
    """Return a heuristic confidence score in [0.0, 1.0]."""
    if to_taste:
        return CONFIDENCE_TO_TASTE

    score = CONFIDENCE_KNOWN_BASE if canonical in KNOWN_INGREDIENTS else CONFIDENCE_UNKNOWN_BASE

    if quantity is not None:
        score += CONFIDENCE_QUANTITY_BONUS
    if unit is not None:
        score += CONFIDENCE_UNIT_BONUS

    return min(round(score, 2), 1.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_ingredient(raw_text: str) -> ParsedIngredient:
    """Parse a single raw ingredient string into a structured ParsedIngredient."""

    # Stage 1 – Clean
    text = clean_text(raw_text)

    # Stage 2 – To-taste detection (now strips "to taste" phrase from text)
    to_taste, text = detect_to_taste(text)

    # Stage 3 – Optional detection
    is_optional, text = detect_optional(text)

    # Stage 4+5 – Quantity
    quantity, text = extract_quantity(text)

    # Stage 6 – Unit
    unit, text = extract_unit(text)

    # Stage 7 – Preparation note
    prep_note, text = extract_preparation_note(text)

    # Strip non-numeric quantity lead phrases (e.g. "a pinch of") if no quantity extracted
    if quantity is None:
        text = clean_non_numeric_prefixes(text)

    # Remaining text is the ingredient name
    raw_name = text.strip().strip(",").strip()

    # Capture the cleaned display name before normalisation
    # Title-case preserves human readability (e.g. "Large Onions")
    display_name = raw_name.title() if raw_name else clean_text(raw_text).title()

    # Stage 8 – Normalise ingredient name (returns NormResult)
    norm = normalize_ingredient(raw_name)

    # Stage 9 – Category
    category = get_category(norm.canonical_name)

    # Stage 10 – Confidence
    confidence = compute_confidence(norm.canonical_name, quantity, unit, to_taste)

    return ParsedIngredient(
        raw_text=raw_text.strip(),
        display_name=display_name,
        canonical_name=norm.canonical_name,
        category=category,
        quantity=quantity,
        unit=unit,
        preparation_note=prep_note,
        optional=is_optional,
        to_taste=to_taste,
        confidence_score=confidence,
        matched_alias=norm.matched_alias,
        normalization_source=norm.normalization_source,
        parser_version=PARSER_VERSION,
    )


def parse_ingredients(raw_texts: List[str]) -> List[ParsedIngredient]:
    """Parse a list of raw ingredient strings."""
    return [parse_ingredient(t) for t in raw_texts]


