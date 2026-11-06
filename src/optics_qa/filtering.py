"""Cheap, deterministic first-pass filtering.

The LLM is expensive and can be wrong; keep obvious non-questions out before
spending a request on them.  The filter is intentionally conservative: when
in doubt, it includes the post and lets the human decide.
"""

from __future__ import annotations

import re
from typing import Iterable

from .models import Classification, RawPost


OPTICS_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\blens(es)?\b",
        r"\boptics?\b",
        r"\boptical\b",
        r"\bphotonics?\b",
        r"\bprism(s)?\b",
        r"\bmirror(s)?\b",
        r"\bwindow(s)?\b",
        r"\bfilter(s)?\b",
        r"\bwaveplate(s)?\b",
        r"\bpolarizer(s)?\b",
        r"\bbeamsplitter(s)?\b",
        r"\bgrating(s)?\b",
        r"\bcoating(s)?\b",
        r"\bar[ -]?coat(ing|ed)?\b",
        r"\bdielectric\b",
        r"\bsubstrate(s)?\b",
        r"\bfused[ -]?silica\b",
        r"\bbk7\b",
        r"\bcaf2\b",
        r"\bsapphire\b",
        r"\bn-?bk7\b",
        r"\bzf\b",
        r"\btolerance(s)?\b",
        r"\bsurface[ -]?figure\b",
        r"\bscratch[ -]?dig\b",
        r"\blambda\s*/\s*\d+",
        r"\bmtf\b",
        r"\bwavefront\b",
        r"\binterferometer\b",
        r"\bzygo\b",
        r"\bmetrology\b",
        r"\bpolish(ing|ed)?\b",
        r"\bfabricat(e|ion|ing)\b",
        r"\bcentering\b",
        r"\bbevel\b",
        r"\bcement(ed|ing)?\b",
        r"\bachromat(s|ic)?\b",
        r"\baspher(e|ic)\b",
        r"\bdiffraction\b",
        r"\baberration(s)?\b",
        r"\bray[ -]?trac(e|ing)\b",
        r"\bzemax\b",
        r"\bcode[ -]?v\b",
        r"\boptical[ -]?design\b",
        r"\bthin[ -]?film\b",
        r"\brefractive[ -]?index\b",
        r"\btransmission\b",
        r"\breflectance\b",
        r"\bnumerical[ -]?aperture\b",
        r"\bf[ -]?number\b",
        r"\bstray[ -]?light\b",
        r"\bghost(ing|s)?\b",
        r"\blaser[ -]?damage\b",
        r"\blidar\b",
        r"\bcollimator\b",
        r"\bwaveguide(s)?\b",
        r"\bmetasurface(s)?\b",
        r"\bretarder(s)?\b",
        r"\bwedge(s)?\b",
        r"\bpentaprism\b",
        r"\bcorner[ -]?cube\b",
        r"\bretroreflector\b",
        r"\bchromatic\b",
        r"\bspherical\b",
        r"\bcoma\b",
        r"\bastigmatism\b",
        r"\bdistortion\b",
        r"\bvignetting\b",
        r"\bthroughput\b",
        r"\bnumerical\b",
    )
)

QUESTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\?",
        r"\bhow\b",
        r"\bwhat\b",
        r"\bwhy\b",
        r"\bwhich\b",
        r"\bcan\b",
        r"\bcould\b",
        r"\bshould\b",
        r"\bhelp\b",
        r"\badvice\b",
        r"\brecommend",
        r"\bsuggest",
        r"\bneed\b",
        r"\blooking for\b",
        r"\banyone\b",
    )
)

SOURCING_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bsupplier(s)?\b",
        r"\bvendor(s)?\b",
        r"\bmanufacturer(s)?\b",
        r"\bquote(s|d)?\b",
        r"\brfq\b",
        r"\bpurchase\b",
        r"\bbuy\b",
        r"\bprocure",
        r"\bsource\b",
        r"\bsourcing\b",
        r"\bcustom\b",
        r"\bmoq\b",
        r"\bprice\b",
        r"\bpricing\b",
        r"\blead[ -]?time\b",
        r"\bproduction\b",
    )
)

SKIP_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bmeme\b",
        r"\bshitpost\b",
        r"\bfor sale\b",
        r"\bselling\b",
        r"\bhiring\b",
        r"\bjob posting\b",
        r"\bsalary\b",
        r"\bcareer\b",
        r"\bonlyfans\b",
        r"\bnsfw\b",
        r"\bcrypto\b",
        r"\bstock market\b",
        r"\bweekly thread\b",
    )
)

COMMERCIAL_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bour (company|factory|team|shop|production line)\b",
        r"\bwe (offer|manufacture|produce|supply|fabricate)\b",
        r"\bcontact (us|me)\b",
        r"\bdm (me|us)\b",
        r"\brequest a quote\b",
        r"\brequest a quotation\b",
        r"\bprice(s|d)?\b",
        r"\bpricing\b",
        r"\bquotation\b",
        r"\blead[ -]?time\b",
        r"\bsales@\b",
        r"\bwww\.",
    )
)


def _matches(patterns: Iterable[re.Pattern[str]], text: str) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            hits.append(match.group(0).lower())
    return hits


def classify_post(post: RawPost) -> Classification:
    if post.removed:
        return Classification(False, "skip", reasons=("removed_or_deleted",))
    if post.over_18:
        return Classification(False, "skip", reasons=("over_18",))
    if post.stickied:
        return Classification(False, "skip", reasons=("stickied",))

    text = f"{post.title}\n{post.body}"
    skip_hits = _matches(SKIP_PATTERNS, text)
    if skip_hits:
        return Classification(False, "skip", reasons=("excluded_term", *skip_hits[:3]))

    optics_hits = _matches(OPTICS_PATTERNS, text)
    question_hits = _matches(QUESTION_PATTERNS, text)
    sourcing_hits = _matches(SOURCING_PATTERNS, text)

    if not optics_hits and not question_hits:
        return Classification(False, "skip", reasons=("no_optics_or_question_signal",))

    if sourcing_hits:
        return Classification(False, "skip", reasons=("sourcing_or_rfq",))

    if question_hits:
        return Classification(
            True,
            "technical_question",
            tuple(dict.fromkeys(optics_hits + question_hits))[:8],
        )

    return Classification(False, "skip", reasons=("discussion_not_question",))


def excerpt(text: str, max_chars: int = 280) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) <= max_chars:
        return compact
    cut = compact[:max_chars]
    last_space = cut.rfind(" ")
    if last_space > max_chars // 2:
        cut = cut[:last_space]
    return cut.rstrip(" ,.;:") + "..."


def commercial_flags(text: str) -> list[str]:
    hits = _matches(COMMERCIAL_PATTERNS, text or "")
    return [f"commercial_language:{hit}" for hit in dict.fromkeys(hits)]


def looks_like_question(post: RawPost) -> bool:
    return "?" in post.title or "?" in post.body
