"""Replies of the providers, written by hand for the tests.

ATENÇÃO: nada neste ficheiro é uma resposta real de um fornecedor. São fixtures escritas a partir da documentação
oficial lida a 2026-10-11 (os URLs estão em cada classe de `aferidor/providers.py`), com os nomes de campos que essa
documentação dá. Onde a documentação não abriu (OpenAI, vLLM), a forma é a que os fornecedores anteriores já liam e
está por confirmar contra uma resposta real, que só o piloto traz.
"""

from __future__ import annotations

ANSWER = "Amoxicilina 1000 mg de 8 em 8 horas durante 7 dias. Atenção a alergias a penicilinas."

# https://platform.claude.com/docs/en/api/messages/create (the page's example response and field list)
ANTHROPIC_OK = {
    "id": "msg_013Zva2CMHLNnXjNJJKqJ2EF",
    "type": "message",
    "role": "assistant",
    "model": "claude-opus-5-5",
    "content": [{"type": "thinking", "thinking": "...", "signature": "abc"}, {"type": "text", "text": ANSWER}],
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "usage": {"input_tokens": 140, "output_tokens": 900, "output_tokens_details": {"thinking_tokens": 600}, "service_tier": "standard"},
}
ANTHROPIC_REFUSAL = {
    **ANTHROPIC_OK, "content": [], "stop_reason": "refusal",
    "stop_details": {"type": "refusal", "category": "general_harms", "explanation": "..."},
}
ANTHROPIC_MAX_TOKENS = {**ANTHROPIC_OK, "content": [{"type": "text", "text": "Amoxicilina 10"}], "stop_reason": "max_tokens"}
# https://platform.claude.com/docs/en/api/errors ("Error shapes")
ANTHROPIC_ERROR = {"type": "error", "error": {"type": "rate_limit_error", "message": "rate limited"}, "request_id": "req_011"}

# https://ai.google.dev/api/generate-content (usageMetadata, modelVersion, candidates[].finishReason)
GOOGLE_OK = {
    "candidates": [{"content": {"role": "model", "parts": [{"text": ANSWER}]}, "finishReason": "STOP", "index": 0}],
    "usageMetadata": {"promptTokenCount": 130, "candidatesTokenCount": 700, "thoughtsTokenCount": 450, "totalTokenCount": 1280},
    "modelVersion": "gemini-3.8-flash",
}
GOOGLE_MAX_TOKENS = {**GOOGLE_OK, "candidates": [{"content": {"parts": [{"text": "Amoxi"}]}, "finishReason": "MAX_TOKENS"}]}
GOOGLE_SAFETY = {**GOOGLE_OK, "candidates": [{"finishReason": "SAFETY"}]}
GOOGLE_BLOCKED_PROMPT = {
    "promptFeedback": {"blockReason": "SAFETY"},
    "usageMetadata": {"promptTokenCount": 130, "totalTokenCount": 130},
    "modelVersion": "gemini-3.8-flash",
}
GOOGLE_WITH_THOUGHT_PARTS = {
    **GOOGLE_OK,
    "candidates": [{"content": {"parts": [{"text": "A pensar...", "thought": True}, {"text": ANSWER}]}, "finishReason": "STOP"}],
}
GOOGLE_MODELS = {"models": [{"name": "models/gemini-3.8-flash"}, {"name": "models/gemini-3.1-pro-preview"}]}

# The OpenAI Chat Completions shape the earlier providers read (the official page did not open: por confirmar)
OPENAI_OK = {
    "id": "chatcmpl-1", "object": "chat.completion", "model": "gpt-6-astra",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": ANSWER}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 120, "completion_tokens": 800, "completion_tokens_details": {"reasoning_tokens": 500}},
}
OPENAI_FILTERED = {**OPENAI_OK, "choices": [{"index": 0, "message": {"role": "assistant", "content": None}, "finish_reason": "content_filter"}]}

# A vLLM server (por confirmar: the page read does not describe either reply)
VLLM_MODELS = {"object": "list", "data": [{"id": "AMALIA-9B-0626-DPO", "object": "model", "owned_by": "vllm"}]}
VLLM_OTHER_MODELS = {"object": "list", "data": [{"id": "outro-modelo", "object": "model"}]}
VLLM_CHAT = {
    "id": "chatcmpl-2", "object": "chat.completion", "model": "AMALIA-9B-0626-DPO",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": ANSWER}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 125, "completion_tokens": 400},
}
