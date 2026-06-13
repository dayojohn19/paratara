import threading

from django.conf import settings



DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_model = None
_model_name = None
_model_lock = threading.Lock()


def get_embedding_model():
    """Load the sentence-transformers model once, on CPU."""
    global _model, _model_name

    configured_name = getattr(settings, "AI_DISCUSSION_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    configured_name = configured_name or DEFAULT_EMBEDDING_MODEL
    local_files_only = bool(getattr(settings, "AI_DISCUSSION_EMBEDDING_LOCAL_FILES_ONLY", False))

    cache_key = (configured_name, local_files_only)

    if _model is not None and _model_name == cache_key:
        return _model

    with _model_lock:
        if _model is not None and _model_name == cache_key:
            return _model

        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(
            configured_name,
            device="cpu",
            local_files_only=local_files_only,
        )
        _model_name = cache_key
        return _model


def embed_text(text):
    embeddings = embed_texts([text])
    return embeddings[0] if embeddings else []


def embed_texts(texts):
    cleaned = [str(text or "").strip() for text in texts]
    if not cleaned:
        return []

    model = get_embedding_model()
    vectors = model.encode(
        cleaned,
        batch_size=getattr(settings, "AI_DISCUSSION_EMBEDDING_BATCH_SIZE", 16),
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return [[float(value) for value in vector] for vector in vectors]


def cosine_similarity(left, right):
    if not left or not right or len(left) != len(right):
        return 0.0

    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for a, b in zip(left, right):
        a = float(a)
        b = float(b)
        dot += a * b
        left_norm += a * a
        right_norm += b * b

    if left_norm <= 0 or right_norm <= 0:
        return 0.0
    return dot / ((left_norm ** 0.5) * (right_norm ** 0.5))
