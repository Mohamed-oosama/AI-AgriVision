"""
scripts/index_builder.py — Build FAISS + BM25 + Parent-Child Index.

Usage:
  python scripts/index_builder.py --docs data/docs.jsonl --output .
  python scripts/index_builder.py --docs data/ --output . --parent-size 1024 --child-size 256
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import pickle
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import faiss
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import CONFIG
from utils.models import Models
from utils.text import clean_text, normalize_ar

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('index_builder')


def load_docs(path: str) -> List[Dict[str, Any]]:
    docs = []
    p = Path(path)
    if p.is_dir():
        files = list(p.glob('**/*.jsonl')) + list(p.glob('**/*.json'))
    else:
        files = [p]

    for f in files:
        with open(f, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, list):
                        docs.extend(obj)
                    else:
                        docs.append(obj)
                except json.JSONDecodeError:
                    continue
    logger.info('Loaded %d documents from %s', len(docs), path)
    return docs


def chunk_doc(
    doc: Dict[str, Any],
    child_size: int = CONFIG.child_chunk_size,
    parent_size: int = CONFIG.parent_chunk_size,
    overlap: int = 50,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Split document into parent and child chunks.
    Parent chunks: larger context (1024 tokens)
    Child chunks:  smaller indexed units (256 tokens)
    """
    text     = clean_text(doc.get('text', doc.get('content', '')))
    source   = doc.get('source', doc.get('title', ''))
    metadata = doc.get('metadata', {})

    if not text:
        return [], []

    words = text.split()

    # Parent chunks
    parent_chunks = []
    pid = 0
    for i in range(0, len(words), parent_size - overlap):
        chunk_text = ' '.join(words[i:i + parent_size])
        if len(chunk_text.strip()) < 50:
            continue
        parent_chunks.append({
            'text':      chunk_text,
            'source':    source,
            'metadata':  metadata,
            'parent_id': f'{source}_{pid}',
            'child_ids': [],
        })
        pid += 1

    # Child chunks with parent references
    child_chunks = []
    cid = 0
    for i, parent in enumerate(parent_chunks):
        p_words = parent['text'].split()
        for j in range(0, len(p_words), child_size - overlap):
            child_text = ' '.join(p_words[j:j + child_size])
            if len(child_text.strip()) < 30:
                continue
            c_id = f'{source}_{i}_{cid}'
            child_chunks.append({
                'text':      child_text,
                'source':    source,
                'metadata':  metadata,
                'chunk_id':  c_id,
                'parent_id': parent['parent_id'],
            })
            parent['child_ids'].append(c_id)
            cid += 1

    return child_chunks, parent_chunks


def build_index(
    docs_path: str,
    output_dir: str = '.',
    child_size: int = CONFIG.child_chunk_size,
    parent_size: int = CONFIG.parent_chunk_size,
) -> None:
    os.makedirs(output_dir, exist_ok=True)

    raw_docs     = load_docs(docs_path)
    child_chunks: List[Dict] = []
    parent_chunks: List[Dict] = []

    for doc in raw_docs:
        ch, par = chunk_doc(doc, child_size=child_size, parent_size=parent_size)
        child_chunks.extend(ch)
        parent_chunks.extend(par)

    logger.info('Child chunks: %d | Parent chunks: %d',
                len(child_chunks), len(parent_chunks))

    if not child_chunks:
        logger.error('No chunks generated. Check input format.')
        return

    # Build embeddings in batches
    logger.info('Encoding child chunks with %s…', CONFIG.embed_model)
    texts     = [c['text'] for c in child_chunks]
    batch_sz  = CONFIG.embed_batch_size
    all_embs  = []
    for i in range(0, len(texts), batch_sz):
        batch = texts[i:i + batch_sz]
        embs  = Models.embed_docs(batch)
        all_embs.append(embs)
        if (i // batch_sz) % 10 == 0:
            logger.info('  Encoded %d/%d…', min(i + batch_sz, len(texts)), len(texts))

    embeddings = np.vstack(all_embs).astype(np.float32)
    dim        = embeddings.shape[1]

    # FAISS index: Inner Product (works with normalized embeddings = cosine)
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    logger.info('FAISS index built: %d vectors, dim=%d', index.ntotal, dim)

    # Save
    faiss.write_index(index, os.path.join(output_dir, CONFIG.index_file))

    with open(os.path.join(output_dir, CONFIG.chunks_file), 'wb') as f:
        pickle.dump(child_chunks, f)

    with open(os.path.join(output_dir, CONFIG.parent_chunks_file), 'wb') as f:
        pickle.dump(parent_chunks, f)

    logger.info('✅ Index saved to %s', output_dir)
    logger.info('   %s  (%d child chunks)', CONFIG.index_file, len(child_chunks))
    logger.info('   %s (%d parent chunks)', CONFIG.parent_chunks_file, len(parent_chunks))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--docs',        required=True)
    parser.add_argument('--output',      default='.')
    parser.add_argument('--child-size',  type=int, default=CONFIG.child_chunk_size)
    parser.add_argument('--parent-size', type=int, default=CONFIG.parent_chunk_size)
    args = parser.parse_args()
    build_index(args.docs, args.output, args.child_size, args.parent_size)
