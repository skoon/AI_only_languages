# AIRL Training Data Generator

Generates structured training datasets for teaching an AI model to emit valid
AIRL (AI-Ready Language) computation graphs.

## Quick Start

```bash
# Generate 500 entries (default 20% invalid)
python generate.py --count 500 --output ./dataset

# Generate 1000 entries, 30% invalid, difficulty 1–3 only
python generate.py --count 1000 --negative-ratio 0.3 --difficulty 1 2 3

# Generate only IO-related programs
python generate.py --count 200 --template hello_world echo_stdin file_read_emit

# List all available templates
python generate.py --list-templates

# All output formats
python generate.py --count 500 --format jsonl json split files
```

## Output Formats

| Format  | Description |
|---------|-------------|
| `jsonl` | One entry per line (default, best for training) |
| `json`  | Full dataset as a single JSON array |
| `split` | Separate valid.jsonl and invalid.jsonl files |
| `files` | One directory per entry with individual .jsonld files |

Every run also produces `manifest.json` with full dataset statistics.

## Dataset Entry Structure

Each entry contains:

```json
{
  "entryId": "abc123...",
  "templateName": "safe_divide",
  "difficulty": 2,
  "label": "VALID",
  "seed": 1234567,
  "tags": ["arithmetic", "error-handling", "pure"],
  "mutationType": null,
  "mutationDescription": null,
  "program": { ... },       // AIRL computation graph (JSON-LD)
  "intent": { ... },        // Structured goal that motivated this program
  "sidecar": { ... },       // Provenance graph with per-node confidence scores
  "verification": { ... }   // Compiler verification report
}
```

For `INVALID` entries, `mutationType` and `mutationDescription` describe exactly
what error was introduced.

## Templates (23 total)

Templates are grouped by difficulty:

| Level | Count | Description |
|-------|-------|-------------|
| 1 | 4  | Trivial: literals, echo, simple arithmetic |
| 2 | 6  | Simple: params, type coercion, conditionals |
| 3 | 7  | Moderate: pipelines, collections, error handling |
| 4 | 6  | Complex: reduce, crypto, AI calls, network, time |

## Mutation Types (10 types for negative examples)

| Mutation | Error Introduced |
|----------|-----------------|
| `MISSING_EFFECT_DECLARATION` | Effect used but not declared on node |
| `TYPE_MISMATCH` | Node valueType changed to incompatible type |
| `DANGLING_EDGE_REFERENCE` | Edge references a non-existent node UUID |
| `MISSING_ENTRY_POINT` | Entry point set to null |
| `NULL_LITERAL_VALUE` | LITERAL node data set to null |
| `WRONG_OP_FOR_TYPE` | Op replaced with one of wrong signature |
| `DEAD_NODE_ADDED` | Unreachable node appended to graph |
| `DUPLICATE_NODE_ID` | Two nodes given the same UUID |
| `LOW_CONFIDENCE_NODE` | Confidence score set below 0.75 threshold |
| `INVALID_CONFIDENCE_RANGE` | Confidence set outside [0.0, 1.0] |

## Module Structure

```
airl_generator/
  __init__.py      Package root
  types.py         AIRL type system (primitives, composites, effects)
  graph.py         Node, Edge, ComputationGraph definitions
  verifier.py      6-pass verification engine
  templates.py     23 program template definitions
  builder.py       Concrete graph builders (one per template)
  mutations.py     10 mutation types for negative examples
  generator.py     Dataset orchestrator and CLI
generate.py        Entrypoint
```

## Performance

~4,000 entries/second on a single core. 1,000,000 entries ≈ 4 minutes.
Generation is fully deterministic given a `--seed`.

## Using the Dataset for Training

The `label` field is the primary training signal:
- `VALID` → the model should learn to emit graphs like this
- `INVALID` → the model should learn to avoid graphs like this

For each `INVALID` entry, the `verification` field contains structured error
reports that can be used as additional training signal — teaching the model to
predict not just whether a graph is valid, but *why* it failed.

The `intent` field can be used to train goal-to-graph decomposition:
given a structured intent graph, predict the corresponding AIRL program.

The `sidecar.nodes[].confidence` fields can be used to train calibration:
given a node and its context, predict how likely it is to pass verification.
