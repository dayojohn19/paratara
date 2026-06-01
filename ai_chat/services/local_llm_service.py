import logging
import threading

from django.conf import settings


logger = logging.getLogger(__name__)

STRICT_LOCAL_PROMPT = """You are a local travel assistant for {place_name}.
Answer only from the provided context.
If the context does not contain the answer, say you do not have enough local information.
Use HTML <strong> tags, not markdown.
Keep answer under 80 words.
Never invent URLs, prices, contacts, places, events, or schedules.
Copy URLs exactly from context."""

_llama_model = None
_llama_model_path = None
_llama_lock = threading.Lock()


def discussion_backend():
    return str(getattr(settings, "AI_DISCUSSION_BACKEND", "template") or "template").strip().lower()


def build_context_text(matches, max_chars=4000):
    parts = []
    for match in matches:
        metadata = match.get("metadata", {})
        title = metadata.get("title") or match.get("title") or ""
        kind = metadata.get("kind_label") or metadata.get("kind") or match.get("source_type") or "Result"
        text = match.get("text") or ""
        parts.append(f"[{kind}] {title}\n{text}")
    context = "\n\n".join(parts)
    if len(context) > max_chars:
        context = context[:max_chars].rsplit("\n", 1)[0]
    return context


def build_prompt(message, place_name, matches):
    context = build_context_text(matches)
    return f"""{STRICT_LOCAL_PROMPT.format(place_name=place_name)}

Context:
{context}

User question:
{message}

Answer:"""


def generate_local_llm_answer(message, place_name, matches):
    backend = discussion_backend()
    if backend == "template":
        return ""
    if backend == "ollama":
        return generate_with_ollama(message, place_name, matches)
    if backend == "llama_cpp":
        return generate_with_llama_cpp(message, place_name, matches)
    logger.warning("Unknown AI_DISCUSSION_BACKEND=%s; using template fallback", backend)
    return ""


def generate_with_ollama(message, place_name, matches):
    import requests

    prompt = build_prompt(message, place_name, matches)
    url = getattr(settings, "AI_OLLAMA_URL", "http://localhost:11434/api/generate")
    model = getattr(settings, "AI_OLLAMA_MODEL", "qwen2.5:0.5b")
    timeout = getattr(settings, "AI_DISCUSSION_LOCAL_TIMEOUT", 20)

    response = requests.post(
        url,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 160,
            },
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    return str(payload.get("response", "")).strip()


def _get_llama_cpp_model():
    global _llama_model, _llama_model_path

    model_path = str(getattr(settings, "AI_LLAMA_CPP_MODEL_PATH", "") or "").strip()
    if not model_path:
        raise RuntimeError("AI_LLAMA_CPP_MODEL_PATH is not configured")

    if _llama_model is not None and _llama_model_path == model_path:
        return _llama_model

    with _llama_lock:
        if _llama_model is not None and _llama_model_path == model_path:
            return _llama_model

        from llama_cpp import Llama

        _llama_model = Llama(
            model_path=model_path,
            n_ctx=getattr(settings, "AI_LLAMA_CPP_N_CTX", 2048),
            n_threads=getattr(settings, "AI_LLAMA_CPP_N_THREADS", 4),
            verbose=False,
        )
        _llama_model_path = model_path
        return _llama_model


def generate_with_llama_cpp(message, place_name, matches):
    prompt = build_prompt(message, place_name, matches)
    model = _get_llama_cpp_model()
    response = model(
        prompt,
        max_tokens=160,
        temperature=0.1,
        stop=["\nUser question:", "\nContext:"],
    )
    choices = response.get("choices", [])
    if not choices:
        return ""
    return str(choices[0].get("text", "")).strip()

