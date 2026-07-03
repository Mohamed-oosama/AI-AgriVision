# 🌾 AgriAI v8 — المساعد الزراعي المصري

نظام RAG متعدد الوكلاء مبني على LangGraph لدعم الزراعة المصرية.

## متطلبات الأجهزة
| المكوّن | المطلوب |
|---------|---------|
| GPU | RTX 4050 (6GB) أو أحدث |
| RAM | 16 GB (32 GB أفضل) |
| Ollama | آخر إصدار |
| Python | 3.10+ |

## التثبيت السريع
```bash
pip install -r requirements.txt

# تثبيت النماذج
ollama pull qwen3:8b
ollama pull qwen3:4b

# بناء الفهرس
python main.py --index data/docs.jsonl

# تشغيل المحادثة
python main.py --chat

# API Server
python main.py --api
```

## هيكل المشروع
```
agri_ai_v8/
├── core/          config + state
├── utils/         text + ollama + models + cache
├── ontology/      45+ محصول، أمراض، آفات، تسميد
├── memory/        ذاكرة قصيرة + تلخيص + طويلة
├── retrieval/     BM25+FAISS+RRF+HyDE+Self-RAG+Parent-Doc
├── graph/         Multi-hop BFS + chains + contradictions
├── confidence/    5 مكوّنات + LLM judge
├── agents/        17 node LangGraph workflow
├── evaluation/    Recall/MRR/Faithfulness/Hallucination
├── api/           FastAPI + streaming SSE
└── scripts/       index_builder
```

## أوامر CLI
```bash
python main.py --chat                    # محادثة تفاعلية
python main.py --query "الطماطم بتصفر"  # سؤال واحد
python main.py --bench data/test.jsonl   # تقييم شامل
python main.py --health                  # فحص النظام
python main.py --api --port 8000         # API Server
```

## متغيرات البيئة
```env
OLLAMA_URL=http://localhost:11434
MODEL_MAIN=qwen3:8b
MODEL_FAST=qwen3:4b
MODEL_DEEP=qwen3.5:9b
EMBED_MODEL=BAAI/bge-m3
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
USE_REDIS=false
```
