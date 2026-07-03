"""
utils/text.py — v8 Arabic text utilities.

New in v8:
  • normalize_ar_strict()   — deep normalization (hamza, tatweel, etc.)
  • detect_egyptian_dialect() — confidence score 0–1
  • expand_egyptian()        — map Egyptian terms → formal Arabic
  • stem_arabic_light()       — prefix/suffix stripping (no heavy deps)
  • context_window_fit()      — smart truncation to fit token budget
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import List

from core.config import CONFIG

# =========================================================
# NOISE PATTERNS
# =========================================================

_NOISE = [
    re.compile(r'\(?\bscore\s*:\s*[\d.]+\)?', re.IGNORECASE),
    re.compile(r'[\[\(]\s*(?:page|p\.?|صفحة)\s*\d+\s*[\]\)]', re.IGNORECASE),
    re.compile(r'\bp\.?\s*\d{1,3}\b', re.IGNORECASE),
    re.compile(r'-{1,2}\[.*?\]-{1,2}>'),
    re.compile(r'[{}\[\]]'),
    re.compile(r'\n{3,}'),
]

_INJECTION = [re.compile(p, re.IGNORECASE) for p in CONFIG.injection_patterns]

# =========================================================
# EGYPTIAN DIALECT VOCABULARY
# =========================================================

_EGYPTIAN_MARKERS = frozenset([
    'ايه', 'ليه', 'ازاي', 'فين', 'عندي', 'عندنا', 'عاوز', 'عايز',
    'فيه', 'فيها', 'بيحصل', 'محتاج', 'حصل', 'بتاع', 'كده', 'لسه',
    'عامل', 'بتظهر', 'بيصفر', 'هيعمل', 'مش', 'ايوه', 'لا', 'ده',
    'دي', 'دول', 'هنا', 'هناك', 'بقى', 'بقا', 'خالص', 'اوي',
    'قوي', 'شوية', 'معاه', 'معاها', 'بتاعي', 'بتاعك', 'ناحيه',
    'مسمش', 'مشمش', 'اللي', 'اللى', 'اوه', 'عشان', 'علشان',
    'جاي', 'جاية', 'زي', 'زيه', 'زيها', 'كمان', 'برضو', 'برضه',
])

# Egyptian → Formal Arabic
_EGYPTIAN_TO_FORMAL = {
    'ايه': 'ما هو',
    'ليه': 'لماذا',
    'ازاي': 'كيف',
    'فين': 'أين',
    'عاوز': 'أريد',
    'عايز': 'أريد',
    'مش': 'ليس',
    'كده': 'هكذا',
    'بقى': 'إذن',
    'خالص': 'تماماً',
    'اوي': 'جداً',
    'علشان': 'لأن',
    'عشان': 'لأن',
    'كمان': 'أيضاً',
    'برضو': 'أيضاً',
    'برضه': 'أيضاً',
    'دلوقتي': 'الآن',
    'زي': 'مثل',
    'بره': 'خارج',
    'جوه': 'داخل',
}

# =========================================================
# ARABIC NORMALIZATION
# =========================================================

def normalize_ar(text: str) -> str:
    """Fast canonical Arabic normalization for indexing/matching."""
    text = text.lower()
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'ى', 'ي', text)
    text = re.sub(r'ة', 'ه', text)
    text = re.sub(r'[ًٌٍَُِّْـ]', '', text)   # strip tashkeel + tatweel
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def normalize_ar_strict(text: str) -> str:
    """
    Deep normalization including:
    - All hamza forms → ا
    - shadda removal
    - alef maqsura → ya
    - teh marbuta → ha
    - lam-alef ligatures
    - non-Arabic chars stripped (except spaces and digits)
    """
    text = text.strip()
    # Remove tashkeel (harakat + shadda + sukun)
    text = re.sub(r'[\u0600-\u061F\u064B-\u065F\u0670]', '', text)
    # Normalize alef variants → bare alef
    text = re.sub(r'[أإآٱ]', 'ا', text)
    # Normalize lam-alef ligatures
    text = re.sub(r'[ﻻﻼﻷﻸﻹﻺﻵﻶ]', 'لا', text)
    # Alef maqsura → ya
    text = re.sub(r'ى', 'ي', text)
    # Teh marbuta → ha
    text = re.sub(r'ة', 'ه', text)
    # Remove waw al-jama'a suffix (common)
    # Lowercase + collapse spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def stem_arabic_light(word: str) -> str:
    """
    Lightweight Arabic light stemmer.
    Strips common prefixes (al-, wa-, fa-, bi-, li-)
    and common suffixes (-oun, -een, -at, -ah, -an).
    No external library needed.
    """
    # Remove definite article
    for prefix in ('ال', 'وال', 'بال', 'لل', 'فال'):
        if word.startswith(prefix) and len(word) > len(prefix) + 2:
            word = word[len(prefix):]
            break
    # Remove single-char prefixes
    if len(word) > 4 and word[0] in 'وفب':
        word = word[1:]
    # Remove common suffixes
    for suffix in ('ون', 'ين', 'ات', 'ان', 'ية', 'ها', 'كم', 'هم', 'تم'):
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            word = word[:-len(suffix)]
            break
    return word


# =========================================================
# DIALECT DETECTION
# =========================================================

def detect_language(text: str) -> str:
    """Returns 'english' | 'arabic_egyptian' | 'arabic_formal'."""
    latin = len(re.findall(r'[a-zA-Z]', text))
    total = len(text.replace(' ', '')) or 1
    if latin / total > 0.5:
        return 'english'
    norm = normalize_ar(text)
    tokens = set(norm.split())
    hits = len(tokens & _EGYPTIAN_MARKERS)
    if hits >= 1 or any(m in norm for m in _EGYPTIAN_MARKERS):
        return 'arabic_egyptian'
    return 'arabic_formal'


def detect_egyptian_score(text: str) -> float:
    """Returns 0–1 confidence that text is Egyptian dialect."""
    norm = normalize_ar(text)
    tokens = norm.split()
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in _EGYPTIAN_MARKERS)
    return min(hits / max(len(tokens) * 0.15, 1), 1.0)


def normalize_egyptian_to_formal(text: str) -> str:
    """Replace Egyptian colloquial terms with formal Arabic equivalents."""
    norm = normalize_ar(text)
    for egyptian, formal in _EGYPTIAN_TO_FORMAL.items():
        norm = re.sub(rf'\b{re.escape(egyptian)}\b', formal, norm)
    return norm


# =========================================================
# TEXT CLEANING
# =========================================================

def clean_text(text: str) -> str:
    for pat in _NOISE:
        text = pat.sub(' ', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()


def compress_context(
    text: str,
    max_lines: int = CONFIG.max_context_lines,
    max_chars: int = CONFIG.max_context_chars,
) -> str:
    """
    Deduplicate lines, enforce line-length minimum, cap total chars.
    Preserves most informative lines (longer = more informative heuristic).
    """
    lines, seen = [], set()
    for line in text.splitlines():
        line = line.strip()
        if len(line) < CONFIG.min_line_length:
            continue
        sig = hashlib.md5(normalize_ar(line).encode()).hexdigest()
        if sig in seen:
            continue
        seen.add(sig)
        lines.append(line)

    # Sort by length descending — longer lines carry more info
    lines.sort(key=len, reverse=True)
    lines = lines[:max_lines]

    result = '\n'.join(lines)
    return result[:max_chars]


def context_window_fit(text: str, max_chars: int = 2400) -> str:
    """Truncate context to fit within LLM context window budget."""
    if len(text) <= max_chars:
        return text
    # Keep beginning and end — both have high information density in RAG chunks
    half = max_chars // 2 - 20
    return text[:half] + '\n…[مختصر]…\n' + text[-half:]


def sanitize_chunk(text: str) -> str:
    """Remove prompt-injection attempts from retrieved chunks."""
    import logging
    logger = logging.getLogger('agri_ai.utils')
    for pat in _INJECTION:
        if pat.search(text):
            logger.warning('Prompt injection detected — chunk sanitized.')
            return ''
    return text


# =========================================================
# MATH UTILITIES
# =========================================================

def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(min(x, 30), -30)))


def norm_dense(score: float) -> float:
    """FAISS cosine ∈ [-1,1] → [0,1]."""
    return float(max(0.0, min(1.0, (score + 1.0) / 2.0)))


def norm_sparse(score: float) -> float:
    """BM25 ≥ 0 → [0,1] via log-normalisation."""
    if score <= 0:
        return 0.0
    return float(min(math.log1p(score) / math.log1p(CONFIG.bm25_norm + 1), 1.0))


def text_hash(text: str, prefix_len: int = 400) -> str:
    return hashlib.md5(normalize_ar(text[:prefix_len]).encode()).hexdigest()


def chunk_list(lst: list, size: int) -> List[list]:
    return [lst[i:i + size] for i in range(0, len(lst), size)]
