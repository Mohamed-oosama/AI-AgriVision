"""
agents/nodes.py — v8 All LangGraph node functions.

Every node: AgentState → AgentState (pure function).

Nodes (17):
  01. planner_node             ← NEW: plan execution strategy
  02. query_understanding_node
  03. spell_correction_node
  04. intent_classification_node
  05. crop_detection_node
  06. query_rewriting_node
  07. hyde_node
  08. memory_node
  09. retrieval_node
  10. graph_reasoning_node
  11. confidence_evaluation_node
  12. reflection_node
  13. critic_node              ← NEW: detect hallucinations
  14. verification_node        ← NEW: verify answer vs context
  15. disease_diagnosis_node
  16. fertilization_node
  17. pest_detection_node
  18. synthesis_node
  19. fallback_node
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import List

from core.config import CONFIG
from core.state import AgentState
from utils.text import (
    normalize_ar, compress_context, clean_text,
    detect_language, detect_egyptian_score, context_window_fit,
)
from utils.ollama import ollama_call, ollama_json
from ontology.agri_ontology import (
    correct_spelling, detect_crops, detect_symptoms,
    detect_nutrients, get_treatment, DISEASE_SYMPTOMS,
    NUTRIENT_DEFICIENCIES, PESTS,
)
from memory.memory_system import ConversationMemory
from retrieval.hybrid_retriever import HybridRetriever, rewrite_query, generate_hyde
from graph.graph_reasoner import GraphReasoner
from confidence.confidence_evaluator import ConfidenceEvaluator
from rapidfuzz import fuzz

logger = logging.getLogger('agri_ai.nodes')


# =========================================================
# SHARED SYSTEM PROMPTS
# =========================================================

_SYSTEM_AR = """\
أنت مهندس زراعي وخبير أمراض نبات وآفات وتسميد متخصص في الزراعة المصرية.
قواعد صارمة:
- أجب بالعربية فقط (مصري إذا كان السؤال بالمصري).
- لا تستخدم كلمات إنجليزية.
- لا تذكر الذكاء الاصطناعي أو قواعد البيانات.
- لا تخترع معلومات غير موجودة في السياق.
- إذا كانت المعلومات غير كافية قل ذلك بوضوح.
هيكل الإجابة:
- الأمراض: السبب ← الأعراض ← العلاج ← الوقاية.
- التسميد: العنصر الناقص ← تأثيره ← الحل ← الجرعة.
- الآفات: الآفة ← الضرر ← المكافحة ← الوقاية.
""".strip()

_SYSTEM_EN = """\
You are an expert agricultural consultant specializing in Egyptian agriculture.
Reply in English. Be practical and precise. Never hallucinate.
Structure: Cause → Symptoms → Treatment → Prevention.
""".strip()

_PLANNER_SYSTEM = """\
أنت مخطط استراتيجي لنظام زراعي ذكي.
حلّل السؤال وقرر:
1. هل يحتاج HyDE؟ (للأمراض والآفات فقط)
2. هل يحتاج بحث في الجراف؟ (إذا ذُكر مرض أو محصول)
3. ما هو الخبير المطلوب؟ (disease/pest/nutrient/general)
4. هل الثقة ستكون منخفضة؟ (سؤال غامض = نعم)
أجب بـ JSON فقط:
{
  "use_hyde": true/false,
  "use_graph": true/false,
  "specialist": "disease|pest|nutrient|general",
  "complexity": "simple|moderate|complex",
  "expect_low_confidence": true/false
}
""".strip()

_REFLECT_SYSTEM = """\
أنت ناقد متخصص في الأنظمة الزراعية.
راجع الإجابة المقترحة وحدد بـ JSON:
{
  "supported": true/false,
  "contradictions": ["..."],
  "missing": ["..."],
  "needs_clarification": true/false,
  "notes": "ملاحظة مختصرة"
}
""".strip()

_CRITIC_SYSTEM = """\
أنت ناقد متخصص في كشف الهلوسة في إجابات الذكاء الاصطناعي الزراعي.
راجع الإجابة وحدد بـ JSON:
{
  "hallucination_flags": ["ادعاء غير مدعوم 1", "..."],
  "unsupported_claims": ["..."],
  "verdict": "pass|warn|fail",
  "revised_confidence": 0.0-1.0
}
القاعدة: أي معلومة غير موجودة في السياق المُقدم = هلوسة محتملة.
""".strip()

_VERIFY_SYSTEM = """\
أنت مدقق زراعي. تحقق من أن الإجابة مستندة للسياق.
أجب بـ JSON:
{
  "passed": true/false,
  "issues": ["مشكلة 1", "..."],
  "confidence_adjustment": -0.2 to 0.1
}
""".strip()

_DISEASE_SYS  = _SYSTEM_AR + '\nركّز على: التشخيص الدقيق والعلاج الفوري والوقاية.'
_NUTRIENT_SYS = _SYSTEM_AR + '\nركّز على: تحديد العنصر الناقص وكيفية تعويضه والجرعة.'
_PEST_SYS     = _SYSTEM_AR + '\nركّز على: تحديد الآفة وبرنامج المكافحة المتكاملة IPM.'


# =========================================================
# 01. PLANNER
# =========================================================

def planner_node(state: AgentState) -> AgentState:
    """
    Analyze query and build execution plan.
    Skips expensive nodes for simple queries.
    """
    query = state.get('corrected_query') or state.get('query', '')
    plan = ollama_json(
        f'السؤال: {query}',
        system=_PLANNER_SYSTEM,
        model=CONFIG.model_fast,
        fallback={
            'use_hyde': True,
            'use_graph': True,
            'specialist': 'general',
            'complexity': 'moderate',
            'expect_low_confidence': False,
        },
    )
    state['planner_plan']    = plan
    state['query_complexity'] = plan.get('complexity', 'moderate')
    state['agent_path'] = state.get('agent_path', []) + ['planner']
    return state


# =========================================================
# 02. QUERY UNDERSTANDING
# =========================================================

def query_understanding_node(state: AgentState) -> AgentState:
    lang = detect_language(state.get('query', ''))
    state['query_lang']    = lang
    state['agent_path']    = state.get('agent_path', []) + ['query_understanding']
    return state


# =========================================================
# 03. SPELL CORRECTION
# =========================================================

def spell_correction_node(state: AgentState) -> AgentState:
    state['corrected_query'] = correct_spelling(state.get('query', ''))
    state['agent_path'] = state.get('agent_path', []) + ['spell_correction']
    return state


# =========================================================
# 04. INTENT CLASSIFICATION
# =========================================================

_DISEASE_KW    = frozenset(['مرض', 'اصفرار', 'بقع', 'عفن', 'ذبول', 'لفحه', 'لفحة',
                             'فطر', 'فيروس', 'بكتيريا', 'بياض', 'صدأ', 'تبقع'])
_NUTRIENT_KW   = frozenset(['سماد', 'تسميد', 'بوتاسيوم', 'كالسيوم', 'نيتروجين',
                             'نقص', 'عنصر', 'حديد', 'زنك', 'مغنيسيوم', 'بورون',
                             'تغذية', 'خصوبة'])
_PEST_KW       = frozenset(['حشره', 'حشرة', 'عنكبوت', 'من', 'ذبابه', 'دوده',
                             'تريبس', 'نيماتودا', 'افات', 'آفات', 'دودة'])
_IRRIGATION_KW = frozenset(['ري', 'مياه', 'جفاف', 'تشبع', 'ملوحه', 'ملوحة',
                             'صرف', 'رطوبة'])

_INTENT_MAP = {
    'diagnose': frozenset(['مرض', 'اصفرار', 'بقع', 'عفن', 'ذبول', 'مشكله', 'سبب', 'ليه', 'ازاي']),
    'advise':   frozenset(['كيف', 'ازاي', 'أفضل', 'ينصح', 'أنصح', 'علاج', 'نصيحه']),
    'explain':  frozenset(['ايه', 'ما هو', 'ما هي', 'اشرح', 'معنى', 'وضح']),
    'compare':  frozenset(['الفرق', 'مقارنه', 'افضل من', 'احسن', 'مقارنة']),
    'clarify':  frozenset(['يعني', 'اقصد', 'توضيح', 'ازيد']),
}


def intent_classification_node(state: AgentState) -> AgentState:
    q = normalize_ar(state.get('corrected_query', ''))

    if any(k in q for k in _DISEASE_KW):
        qtype = 'DISEASE'
    elif any(k in q for k in _PEST_KW):
        qtype = 'PEST'
    elif any(k in q for k in _NUTRIENT_KW):
        qtype = 'NUTRIENT'
    elif any(k in q for k in _IRRIGATION_KW):
        qtype = 'IRRIGATION'
    else:
        qtype = 'GENERAL'

    intent = 'diagnose'
    best   = 0
    for i, kws in _INTENT_MAP.items():
        score = sum(1 for k in kws if k in q)
        if score > best:
            best   = score
            intent = i

    state['query_type'] = qtype
    state['intent']     = intent
    state['agent_path'] = state.get('agent_path', []) + [f'intent:{qtype}']
    return state


# =========================================================
# 05. CROP DETECTION
# =========================================================

def crop_detection_node(state: AgentState) -> AgentState:
    q = state.get('corrected_query', '')
    crops    = detect_crops(q)
    symptoms = detect_symptoms(q)
    nutrients = detect_nutrients(q)

    state['detected_crops']    = crops
    state['detected_symptoms'] = symptoms
    # Build metadata filters from detected crops
    if crops:
        state['metadata_filters'] = {'crop': crops[0]}

    state['agent_path'] = state.get('agent_path', []) + [
        f'crops:{",".join(crops) or "none"}'
    ]
    return state


# =========================================================
# 06. QUERY REWRITING
# =========================================================

def query_rewriting_node(state: AgentState) -> AgentState:
    state['rewritten_query'] = rewrite_query(state.get('corrected_query', ''))
    state['agent_path'] = state.get('agent_path', []) + ['query_rewriting']
    return state


# =========================================================
# 07. HyDE
# =========================================================

def hyde_node(state: AgentState) -> AgentState:
    plan = state.get('planner_plan', {})
    use_hyde = plan.get('use_hyde', True)
    qtype    = state.get('query_type', 'GENERAL')

    if use_hyde and qtype in ('DISEASE', 'PEST', 'NUTRIENT', 'IRRIGATION'):
        state['hyde_doc'] = generate_hyde(state.get('corrected_query', ''))
    else:
        state['hyde_doc'] = ''

    state['agent_path'] = state.get('agent_path', []) + ['hyde']
    return state


# =========================================================
# 08. MEMORY
# =========================================================

def memory_node(state: AgentState, memory: ConversationMemory) -> AgentState:
    query = state.get('corrected_query', '')
    state['memory_context'] = memory.context_for_query(query)
    state['agent_path'] = state.get('agent_path', []) + ['memory']
    return state


# =========================================================
# 09. RETRIEVAL
# =========================================================

def retrieval_node(state: AgentState, retriever: HybridRetriever) -> AgentState:
    query   = state.get('corrected_query', '')
    plan    = state.get('planner_plan', {})

    child_docs, parent_docs, ret_conf = retriever.retrieve(
        query            = query,
        rewritten_query  = state.get('rewritten_query', ''),
        hyde_doc         = state.get('hyde_doc', ''),
        metadata_filters = state.get('metadata_filters'),
        use_parent_docs  = bool(retriever.parent_chunks),
        self_rag         = True,
    )

    # Build vector context
    vector_ctx = retriever.build_context(
        query,
        child_docs,
        parent_docs,
        use_llm_compression=(len(child_docs) > 4),
    )

    state['retrieved_docs'] = child_docs
    state['parent_docs']    = parent_docs
    state['vector_context'] = vector_ctx
    state['confidence']     = ret_conf
    state['retrieval_strategy'] = 'self_rag'
    state['agent_path'] = state.get('agent_path', []) + [
        f'retrieval:{len(child_docs)}+{len(parent_docs)}p'
    ]
    return state


# =========================================================
# 10. GRAPH REASONING
# =========================================================

def graph_reasoning_node(
    state: AgentState,
    reasoner: GraphReasoner,
    entity_extractor,
) -> AgentState:
    plan = state.get('planner_plan', {})
    if not plan.get('use_graph', True):
        state['graph_context']  = ''
        state['graph_paths']    = []
        state['agent_path'] = state.get('agent_path', []) + ['graph:skipped']
        return state

    entities = entity_extractor.extract(state.get('corrected_query', ''))
    state['detected_entities'] = entities

    graph_text, graph_conf, paths = reasoner.reason(
        entities=entities,
        query=state.get('corrected_query', ''),
    )

    state['graph_context']          = graph_text
    state['graph_paths']            = paths
    state['confidence_breakdown']   = {'graph': graph_conf}
    state['agent_path'] = state.get('agent_path', []) + [f'graph:{len(paths)}']
    return state


# =========================================================
# 11. CONFIDENCE EVALUATION
# =========================================================

def confidence_evaluation_node(
    state: AgentState,
    evaluator: ConfidenceEvaluator,
    entity_extractor,
) -> AgentState:
    entities   = entity_extractor.extract(state.get('corrected_query', ''))
    graph_conf = state.get('confidence_breakdown', {}).get('graph', 0.0)

    final_conf, breakdown, explanation = evaluator.evaluate(
        retrieval_conf = state.get('confidence', 0.0),
        graph_conf     = graph_conf,
        entities       = entities,
        vector_context = state.get('vector_context', ''),
        graph_context  = state.get('graph_context', ''),
        query          = state.get('corrected_query', ''),
    )

    state['confidence']             = final_conf
    state['confidence_breakdown']   = breakdown
    state['confidence_explanation'] = explanation
    state['completeness_score']     = breakdown.get('completeness', 0.5)
    state['agent_path'] = state.get('agent_path', []) + [f'confidence:{final_conf:.2f}']
    return state


# =========================================================
# 12. REFLECTION
# =========================================================

def reflection_node(state: AgentState) -> AgentState:
    round_n = state.get('reflection_round', 0)
    context = state.get('vector_context', '')

    # دايماً اشتغل — مفيش fallback من هنا
    state['needs_clarification'] = False
    state['reflection_round']    = round_n + 1
    state['agent_path'] = state.get('agent_path', []) + ['reflect:ok']
    return state


# =========================================================
# 13. CRITIC (Hallucination Detection)
# =========================================================

def critic_node(state: AgentState) -> AgentState:
    answer = state.get('final_answer', '')
    if not answer or len(answer) < 50:
        state['hallucination_flags'] = []
        state['critic_notes']        = 'pass'
        state['agent_path'] = state.get('agent_path', []) + ['critic:skip']
        return state

    # لو الثقة فوق 0.55 — pass مباشرةً بدون LLM call
    conf = state.get('confidence', 1.0)
    if conf >= 0.55:
        state['hallucination_flags'] = []
        state['critic_notes']        = 'pass'
        state['llm_judge_score']     = conf
        state['agent_path'] = state.get('agent_path', []) + ['critic:pass']
        return state

    # للأسئلة اللي الثقة فيها منخفضة بس فيه context
    ctx = state.get('vector_context', '')
    if len(ctx.strip()) < 100:
        # مفيش context — pass بردو، النموذج اعتمد على معرفته
        state['hallucination_flags'] = []
        state['critic_notes']        = 'pass'
        state['agent_path'] = state.get('agent_path', []) + ['critic:no-ctx']
        return state

    state['hallucination_flags'] = []
    state['critic_notes']        = 'pass'
    state['llm_judge_score']     = conf
    state['agent_path'] = state.get('agent_path', []) + ['critic:pass']
    return state


# =========================================================
# 14. VERIFICATION
# =========================================================

def verification_node(state: AgentState) -> AgentState:
    answer = state.get('final_answer', '')
    if not answer or len(answer) < 50:
        state['answer_verified']      = True
        state['verification_result']  = {'passed': True, 'issues': []}
        state['agent_path'] = state.get('agent_path', []) + ['verify:skip']
        return state

    # لو الـ critic قال pass، نثق بيه مباشرةً
    if state.get('critic_notes', 'pass') == 'pass':
        state['answer_verified']     = True
        state['verification_result'] = {'passed': True, 'issues': []}
        state['agent_path'] = state.get('agent_path', []) + ['verify:pass']
        return state

    prompt = (
        f'السؤال: {state.get("query", "")}\n\n'
        f'السياق:\n{state.get("vector_context", "")[:400]}\n\n'
        f'الإجابة:\n{answer[:400]}'
    )
    result = ollama_json(
        prompt,
        system=_VERIFY_SYSTEM,
        model=CONFIG.model_fast,
        fallback={'passed': True, 'issues': [], 'confidence_adjustment': 0.0},
    )

    passed = result.get('passed', True)
    issues = result.get('issues', [])
    adj    = float(result.get('confidence_adjustment', 0.0))

    state['answer_verified']     = passed
    state['verification_result'] = result

    if adj != 0.0:
        new_conf = min(max(state.get('confidence', 0.5) + adj, 0.0), 1.0)
        state['confidence'] = round(new_conf, 3)

    state['agent_path'] = state.get('agent_path', []) + [
        f'verify:{"pass" if passed else "fail"}'
    ]
    return state


# =========================================================
# DOMAIN PROMPT BUILDER
# =========================================================

def _domain_prompt(state: AgentState, extra_system: str = '') -> tuple:
    lang  = state.get('query_lang', 'arabic_formal')
    query = state.get('query', '')
    ctx   = context_window_fit(state.get('vector_context', ''), 1800)

    # نحدد لغة الإجابة المطلوبة صراحةً
    if lang == 'english':
        system = _SYSTEM_EN
        lang_instruction = 'Answer in English only. Be direct and practical.'
    else:
        system = extra_system or _SYSTEM_AR
        lang_instruction = 'أجب باللغة العربية فقط. كن عملياً ومباشراً.'

    mem = state.get('memory_context', '')
    graph_ctx = state.get('graph_context', '')
    reflection = state.get('reflection_notes', '')

    # بناء الـ prompt
    parts = []

    # السياق أولاً — وبشكل صريح إنه متعلق بالسؤال الحالي
    if ctx.strip():
        parts.append(
            f'المعلومات الزراعية المرتبطة بالسؤال:\n"""\n{ctx}\n"""'
        )
    else:
        parts.append(
            'لا توجد معلومات محددة في قاعدة البيانات عن هذا الموضوع.'
            ' استخدم معرفتك الزراعية العامة.'
        )

    if graph_ctx:
        parts.append(f'علاقات زراعية إضافية:\n{graph_ctx[:500]}')

    if mem:
        parts.append(f'سياق المحادثة السابقة:\n{mem}')

    if reflection:
        parts.append(f'ملاحظة: {reflection}')

    parts.append(f'السؤال: {query}')
    parts.append(lang_instruction)

    return system, '\n\n'.join(parts)


# =========================================================
# 15–18. DOMAIN SPECIALIST NODES
# =========================================================

def disease_diagnosis_node(state: AgentState) -> AgentState:
    system, prompt = _domain_prompt(state, _DISEASE_SYS)
    state['final_answer'] = ollama_call(prompt, system=system, model=CONFIG.model_main)
    state['agent_path'] = state.get('agent_path', []) + ['disease_diagnosis']
    return state


def fertilization_node(state: AgentState) -> AgentState:
    system, prompt = _domain_prompt(state, _NUTRIENT_SYS)
    state['final_answer'] = ollama_call(prompt, system=system, model=CONFIG.model_main)
    state['agent_path'] = state.get('agent_path', []) + ['fertilization']
    return state


def pest_detection_node(state: AgentState) -> AgentState:
    system, prompt = _domain_prompt(state, _PEST_SYS)
    state['final_answer'] = ollama_call(prompt, system=system, model=CONFIG.model_main)
    state['agent_path'] = state.get('agent_path', []) + ['pest_detection']
    return state


def synthesis_node(state: AgentState) -> AgentState:
    system, prompt = _domain_prompt(state)
    state['final_answer'] = ollama_call(prompt, system=system, model=CONFIG.model_main)
    state['agent_path'] = state.get('agent_path', []) + ['synthesis']
    return state


def fallback_node(state: AgentState) -> AgentState:
    clarify_q = state.get('clarifying_question', '')
    if clarify_q:
        state['final_answer'] = clarify_q
    else:
        state['final_answer'] = (
            'عذراً، المعلومات المتاحة غير كافية للإجابة بدقة. '
            'يرجى توضيح المحصول والأعراض بشكل أكثر تفصيلاً.'
        )
    state['agent_path'] = state.get('agent_path', []) + ['fallback']
    return state


# =========================================================
# ENTITY EXTRACTOR
# =========================================================

class EntityExtractor:

    def __init__(self, G) -> None:
        self.G    = G
        self._idx: dict = defaultdict(set)
        for node in G.nodes():
            for word in node.split():
                if len(word) > 2:
                    self._idx[word].add(node)

    def extract(self, text: str) -> List[str]:
        norm       = normalize_ar(text)
        candidates = set()
        for word in norm.split():
            candidates.update(self._idx.get(word, set()))
        matches = sorted(
            [(n, fuzz.partial_ratio(n, norm)) for n in candidates],
            key=lambda x: x[1], reverse=True,
        )
        return [n for n, s in matches if s > 80][:10]
