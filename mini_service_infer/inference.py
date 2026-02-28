import hashlib
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from observability import log_event


def _sha256(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def infer_keyword_match(
    policy_text: str, hcpcs_catalog: List[Dict[str, str]]
) -> List[Dict[str, Any]]:
    """
    Simple keyword matching against HCPCS descriptions.
    """
    t = policy_text.lower()
    scored: List[Tuple[Dict[str, str], float]] = []

    for item in hcpcs_catalog:
        d = item["description"].lower()
        score = 0.0

        if "home infusion" in t and "home infusion" in d:
            score += 0.6
        if "antibiotic" in t and "antibiotic" in d:
            score += 0.3
        if ("supplies" in t or "equipment" in t) and (
            "suppl" in d or "pump" in d or "pole" in d
        ):
            score += 0.2

        if score > 0:
            scored.append((item, min(score, 1.0)))

    scored.sort(key=lambda x: x[1], reverse=True)
    out: List[Dict[str, Any]] = []
    for item, conf in scored[:3]:
        out.append(
            {
                "code": item["code"],
                "confidence": round(conf, 2),
                "justification": f"Keword match on HCPCS description: {item['description']}",
                "provenance": {"strategy": "keyword"},
            }
        )
    return out


def infer_rag_llm(
    policy_text: str, hcpcs_catalog: List[Dict[str, str]]
) -> List[Dict[str, Any]]:
    """
    Mocked 'RAG+LLM' that selects one HCPCS code with weighted randomness.
    Intentionally non-deterministic (great for observability + debugging discussion).
    """
    if not hcpcs_catalog:
        return []

    t = policy_text.lower()
    weights = []
    for item in hcpcs_catalog:
        d = item["description"].lower()
        w = 0.1
        if "home infusion" in d and "home infusion" in t:
            w += 1.0
        if "antibiotic" in d and "antibiotic" in t:
            w += 0.7
        if ("supplies" in t or "equipment" in t) and ("suppl" in d or "pump" in d):
            w += 0.3
        weights.append(w)

    picked = random.choices(hcpcs_catalog, weights=weights, k=1)[0]
    return [
        {
            "code": picked["code"],
            "confidence": 0.78,
            "justification": "Mocked RAG+LLM selection from hcpcs_catalog based on semantic alignment.",
            "provenance": {
                "strategy": "rag_llm",
                "model": "mock-llm",
                "prompt_id": "mock_v1",
            },
        }
    ]


## added
def infer_ensemble(policy_text: str, hcpcs_catalog: List[Dict[str, str]]):
    keyword_codes = infer_keyword_match(policy_text, hcpcs_catalog)
    rag_codes = infer_rag_llm(policy_text, hcpcs_catalog)
    ensemble_codes = keyword_codes + rag_codes
    ensemble_codes.sort(key=lambda x: x["confidence"], reverse=True)
    return ensemble_codes


def run_inference(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    accepts a single strategy (default keyword match).
    TODO: extend to multiple strategies and/or compare results.
    """
    request_id = payload["request_id"]
    policy_text = payload["policy_text"]
    hcpcs_catalog = payload.get("hcpcs_catalog", [])
    options = payload.get("options", {})
    strategy = payload.get("strategy", "keyword")
    max_codes = int(options.get("max_codes", 3))

    run_id = "run_" + uuid.uuid4().hex[:12]
    policy_hash = _sha256(policy_text)
    hcpcs_hash = _sha256("|".join([x["code"] for x in hcpcs_catalog]))

    if strategy == "keyword":
        codes = infer_keyword_match(policy_text, hcpcs_catalog)[:max_codes]
        method = {"strategy": "keyword"}
    elif strategy == "rag_llm":
        codes = infer_rag_llm(policy_text, hcpcs_catalog)[:max_codes]
        method = {"strategy": "rag_llm", "model": "mock-llm", "prompt_id": "mock_v1"}
    ## added
    elif strategy == "ensemble":
        codes = infer_ensemble(policy_text, hcpcs_catalog)[:max_codes]
        method = {"strategy": "ensemble", "model": "mock-llm", "prompt_id": "mock_v1"}
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    resp = {
        "schema_version": "hcpcs_inference.v1",
        "request_id": request_id,
        "inference_run_id": run_id,
        "needs_review": False,
        "codes": codes,
        "audit": {
            "timestamp": _now_iso(),
            "inputs": {"policy_fragment_hash": policy_hash, "hcpcs_hash": hcpcs_hash},
            "method": method,
        },
    }

    log_event(
        {
            "event": "infer.completed",
            "request_id": request_id,
            "inference_run_id": run_id,
            "strategy": strategy,
            "codes_count": len(codes),
        }
    )

    return resp
