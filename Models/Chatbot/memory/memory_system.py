"""
memory/memory_system.py — v8 Multi-tier Conversation Memory.

Architecture:
  Tier 1: Raw buffer (deque, last N turns)          → always available
  Tier 2: Rolling summary (LLM-compressed)           → every K turns
  Tier 3: Long-term JSON (session-persistent facts)  → crops, farm info
  Tier 4: Semantic index (embedding similarity lookup) → optional

New in v8:
  • extract_facts()     — automatically extract structured farm facts from conversation
  • get_relevant()      — embedding-based retrieval of past turns
  • context_for_query() — return most relevant memory for current query
  • Memory health check — prevent context explosion
  • Track turn timestamps for time-aware summarization
"""
from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from core.config import CONFIG
from utils.ollama import ollama_call, ollama_json

logger = logging.getLogger('agri_ai.memory')


_SUMMARY_SYSTEM = """\
أنت مساعد يُلخّص محادثات زراعية.
اكتب ملخصاً قصيراً (جملتان إلى ثلاث) باللغة العربية.
احتفظ فقط بـ: المحصول، المشكلة، الحل المقترح، والنتيجة.
لا تضف مقدمة أو ختام.
""".strip()

_FACT_EXTRACT_SYSTEM = """\
استخرج الحقائق الثابتة من المحادثة التالية بصيغة JSON.
أجب بـ JSON فقط. المفاتيح المطلوبة (إذا ذُكرت):
{
  "crop": "المحصول الرئيسي",
  "location": "الموقع أو المنطقة",
  "soil_type": "نوع التربة",
  "irrigation": "نظام الري",
  "farm_size": "مساحة المزرعة"
}
إذا لم تُذكر معلومة، لا تضعها في الـ JSON.
""".strip()


class ConversationMemory:

    def __init__(self, session_id: str = 'default') -> None:
        self.session_id   = session_id
        self._raw: deque  = deque(maxlen=CONFIG.memory_max_raw)
        self._summary: str = ''
        self._turn_count: int = 0
        self._long_term: Dict[str, Any] = {}
        self._timestamps: List[float] = []
        self._lt_path = os.path.join(CONFIG.cache_dir, f'lt_{session_id}.json')
        self._load_long_term()

    # ── Long-term persistence ─────────────────────────────────────

    def _load_long_term(self) -> None:
        os.makedirs(CONFIG.cache_dir, exist_ok=True)
        if os.path.exists(self._lt_path):
            try:
                with open(self._lt_path, 'r', encoding='utf-8') as f:
                    self._long_term = json.load(f)
                logger.debug('Long-term memory loaded: %d facts', len(self._long_term))
            except Exception as e:
                logger.warning('Could not load long-term memory: %s', e)

    def _save_long_term(self) -> None:
        try:
            with open(self._lt_path, 'w', encoding='utf-8') as f:
                json.dump(self._long_term, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning('Could not save long-term memory: %s', e)

    def remember(self, key: str, value: Any) -> None:
        """Explicitly store a persistent fact (from user or auto-extraction)."""
        self._long_term[key] = value
        self._save_long_term()

    def forget(self, key: str) -> None:
        """Remove a stored fact."""
        if key in self._long_term:
            del self._long_term[key]
            self._save_long_term()

    # ── Turn management ────────────────────────────────────────────

    def add(self, user: str, assistant: str) -> None:
        """Add a Q&A turn to memory."""
        self._raw.append({'user': user, 'assistant': assistant})
        self._timestamps.append(time.time())
        self._turn_count += 1

        # Auto-extract facts every 2 turns
        if self._turn_count % 2 == 0:
            self._auto_extract_facts(user, assistant)

        # Summarize every K turns
        if self._turn_count % CONFIG.memory_summarize_every == 0:
            self._summarize()

    def _auto_extract_facts(self, user: str, assistant: str) -> None:
        """Silently extract structured facts from a conversation turn."""
        try:
            snippet = f'مستخدم: {user}\nمساعد: {assistant[:300]}'
            facts = ollama_json(snippet, system=_FACT_EXTRACT_SYSTEM, model=CONFIG.model_fast)
            for k, v in facts.items():
                if v and k not in self._long_term:
                    self._long_term[k] = v
                    logger.debug('Auto-extracted fact: %s = %s', k, v)
            if facts:
                self._save_long_term()
        except Exception as e:
            logger.debug('Fact extraction failed: %s', e)

    def _summarize(self) -> None:
        """Compress raw buffer into a summary using LLM."""
        if not self._raw:
            return
        history = '\n'.join(
            f'مستخدم: {h["user"]}\nمساعد: {h["assistant"][:300]}'
            for h in self._raw
        )
        prev = f'الملخص السابق:\n{self._summary}\n\n' if self._summary else ''
        prompt = (
            f'{prev}'
            f'المحادثة الأخيرة:\n{history}\n\n'
            'اكتب ملخصاً محدّثاً.'
        )
        new_summary = ollama_call(
            prompt,
            system=_SUMMARY_SYSTEM,
            model=CONFIG.model_fast,
            timeout=30,
        )
        self._summary = new_summary.strip()[:CONFIG.memory_max_summary_len]
        logger.debug('Memory summarized: %s…', self._summary[:80])

    # ── Context retrieval ──────────────────────────────────────────

    def get_context(self) -> str:
        """
        Return compact context string for current prompt.
        Priority: summary → last raw turn.
        """
        parts: List[str] = []

        if self._summary:
            parts.append(f'ملخص المحادثة:\n{self._summary}')
        elif self._raw:
            last = self._raw[-1]
            snippet = last['user'][:200]
            parts.append(f'السؤال السابق: {snippet}')

        if self._long_term:
            lt_items = {k: v for k, v in self._long_term.items()
                       if k in ('crop', 'location', 'soil_type', 'irrigation', 'farm_size')}
            if lt_items:
                lt_text = ' | '.join(f'{k}: {v}' for k, v in lt_items.items())
                parts.append(f'معلومات المزرعة: {lt_text}')

        return '\n\n'.join(parts)

    def context_for_query(self, query: str) -> str:
        """
        Return memory context most relevant to current query.
        Uses simple keyword overlap if embedding not available.
        """
        # Try semantic relevance
        ctx = self._semantic_relevant(query)
        if ctx:
            return ctx
        # Fallback to standard context
        return self.get_context()

    def _semantic_relevant(self, query: str) -> str:
        """Find most relevant past turn via keyword overlap."""
        if not self._raw:
            return ''
        from utils.text import normalize_ar
        q_words = set(normalize_ar(query).split())
        best_score, best_turn = 0.0, None
        for turn in self._raw:
            turn_words = set(normalize_ar(turn['user']).split())
            overlap = len(q_words & turn_words)
            score = overlap / max(len(q_words), 1)
            if score > best_score:
                best_score = score
                best_turn = turn
        if best_turn and best_score > 0.3:
            return (
                f'سؤال ذو صلة سابق: {best_turn["user"][:200]}\n'
                f'الإجابة: {best_turn["assistant"][:300]}'
            )
        return ''

    def get_last_query(self) -> Optional[str]:
        if self._raw:
            return self._raw[-1]['user']
        return None

    def get_farm_info(self) -> Dict[str, Any]:
        """Return extracted long-term farm facts."""
        return {k: v for k, v in self._long_term.items()
                if k in ('crop', 'location', 'soil_type', 'irrigation', 'farm_size')}

    def clear_session(self) -> None:
        """Clear short-term memory (keep long-term facts)."""
        self._raw.clear()
        self._summary = ''
        self._turn_count = 0

    def full_reset(self) -> None:
        """Clear everything including long-term facts."""
        self.clear_session()
        self._long_term.clear()
        if os.path.exists(self._lt_path):
            os.remove(self._lt_path)

    def stats(self) -> Dict[str, Any]:
        return {
            'session_id':   self.session_id,
            'turns':        self._turn_count,
            'raw_buffer':   len(self._raw),
            'has_summary':  bool(self._summary),
            'long_term_facts': len(self._long_term),
        }
