"""
utils/ollama.py — v8 Ollama HTTP client.

New in v8:
  • ollama_stream()      — token-level streaming generator
  • ollama_json()        — enforces JSON output (structured generation)
  • health_check()       — verify Ollama is up + model is loaded
  • model_info()         — query loaded model VRAM / param info
  • Exponential backoff with jitter on retries
"""
from __future__ import annotations

import json
import logging
import random
import re
import time
from typing import Dict, Generator, Iterator, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config import CONFIG

logger = logging.getLogger('agri_ai.ollama')

# =========================================================
# HTTP SESSION — connection reuse + urllib3 retry
# =========================================================

def _make_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=0,              # we handle retries manually
        backoff_factor=0,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=4, pool_maxsize=8)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


_SESSION = _make_session()


# =========================================================
# CORE CALL
# =========================================================

def ollama_call(
    prompt: str,
    system: str = '',
    model: str = CONFIG.model_main,
    temperature: Optional[float] = None,
    max_retries: int = CONFIG.max_retries,
    timeout: int = CONFIG.ollama_timeout,
) -> str:
    """
    Synchronous Ollama completion.
    Returns text response or error string in Arabic.
    """
    messages: List[Dict[str, str]] = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})

    payload = {
        'model': model,
        'messages': messages,
        'stream': False,
        'options': {
            'temperature':    temperature if temperature is not None else CONFIG.ollama_temperature,
            'top_p':          CONFIG.ollama_top_p,
            'repeat_penalty': CONFIG.ollama_repeat_penalty,
            'num_ctx':        CONFIG.ollama_num_ctx,
        },
    }

    for attempt in range(1, max_retries + 1):
        try:
            t0 = time.perf_counter()
            r = _SESSION.post(
                f'{CONFIG.ollama_url}/api/chat',
                json=payload,
                timeout=timeout,
            )
            r.raise_for_status()
            elapsed = time.perf_counter() - t0
            result = r.json()['message']['content']
            logger.debug('ollama_call model=%s elapsed=%.2fs len=%d',
                         model, elapsed, len(result))
            return result

        except requests.exceptions.Timeout:
            logger.warning('Ollama timeout attempt %d/%d model=%s', attempt, max_retries, model)
        except requests.exceptions.ConnectionError:
            logger.error('Ollama connection error at %s', CONFIG.ollama_url)
            return 'خطأ: تعذّر الاتصال بخادم Ollama. تأكد من تشغيل: ollama serve'
        except requests.exceptions.HTTPError as e:
            logger.error('Ollama HTTP error: %s', e)
        except Exception as e:
            logger.exception('Ollama unexpected error: %s', e)

        if attempt < max_retries:
            # Exponential backoff with jitter
            sleep_time = (1.5 ** attempt) + random.uniform(0, 0.5)
            time.sleep(sleep_time)

    return 'خطأ: فشل الاتصال بالنموذج بعد عدة محاولات.'


# =========================================================
# JSON-ENFORCED CALL
# =========================================================

def ollama_json(
    prompt: str,
    system: str = '',
    model: str = CONFIG.model_fast,
    fallback: Optional[dict] = None,
) -> dict:
    """
    Call Ollama and parse JSON response.
    Strips markdown fences. Falls back to `fallback` dict on parse failure.
    """
    # Append JSON instruction to system
    json_system = (system + '\n\nأجب بـ JSON فقط. لا تضف أي نص قبل أو بعد الـ JSON.').strip()

    raw = ollama_call(prompt, system=json_system, model=model)

    # Strip markdown json fences
    clean = re.sub(r'```(?:json)?\s*|\s*```', '', raw).strip()

    # Find first JSON object or array
    for pattern in (r'\{.*\}', r'\[.*\]'):
        m = re.search(pattern, clean, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass

    # Last resort: try full clean string
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        logger.warning('ollama_json parse failure. raw=%s', raw[:200])
        return fallback or {}


# =========================================================
# STREAMING CALL
# =========================================================

def ollama_stream(
    prompt: str,
    system: str = '',
    model: str = CONFIG.model_main,
) -> Iterator[str]:
    """
    Token-level streaming generator.
    Yields text chunks as they arrive from Ollama.

    Usage:
        for chunk in ollama_stream(prompt):
            print(chunk, end='', flush=True)
    """
    messages: List[Dict[str, str]] = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})

    payload = {
        'model': model,
        'messages': messages,
        'stream': True,
        'options': {
            'temperature':    CONFIG.ollama_temperature,
            'top_p':          CONFIG.ollama_top_p,
            'repeat_penalty': CONFIG.ollama_repeat_penalty,
            'num_ctx':        CONFIG.ollama_num_ctx,
        },
    }

    try:
        with _SESSION.post(
            f'{CONFIG.ollama_url}/api/chat',
            json=payload,
            stream=True,
            timeout=CONFIG.ollama_timeout,
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    chunk = data.get('message', {}).get('content', '')
                    if chunk:
                        yield chunk
                    if data.get('done', False):
                        break
                except json.JSONDecodeError:
                    continue

    except Exception as e:
        logger.exception('Stream error: %s', e)
        yield 'خطأ في التدفق.'


# =========================================================
# HEALTH & INFO
# =========================================================

def health_check() -> bool:
    """Returns True if Ollama is reachable."""
    try:
        r = _SESSION.get(f'{CONFIG.ollama_url}/api/tags', timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def list_models() -> List[str]:
    """Return list of loaded Ollama model names."""
    try:
        r = _SESSION.get(f'{CONFIG.ollama_url}/api/tags', timeout=5)
        r.raise_for_status()
        return [m['name'] for m in r.json().get('models', [])]
    except Exception:
        return []


def model_info(model_name: str) -> dict:
    """Return model metadata (size, quantization, etc.)."""
    try:
        r = _SESSION.post(
            f'{CONFIG.ollama_url}/api/show',
            json={'name': model_name},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}
