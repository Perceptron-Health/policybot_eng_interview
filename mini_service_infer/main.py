import argparse
import json
import sys

from inference import run_inference
from observability import Metrics, Timer, log_event


def main() -> int:
    parser = argparse.ArgumentParser(description="Policybot pairing mini-service (CLI)")
    parser.add_argument("--input", required=True, help="Path to input JSON")
    parser.add_argument(
        "--output", required=False, help="Path to write output JSON (optional)"
    )
    parser.add_argument(
        "--strategy", required=False, help="Override strategy (keyword|rag_llm)"
    )
    args = parser.parse_args()

    metrics = Metrics()
    timer = Timer()

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            payload = json.load(f)

        if args.strategy:
            payload["strategy"] = args.strategy

        metrics.inc("requests_total", 1)

        resp = run_inference(payload)

        metrics.observe_ms("request_latency_ms", timer.elapsed_ms())
        metrics.inc(f"strategy_{payload.get('strategy', 'heyword')}_total", 1)

        out_text = json.dumps(resp, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out_text + "\n")
        else:
            print(out_text)

        log_event({"event": "metrics.snapshot", "metrics": metrics.snapshot()})
        return 0

    except Exception as e:
        metrics.inc("errors_total", 1)
        log_event(
            {"event": "infer.error", "error": repr(e), "metrics": metrics.snapshot()}
        )
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
