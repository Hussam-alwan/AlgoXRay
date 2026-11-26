import argparse
import json
from pathlib import Path

from .engine import Options, analyze
from .problems import PROBLEMS
from .registry import fixture_cards, get_submission, local_submission


def main(argv=None):
    parser = argparse.ArgumentParser(description="AlgoX-Ray local trusted-code workbench")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="List registered fixtures")
    replay = commands.add_parser("replay", help="Replay the witness from a reviewed local evidence bundle")
    replay.add_argument("bundle", type=Path)
    replay.add_argument("--trusted-local-file", action="store_true")
    server = commands.add_parser("serve", help="Start the loopback-only UI")
    server.add_argument("--port", type=int, default=8000)
    command = commands.add_parser("analyze", help="Analyze reviewed local Python code")
    command.add_argument("--problem", choices=list(PROBLEMS), required=True)
    source = command.add_mutually_exclusive_group(required=True)
    source.add_argument("--fixture")
    source.add_argument("--submission", type=Path)
    command.add_argument("--trusted-local-file", action="store_true")
    command.add_argument("--case", type=Path)
    command.add_argument("--strategy", choices=["hypothesis", "random"], default="hypothesis")
    command.add_argument("--seed", type=int, default=2026)
    command.add_argument("--max-examples", type=int, default=100)
    command.add_argument("--max-seconds", type=float, default=10)
    command.add_argument("--no-shrink", action="store_true")
    command.add_argument("--no-trace", action="store_true")
    command.add_argument("--output", type=Path)
    command.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "list":
        print(json.dumps(fixture_cards(), ensure_ascii=True, indent=2))
        return 0
    if args.command == "replay":
        if not args.trusted_local_file:
            parser.error("Review the embedded Python first, then supply --trusted-local-file")
        from .replay import replay_witness
        try:
            outcome = replay_witness(json.loads(args.bundle.read_text(encoding="utf-8-sig")))
        except (KeyError, TypeError, ValueError, OSError) as exc:
            parser.error(str(exc))
        print(json.dumps(outcome, indent=2))
        return 0 if outcome["matched"] else 1
    if args.command == "serve":
        import uvicorn
        uvicorn.run("algoxray.api:app", host="127.0.0.1", port=args.port)
        return 0
    if args.submission and not args.trusted_local_file:
        parser.error("Local files require --trusted-local-file after reviewing the code; no sandbox is provided")
    try:
        sub = local_submission(args.problem, args.submission) if args.submission else get_submission(args.fixture)
        if sub.problem_id != args.problem:
            raise ValueError("Fixture/problem mismatch")
        case = json.loads(args.case.read_text(encoding="utf-8-sig")) if args.case else None
        result = analyze(sub, Options(seed=args.seed, strategy=args.strategy, max_examples=args.max_examples,
                                      max_seconds=args.max_seconds, shrink=not args.no_shrink,
                                      include_trace=not args.no_trace), case=case)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    if args.summary:
        print(json.dumps({k: result[k] for k in ("run_id", "status", "failure_kind", "evidence_level", "case", "statistics")}, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=True, indent=2, allow_nan=False))
    return 0 if result["status"] in ("witness_found", "inconclusive") else 1


if __name__ == "__main__":
    raise SystemExit(main())
