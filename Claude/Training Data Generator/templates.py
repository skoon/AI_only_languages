"""
AIRL Program Templates
Structured templates that define families of programs the generator can produce.
Each template describes an intent, the graph pattern, and the expected I/O types.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional
from .types import AIRLType, EffectType


@dataclass
class ProgramTemplate:
    """
    Describes a family of AIRL programs with the same structure.
    The `build_fn` is called by the generator with a random seed to produce
    concrete variants within the family.
    """
    name: str
    description: str
    goal_class: str          # e.g. "airl:goal:io-transform"
    goal_ontology_ref: str
    difficulty: int          # 1=trivial, 2=simple, 3=moderate, 4=complex
    input_types: list[str]   # human-readable type descriptions
    output_type: str
    effects: list[EffectType]
    tags: list[str] = field(default_factory=list)

    def __repr__(self):
        return f"<Template '{self.name}' difficulty={self.difficulty}>"


# ── Registry of all available templates ──────────────────────────────────────

TEMPLATES: list[ProgramTemplate] = [

    # ── Difficulty 1: Trivial ─────────────────────────────────────────────

    ProgramTemplate(
        name="hello_world",
        description="Emit a fixed Unicode string to stdout",
        goal_class="airl:goal:io-emit",
        goal_ontology_ref="airl:intent:emit-value-to-stdout",
        difficulty=1,
        input_types=[],
        output_type="UNIT",
        effects=[EffectType.IO_STDOUT],
        tags=["io", "literal", "trivial"],
    ),

    ProgramTemplate(
        name="echo_stdin",
        description="Read a line from stdin and echo it to stdout",
        goal_class="airl:goal:io-passthrough",
        goal_ontology_ref="airl:intent:passthrough-stdin-stdout",
        difficulty=1,
        input_types=[],
        output_type="UNIT",
        effects=[EffectType.IO_STDIN, EffectType.IO_STDOUT],
        tags=["io", "passthrough"],
    ),

    ProgramTemplate(
        name="constant_arithmetic",
        description="Compute a fixed arithmetic expression from literals",
        goal_class="airl:goal:compute",
        goal_ontology_ref="airl:intent:arithmetic-constant",
        difficulty=1,
        input_types=[],
        output_type="INT64",
        effects=[],
        tags=["arithmetic", "pure", "literal"],
    ),

    ProgramTemplate(
        name="boolean_logic",
        description="Evaluate a boolean expression over literal values",
        goal_class="airl:goal:compute",
        goal_ontology_ref="airl:intent:boolean-evaluation",
        difficulty=1,
        input_types=[],
        output_type="BOOL",
        effects=[],
        tags=["logic", "pure", "literal"],
    ),

    # ── Difficulty 2: Simple ──────────────────────────────────────────────

    ProgramTemplate(
        name="integer_add_params",
        description="Add two INT64 parameters and return the result",
        goal_class="airl:goal:compute",
        goal_ontology_ref="airl:intent:arithmetic-param",
        difficulty=2,
        input_types=["INT64", "INT64"],
        output_type="INT64",
        effects=[],
        tags=["arithmetic", "pure", "param"],
    ),

    ProgramTemplate(
        name="string_concat_params",
        description="Concatenate two UNICODE parameters",
        goal_class="airl:goal:string-transform",
        goal_ontology_ref="airl:intent:string-concat",
        difficulty=2,
        input_types=["UNICODE", "UNICODE"],
        output_type="UNICODE",
        effects=[],
        tags=["string", "pure", "param"],
    ),

    ProgramTemplate(
        name="safe_divide",
        description="Divide two integers, returning UNION[INT64, ERR_DIV_ZERO]",
        goal_class="airl:goal:compute",
        goal_ontology_ref="airl:intent:safe-arithmetic",
        difficulty=2,
        input_types=["INT64", "INT64"],
        output_type="UNION[INT64,UNICODE]",
        effects=[],
        tags=["arithmetic", "error-handling", "pure"],
    ),

    ProgramTemplate(
        name="int_to_string_emit",
        description="Convert an INT64 parameter to UNICODE and emit to stdout",
        goal_class="airl:goal:io-emit",
        goal_ontology_ref="airl:intent:coerce-and-emit",
        difficulty=2,
        input_types=["INT64"],
        output_type="UNIT",
        effects=[EffectType.IO_STDOUT],
        tags=["io", "coercion", "param"],
    ),

    ProgramTemplate(
        name="compare_integers",
        description="Compare two integers and return a BOOL",
        goal_class="airl:goal:compute",
        goal_ontology_ref="airl:intent:comparison",
        difficulty=2,
        input_types=["INT64", "INT64"],
        output_type="BOOL",
        effects=[],
        tags=["comparison", "pure"],
    ),

    ProgramTemplate(
        name="conditional_emit",
        description="Conditionally emit one of two strings based on a boolean",
        goal_class="airl:goal:io-conditional",
        goal_ontology_ref="airl:intent:conditional-io",
        difficulty=2,
        input_types=["BOOL"],
        output_type="UNIT",
        effects=[EffectType.IO_STDOUT],
        tags=["io", "conditional", "cond"],
    ),

    # ── Difficulty 3: Moderate ────────────────────────────────────────────

    ProgramTemplate(
        name="string_length_pipeline",
        description="Read a string param, compute length, convert to string, emit",
        goal_class="airl:goal:string-transform",
        goal_ontology_ref="airl:intent:string-analysis-emit",
        difficulty=3,
        input_types=["UNICODE"],
        output_type="UNIT",
        effects=[EffectType.IO_STDOUT],
        tags=["string", "pipeline", "io"],
    ),

    ProgramTemplate(
        name="arithmetic_chain",
        description="Chain multiple arithmetic operations: (a + b) * (c - d)",
        goal_class="airl:goal:compute",
        goal_ontology_ref="airl:intent:arithmetic-chain",
        difficulty=3,
        input_types=["INT64", "INT64", "INT64", "INT64"],
        output_type="INT64",
        effects=[],
        tags=["arithmetic", "chain", "pure"],
    ),

    ProgramTemplate(
        name="read_parse_compute",
        description="Read a string from stdin, parse to INT64, compute modulo, emit result",
        goal_class="airl:goal:io-transform",
        goal_ontology_ref="airl:intent:parse-compute-emit",
        difficulty=3,
        input_types=[],
        output_type="UNIT",
        effects=[EffectType.IO_STDIN, EffectType.IO_STDOUT],
        tags=["io", "parse", "arithmetic"],
    ),

    ProgramTemplate(
        name="map_transform",
        description="Apply a pure function to every element of a LIST[INT64]",
        goal_class="airl:goal:collection-transform",
        goal_ontology_ref="airl:intent:map-transform",
        difficulty=3,
        input_types=["LIST[INT64]"],
        output_type="LIST[INT64]",
        effects=[],
        tags=["collection", "map", "pure"],
    ),

    ProgramTemplate(
        name="file_read_emit",
        description="Read bytes from a file, convert to UNICODE, emit to stdout",
        goal_class="airl:goal:io-transform",
        goal_ontology_ref="airl:intent:file-to-stdout",
        difficulty=3,
        input_types=["UNICODE"],
        output_type="UNIT",
        effects=[EffectType.IO_FILE_READ, EffectType.IO_STDOUT],
        tags=["io", "file", "pipeline"],
    ),

    ProgramTemplate(
        name="float_math_pipeline",
        description="Compute sqrt of a param, round to INT64, emit",
        goal_class="airl:goal:compute",
        goal_ontology_ref="airl:intent:float-math-pipeline",
        difficulty=3,
        input_types=["FLOAT64"],
        output_type="UNIT",
        effects=[EffectType.IO_STDOUT],
        tags=["float", "math", "pipeline", "io"],
    ),

    ProgramTemplate(
        name="safe_parse_pipeline",
        description="Parse a UNICODE param to INT64, handle error with UNION, emit result",
        goal_class="airl:goal:error-handling",
        goal_ontology_ref="airl:intent:safe-parse",
        difficulty=3,
        input_types=["UNICODE"],
        output_type="UNIT",
        effects=[EffectType.IO_STDOUT],
        tags=["error-handling", "parse", "union"],
    ),

    # ── Difficulty 4: Complex ─────────────────────────────────────────────

    ProgramTemplate(
        name="reduce_sum",
        description="Reduce a LIST[INT64] to its sum via FIXPOINT recursion",
        goal_class="airl:goal:collection-reduce",
        goal_ontology_ref="airl:intent:reduce-sum",
        difficulty=4,
        input_types=["LIST[INT64]"],
        output_type="INT64",
        effects=[],
        tags=["collection", "reduce", "fixpoint", "pure"],
    ),

    ProgramTemplate(
        name="map_aggregate",
        description="Aggregate a MAP[UNICODE,FLOAT64] by summing values",
        goal_class="airl:goal:collection-transform",
        goal_ontology_ref="airl:goal:data-transformation",
        difficulty=4,
        input_types=["MAP[UNICODE,FLOAT64]"],
        output_type="FLOAT64",
        effects=[],
        tags=["collection", "map", "aggregate", "pure"],
    ),

    ProgramTemplate(
        name="net_fetch_parse_emit",
        description="Receive bytes from network, parse as UNICODE, emit to stdout",
        goal_class="airl:goal:io-transform",
        goal_ontology_ref="airl:intent:net-to-stdout",
        difficulty=4,
        input_types=[],
        output_type="UNIT",
        effects=[EffectType.IO_NET_RECV, EffectType.IO_STDOUT],
        tags=["io", "network", "pipeline"],
    ),

    ProgramTemplate(
        name="crypto_sign_file",
        description="Read file bytes, compute hash, sign, write signature to file",
        goal_class="airl:goal:crypto",
        goal_ontology_ref="airl:intent:sign-file",
        difficulty=4,
        input_types=["UNICODE", "UNICODE"],
        output_type="UNIT",
        effects=[EffectType.IO_FILE_READ, EffectType.IO_FILE_WRITE, EffectType.CRYPTO_SIGN],
        tags=["crypto", "io", "file"],
    ),

    ProgramTemplate(
        name="ai_query_pipeline",
        description="Compose a UNICODE prompt, query an AI, emit response to stdout",
        goal_class="airl:goal:ai-interaction",
        goal_ontology_ref="airl:intent:ai-query-emit",
        difficulty=4,
        input_types=["UNICODE"],
        output_type="UNIT",
        effects=[EffectType.AI_QUERY, EffectType.IO_STDOUT],
        tags=["ai", "io", "pipeline"],
    ),

    ProgramTemplate(
        name="timed_random_emit",
        description="Get current clock, generate seeded random INT64, emit to stdout",
        goal_class="airl:goal:io-emit",
        goal_ontology_ref="airl:intent:timed-random-emit",
        difficulty=4,
        input_types=[],
        output_type="UNIT",
        effects=[EffectType.IO_CLOCK_READ, EffectType.IO_RANDOM_READ, EffectType.IO_STDOUT],
        tags=["time", "random", "io"],
    ),
]

# Quick lookup helpers
TEMPLATES_BY_DIFFICULTY: dict[int, list[ProgramTemplate]] = {}
for _t in TEMPLATES:
    TEMPLATES_BY_DIFFICULTY.setdefault(_t.difficulty, []).append(_t)

TEMPLATES_BY_NAME: dict[str, ProgramTemplate] = {t.name: t for t in TEMPLATES}
TEMPLATES_BY_TAG: dict[str, list[ProgramTemplate]] = {}
for _t in TEMPLATES:
    for _tag in _t.tags:
        TEMPLATES_BY_TAG.setdefault(_tag, []).append(_t)
