"""
AIRL Mutation Engine
Produces deliberately invalid AIRL programs for negative training examples.
Each mutation introduces a specific, labelled error into a valid graph.
"""
from __future__ import annotations
import copy
import json
import random
from enum import Enum
from typing import Optional


class MutationType(str, Enum):
    MISSING_EFFECT_DECLARATION = "MISSING_EFFECT_DECLARATION"
    TYPE_MISMATCH              = "TYPE_MISMATCH"
    DANGLING_EDGE_REFERENCE    = "DANGLING_EDGE_REFERENCE"
    MISSING_ENTRY_POINT        = "MISSING_ENTRY_POINT"
    NULL_LITERAL_VALUE         = "NULL_LITERAL_VALUE"
    WRONG_OP_FOR_TYPE          = "WRONG_OP_FOR_TYPE"
    DEAD_NODE_ADDED            = "DEAD_NODE_ADDED"
    DUPLICATE_NODE_ID          = "DUPLICATE_NODE_ID"
    LOW_CONFIDENCE_NODE        = "LOW_CONFIDENCE_NODE"
    INVALID_CONFIDENCE_RANGE   = "INVALID_CONFIDENCE_RANGE"


def _deep_copy_program(program: dict) -> dict:
    return json.loads(json.dumps(program))


def mutate(
    program: dict,
    mutation_type: MutationType,
    rng: random.Random,
) -> tuple[dict, str]:
    """
    Apply a single mutation to a program dict.
    Returns (mutated_program, description_of_mutation).
    """
    mutated = _deep_copy_program(program)
    nodes = mutated.get("graph", {}).get("nodes", [])

    if mutation_type == MutationType.MISSING_EFFECT_DECLARATION:
        return _mutate_missing_effect(mutated, nodes, rng)

    elif mutation_type == MutationType.TYPE_MISMATCH:
        return _mutate_type_mismatch(mutated, nodes, rng)

    elif mutation_type == MutationType.DANGLING_EDGE_REFERENCE:
        return _mutate_dangling_edge(mutated, rng)

    elif mutation_type == MutationType.MISSING_ENTRY_POINT:
        return _mutate_missing_entry(mutated)

    elif mutation_type == MutationType.NULL_LITERAL_VALUE:
        return _mutate_null_literal(mutated, nodes, rng)

    elif mutation_type == MutationType.WRONG_OP_FOR_TYPE:
        return _mutate_wrong_op(mutated, nodes, rng)

    elif mutation_type == MutationType.DEAD_NODE_ADDED:
        return _mutate_dead_node(mutated, rng)

    elif mutation_type == MutationType.DUPLICATE_NODE_ID:
        return _mutate_duplicate_id(mutated, nodes, rng)

    elif mutation_type == MutationType.LOW_CONFIDENCE_NODE:
        return _mutate_low_confidence(mutated, nodes, rng)

    elif mutation_type == MutationType.INVALID_CONFIDENCE_RANGE:
        return _mutate_invalid_confidence(mutated, nodes, rng)

    return mutated, "no-op"


def _mutate_missing_effect(mutated, nodes, rng):
    exec_nodes = [n for n in nodes if n.get("@type") == "EXEC" and n.get("effects")]
    if not exec_nodes:
        return mutated, "no-exec-nodes-to-mutate"
    target = rng.choice(exec_nodes)
    removed = target["effects"].pop(0)
    return mutated, f"Removed effect '{removed}' from node '{target['id']}'"


def _mutate_type_mismatch(mutated, nodes, rng):
    type_swaps = {
        "INT64":   "FLOAT64",
        "FLOAT64": "BOOL",
        "BOOL":    "UNICODE",
        "UNICODE": "INT64",
        "UNIT":    "BYTES",
    }
    if not nodes:
        return mutated, "no-nodes"
    target = rng.choice(nodes)
    original = target.get("valueType", "INT64")
    swapped = type_swaps.get(original, "BOOL")
    target["valueType"] = swapped
    return mutated, f"Changed node '{target['id']}' type from '{original}' to '{swapped}'"


def _mutate_dangling_edge(mutated, rng):
    edges = mutated.get("graph", {}).get("edges", [])
    if not edges:
        return mutated, "no-edges"
    target = rng.choice(edges)
    bad_id = "deadbeef-0000-0000-0000-000000000000"
    original_from = target["from"]
    target["from"] = bad_id
    return mutated, f"Edge from '{original_from}' changed to non-existent node '{bad_id}'"


def _mutate_missing_entry(mutated):
    original = mutated.get("graph", {}).get("entry")
    mutated["graph"]["entry"] = None
    return mutated, f"Removed entry point (was '{original}')"


def _mutate_null_literal(mutated, nodes, rng):
    literals = [n for n in nodes if n.get("@type") == "LITERAL"]
    if not literals:
        return mutated, "no-literals"
    target = rng.choice(literals)
    original = target.get("data")
    target["data"] = None
    return mutated, f"Set LITERAL node '{target['id']}' data to null (was '{original}')"


def _mutate_wrong_op(mutated, nodes, rng):
    # Replace an arithmetic op with an IO op that has the wrong signature
    op_mismatches = {
        "ADD":    "STROUT",
        "SUB":    "FILEREAD",
        "CONCAT": "ADD",
        "STRLEN": "NETSEND",
        "SQRT":   "STRIN",
    }
    exec_nodes = [n for n in nodes if n.get("@type") == "EXEC" and n.get("op") in op_mismatches]
    if not exec_nodes:
        return mutated, "no-mutatable-exec-nodes"
    target = rng.choice(exec_nodes)
    original_op = target["op"]
    target["op"] = op_mismatches[original_op]
    return mutated, f"Replaced op '{original_op}' with mismatched '{target['op']}' on node '{target['id']}'"


def _mutate_dead_node(mutated, rng):
    import uuid
    dead_id = str(uuid.uuid4())
    dead_node = {
        "id": dead_id,
        "@type": "LITERAL",
        "valueType": "INT64",
        "data": rng.randint(0, 999),
        "confidence": 0.99,
    }
    mutated["graph"]["nodes"].append(dead_node)
    return mutated, f"Added unreachable dead node '{dead_id}'"


def _mutate_duplicate_id(mutated, nodes, rng):
    if len(nodes) < 2:
        return mutated, "not-enough-nodes"
    n1, n2 = rng.sample(nodes, 2)
    original_id = n2["id"]
    n2["id"] = n1["id"]
    return mutated, f"Duplicated node ID '{n1['id']}' (was '{original_id}')"


def _mutate_low_confidence(mutated, nodes, rng):
    if not nodes:
        return mutated, "no-nodes"
    target = rng.choice(nodes)
    original = target.get("confidence", 1.0)
    target["confidence"] = round(rng.uniform(0.3, 0.74), 4)
    return mutated, (
        f"Set confidence of node '{target['id']}' to {target['confidence']:.4f} "
        f"(was {original:.4f}) — below threshold 0.75"
    )


def _mutate_invalid_confidence(mutated, nodes, rng):
    if not nodes:
        return mutated, "no-nodes"
    target = rng.choice(nodes)
    # Confidence must be in [0.0, 1.0] — put it outside
    bad_value = rng.choice([-0.5, 1.5, 2.0, -1.0])
    target["confidence"] = bad_value
    return mutated, (
        f"Set confidence of node '{target['id']}' to {bad_value} "
        f"(outside valid range [0.0, 1.0])"
    )
