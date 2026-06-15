#!/usr/bin/env python3
"""
AIRL Training Data Generator
=============================
Generates a structured dataset of AIRL programs for AI model training.

Each dataset entry contains:
  - program.jsonld      : The AIRL computation graph
  - intent.jsonld       : The structured goal that motivated the program
  - sidecar.jsonld      : Provenance graph with confidence scores
  - verification.jsonld : Compiler verification report
  - label               : VALID / INVALID
  - mutation            : (for INVALID entries) description of what's wrong

Usage:
    python generate.py --count 500 --output ./dataset --seed 42
    python generate.py --count 1000 --output ./dataset --difficulty 1 2 3
    python generate.py --count 200 --template hello_world echo_stdin
    python generate.py --count 500 --negative-ratio 0.3 --output ./dataset
    python generate.py --list-templates
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .builder import ProgramBuilder
from .verifier import Verifier, PassStatus
from .mutations import mutate, MutationType
from .templates import TEMPLATES, TEMPLATES_BY_NAME, TEMPLATES_BY_DIFFICULTY


# ── Dataset entry ─────────────────────────────────────────────────────────────

@dataclass
class DatasetEntry:
    entry_id: str
    template_name: str
    difficulty: int
    label: str               # "VALID" or "INVALID"
    program: dict
    intent: dict
    sidecar: dict
    verification: dict
    mutation_type: Optional[str] = None
    mutation_description: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    seed: int = 0

    def to_dict(self) -> dict:
        return {
            "entryId": self.entry_id,
            "templateName": self.template_name,
            "difficulty": self.difficulty,
            "label": self.label,
            "seed": self.seed,
            "tags": self.tags,
            "mutationType": self.mutation_type,
            "mutationDescription": self.mutation_description,
            "program": self.program,
            "intent": self.intent,
            "sidecar": self.sidecar,
            "verification": self.verification,
        }


# ── Generator ─────────────────────────────────────────────────────────────────

class DatasetGenerator:
    def __init__(self, model_id: str = "claude-sonnet-4-6"):
        self.builder = ProgramBuilder()
        self.verifier = Verifier()
        self.model_id = model_id
        self._mutation_types = list(MutationType)

    def generate_entry(
        self,
        template_name: str,
        seed: int,
        negative: bool = False,
    ) -> DatasetEntry:
        rng = random.Random(seed)
        template = TEMPLATES_BY_NAME[template_name]

        program, intent, sidecar = self.builder.build(template, rng, self.model_id)
        program_id = program["id"]

        mutation_type = None
        mutation_desc = None

        if negative:
            mt = rng.choice(self._mutation_types)
            program, mutation_desc = mutate(program, mt, rng)
            mutation_type = mt.value

        # Extract graph for verification
        from .graph import ComputationGraph, Node, Edge, NodeKind, EdgeKind
        from .types import Primitive, PrimitiveType

        # Reconstruct a minimal graph object for the verifier
        raw_graph = program.get("graph", {})
        graph = ComputationGraph()
        for n in raw_graph.get("nodes", []):
            from .types import T_UNIT
            node = Node(
                node_id=n["id"],
                kind=NodeKind(n["@type"]) if n["@type"] in [k.value for k in NodeKind] else NodeKind.EXEC,
                value_type=T_UNIT,  # simplified: verifier uses declared type string
                confidence=n.get("confidence", 1.0),
            )
            # Re-attach effects
            if n.get("effects"):
                from .types import EffectType
                for e in n["effects"]:
                    try:
                        node.effects.append(EffectType(e))
                    except ValueError:
                        pass
            if n.get("op"):
                from .graph import Op
                try:
                    node.op = Op(n["op"])
                except ValueError:
                    pass
            if n.get("@type") == "LITERAL":
                node.kind = NodeKind.LITERAL
                node.literal_value = n.get("data")
            graph.nodes.append(node)

        for e in raw_graph.get("edges", []):
            graph.edges.append(Edge(
                from_id=e["from"],
                to_id=e["to"],
                kind=EdgeKind(e.get("type", "DATA")),
                slot=e.get("slot"),
            ))
        graph.entry_id = raw_graph.get("entry")

        verification = self.verifier.verify(graph, program_id)
        label = "VALID" if (not negative and verification.overall_status != PassStatus.FAIL) else "INVALID"

        entry_id = hashlib.sha256(
            f"{template_name}:{seed}:{negative}".encode()
        ).hexdigest()[:16]

        return DatasetEntry(
            entry_id=entry_id,
            template_name=template_name,
            difficulty=template.difficulty,
            label=label,
            program=program,
            intent=intent,
            sidecar=sidecar,
            verification=verification.to_dict(),
            mutation_type=mutation_type,
            mutation_description=mutation_desc,
            tags=template.tags,
            seed=seed,
        )

    def generate_dataset(
        self,
        count: int,
        templates: Optional[list[str]] = None,
        difficulties: Optional[list[int]] = None,
        negative_ratio: float = 0.2,
        base_seed: int = 42,
        verbose: bool = True,
    ) -> list[DatasetEntry]:
        """Generate `count` dataset entries."""

        # Filter template pool
        pool = TEMPLATES[:]
        if templates:
            pool = [t for t in pool if t.name in templates]
        if difficulties:
            pool = [t for t in pool if t.difficulty in difficulties]

        if not pool:
            raise ValueError("No templates match the given filters.")

        rng = random.Random(base_seed)
        entries: list[DatasetEntry] = []
        n_negative = int(count * negative_ratio)
        n_positive = count - n_negative

        plan: list[tuple[str, bool]] = []
        for _ in range(n_positive):
            plan.append((rng.choice(pool).name, False))
        for _ in range(n_negative):
            plan.append((rng.choice(pool).name, True))
        rng.shuffle(plan)

        total = len(plan)
        start = time.time()

        for i, (tname, is_neg) in enumerate(plan):
            seed = rng.randint(0, 2**31)
            try:
                entry = self.generate_entry(tname, seed, negative=is_neg)
                entries.append(entry)
            except Exception as exc:
                if verbose:
                    _log(f"  [WARN] Entry {i+1} failed ({tname}, neg={is_neg}): {exc}")
                continue

            if verbose and (i + 1) % max(1, total // 20) == 0:
                elapsed = time.time() - start
                rate = (i + 1) / elapsed
                remaining = (total - i - 1) / rate if rate > 0 else 0
                pct = (i + 1) / total * 100
                _log(
                    f"  [{pct:5.1f}%] {i+1:>6}/{total}"
                    f"  valid={sum(1 for e in entries if e.label=='VALID')}"
                    f"  invalid={sum(1 for e in entries if e.label=='INVALID')}"
                    f"  {rate:.1f}/s  ETA {remaining:.0f}s"
                )

        return entries


# ── Output writers ────────────────────────────────────────────────────────────

def write_dataset(
    entries: list[DatasetEntry],
    output_dir: Path,
    formats: list[str],
    verbose: bool = True,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    if "jsonl" in formats:
        path = output_dir / "dataset.jsonl"
        with open(path, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry.to_dict(), separators=(",", ":")) + "\n")
        written["jsonl"] = path
        if verbose:
            _log(f"  Wrote {len(entries)} entries → {path}")

    if "json" in formats:
        path = output_dir / "dataset.json"
        with open(path, "w") as f:
            json.dump(
                {"entries": [e.to_dict() for e in entries]},
                f, indent=2,
            )
        written["json"] = path
        if verbose:
            _log(f"  Wrote dataset.json → {path}")

    if "split" in formats:
        split_dir = output_dir / "split"
        split_dir.mkdir(exist_ok=True)
        valid_path = split_dir / "valid.jsonl"
        invalid_path = split_dir / "invalid.jsonl"
        with open(valid_path, "w") as vf, open(invalid_path, "w") as ivf:
            for entry in entries:
                line = json.dumps(entry.to_dict(), separators=(",", ":")) + "\n"
                if entry.label == "VALID":
                    vf.write(line)
                else:
                    ivf.write(line)
        written["split_valid"] = valid_path
        written["split_invalid"] = invalid_path
        if verbose:
            _log(f"  Wrote split/ valid+invalid → {split_dir}")

    if "files" in formats:
        files_dir = output_dir / "files"
        files_dir.mkdir(exist_ok=True)
        for entry in entries:
            entry_dir = files_dir / entry.entry_id
            entry_dir.mkdir(exist_ok=True)
            for name, data in [
                ("program.jsonld",      entry.program),
                ("intent.jsonld",       entry.intent),
                ("sidecar.jsonld",      entry.sidecar),
                ("verification.jsonld", entry.verification),
            ]:
                (entry_dir / name).write_text(json.dumps(data, indent=2))
            meta = {
                "entryId": entry.entry_id,
                "templateName": entry.template_name,
                "difficulty": entry.difficulty,
                "label": entry.label,
                "seed": entry.seed,
                "tags": entry.tags,
                "mutationType": entry.mutation_type,
                "mutationDescription": entry.mutation_description,
            }
            (entry_dir / "meta.json").write_text(json.dumps(meta, indent=2))
        written["files"] = files_dir
        if verbose:
            _log(f"  Wrote {len(entries)} individual entry dirs → {files_dir}")

    # Always write a manifest
    manifest = _build_manifest(entries, formats, written)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    written["manifest"] = manifest_path
    if verbose:
        _log(f"  Wrote manifest.json → {manifest_path}")

    return written


def _build_manifest(
    entries: list[DatasetEntry],
    formats: list[str],
    written: dict[str, Path],
) -> dict:
    template_counts: dict[str, int] = {}
    difficulty_counts: dict[int, int] = {}
    mutation_counts: dict[str, int] = {}

    for e in entries:
        template_counts[e.template_name] = template_counts.get(e.template_name, 0) + 1
        difficulty_counts[e.difficulty] = difficulty_counts.get(e.difficulty, 0) + 1
        if e.mutation_type:
            mutation_counts[e.mutation_type] = mutation_counts.get(e.mutation_type, 0) + 1

    return {
        "@type": "AIRL_DATASET_MANIFEST",
        "version": "1.0",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "totalEntries": len(entries),
        "validEntries": sum(1 for e in entries if e.label == "VALID"),
        "invalidEntries": sum(1 for e in entries if e.label == "INVALID"),
        "formats": formats,
        "templateCounts": template_counts,
        "difficultyCounts": {str(k): v for k, v in sorted(difficulty_counts.items())},
        "mutationCounts": mutation_counts,
        "outputFiles": {k: str(v) for k, v in written.items()},
        "schema": {
            "programContext": "https://airl-spec.org/v1/context.jsonld",
            "intentContext": "https://airl-spec.org/v1/intent.jsonld",
            "provenanceContext": "https://airl-spec.org/v1/provenance.jsonld",
        },
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def _log(msg: str):
    print(msg, flush=True)


def _print_stats(entries: list[DatasetEntry]):
    valid = sum(1 for e in entries if e.label == "VALID")
    invalid = len(entries) - valid
    diffs: dict[int, int] = {}
    tmpl: dict[str, int] = {}
    muts: dict[str, int] = {}
    for e in entries:
        diffs[e.difficulty] = diffs.get(e.difficulty, 0) + 1
        tmpl[e.template_name] = tmpl.get(e.template_name, 0) + 1
        if e.mutation_type:
            muts[e.mutation_type] = muts.get(e.mutation_type, 0) + 1

    _log("")
    _log("─" * 60)
    _log("  DATASET SUMMARY")
    _log("─" * 60)
    _log(f"  Total entries : {len(entries)}")
    _log(f"  Valid         : {valid} ({valid/len(entries)*100:.1f}%)")
    _log(f"  Invalid       : {invalid} ({invalid/len(entries)*100:.1f}%)")
    _log("")
    _log("  By difficulty:")
    for d in sorted(diffs):
        _log(f"    Level {d}: {diffs[d]}")
    _log("")
    _log("  By template:")
    for t in sorted(tmpl, key=lambda x: -tmpl[x]):
        _log(f"    {t:<30} {tmpl[t]}")
    if muts:
        _log("")
        _log("  Mutation types (invalid entries):")
        for m in sorted(muts, key=lambda x: -muts[x]):
            _log(f"    {m:<40} {muts[m]}")
    _log("─" * 60)


def build_cli_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="airl-gen",
        description="AIRL Training Data Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--count", "-n", type=int, default=100,
        help="Number of dataset entries to generate (default: 100)",
    )
    p.add_argument(
        "--output", "-o", type=Path, default=Path("./airl_dataset"),
        help="Output directory (default: ./airl_dataset)",
    )
    p.add_argument(
        "--seed", "-s", type=int, default=42,
        help="Base random seed for reproducibility (default: 42)",
    )
    p.add_argument(
        "--difficulty", "-d", type=int, nargs="+",
        choices=[1, 2, 3, 4],
        help="Filter to specific difficulty levels (1=trivial, 4=complex)",
    )
    p.add_argument(
        "--template", "-t", type=str, nargs="+",
        help="Filter to specific template names (use --list-templates to see all)",
    )
    p.add_argument(
        "--negative-ratio", type=float, default=0.2,
        help="Fraction of entries that should be INVALID (default: 0.2)",
    )
    p.add_argument(
        "--format", "-f", type=str, nargs="+",
        default=["jsonl", "split"],
        choices=["jsonl", "json", "split", "files"],
        help="Output format(s): jsonl, json, split, files (default: jsonl split)",
    )
    p.add_argument(
        "--model-id", type=str, default="claude-sonnet-4-6",
        help="Model ID to embed in provenance metadata",
    )
    p.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress progress output",
    )
    p.add_argument(
        "--list-templates", action="store_true",
        help="List all available templates and exit",
    )
    return p


def list_templates():
    _log("")
    _log("Available AIRL program templates:")
    _log("")
    _log(f"  {'Name':<35} {'Diff':<6} {'Effects':<40} Tags")
    _log("  " + "─" * 100)
    for t in TEMPLATES:
        fx = ",".join(e.value for e in t.effects) or "(none)"
        tags = ",".join(t.tags)
        _log(f"  {t.name:<35} {t.difficulty:<6} {fx:<40} {tags}")
    _log("")
    _log(f"  Total: {len(TEMPLATES)} templates across difficulty levels 1–4")
    _log("")


def main(argv=None):
    parser = build_cli_parser()
    args = parser.parse_args(argv)

    if args.list_templates:
        list_templates()
        return

    verbose = not args.quiet

    if verbose:
        _log("")
        _log("AIRL Training Data Generator")
        _log("─" * 60)
        _log(f"  Count         : {args.count}")
        _log(f"  Output        : {args.output}")
        _log(f"  Seed          : {args.seed}")
        _log(f"  Negative ratio: {args.negative_ratio:.0%}")
        _log(f"  Formats       : {', '.join(args.format)}")
        if args.difficulty:
            _log(f"  Difficulty    : {args.difficulty}")
        if args.template:
            _log(f"  Templates     : {args.template}")
        _log("")

    generator = DatasetGenerator(model_id=args.model_id)

    if verbose:
        _log("Generating entries...")

    t0 = time.time()
    entries = generator.generate_dataset(
        count=args.count,
        templates=args.template,
        difficulties=args.difficulty,
        negative_ratio=args.negative_ratio,
        base_seed=args.seed,
        verbose=verbose,
    )
    elapsed = time.time() - t0

    if verbose:
        _log(f"\nGenerated {len(entries)} entries in {elapsed:.1f}s")
        _log("\nWriting output...")

    write_dataset(entries, args.output, args.format, verbose=verbose)

    if verbose:
        _print_stats(entries)
        _log(f"\n  Done. Output: {args.output.resolve()}")
        _log("")


if __name__ == "__main__":
    main()
