"""
AIRL Program Builder
Constructs concrete ComputationGraphs from ProgramTemplates.
Each build_* method returns a (graph, intent_graph) pair.
"""
from __future__ import annotations
import uuid
import random
import hashlib
from datetime import datetime, timezone
from typing import Optional

from .graph import (
    ComputationGraph, Node, Edge,
    NodeKind, EdgeKind, Op,
    OP_SIGNATURES,
)
from .types import (
    EffectType,
    T_INT, T_FLOAT, T_BOOL, T_BYTES, T_UNICODE, T_UNIT,
    T_LIST_INT, T_LIST_FLOAT, T_LIST_UNICODE,
    T_MAP_STR_FLOAT, T_MAP_STR_INT,
    T_OPTION_INT, T_OPTION_UNICODE,
    RESULT_INT, RESULT_UNICODE, RESULT_FLOAT,
    UnionType, ListType, MapType,
)
from .templates import ProgramTemplate


def _uid() -> str:
    return str(uuid.uuid4())


def _confidence(rng: random.Random, base: float = 0.95, spread: float = 0.08) -> float:
    return round(min(1.0, max(0.6, rng.gauss(base, spread))), 4)


class ProgramBuilder:
    """
    Builds AIRL computation graphs for every template.
    All methods accept a random.Random instance for reproducibility.
    """

    def build(
        self,
        template: ProgramTemplate,
        rng: random.Random,
        model_id: str = "claude-sonnet-4-6",
    ) -> tuple[dict, dict, dict]:
        """
        Returns (program_jsonld, intent_graph, sidecar) for the given template.
        """
        program_id = _uid()
        builder_fn = getattr(self, f"_build_{template.name}", None)
        if builder_fn is None:
            raise NotImplementedError(f"No builder for template '{template.name}'")

        graph = builder_fn(rng)
        graph.declared_effects = graph.collect_effects()

        intent = self._build_intent(template, program_id, rng)
        sidecar = self._build_sidecar(graph, template, program_id, model_id, rng)
        program = self._wrap_program(graph, template, program_id)
        return program, intent, sidecar

    # ── Program wrapper ───────────────────────────────────────────────────

    def _wrap_program(
        self,
        graph: ComputationGraph,
        template: ProgramTemplate,
        program_id: str,
    ) -> dict:
        return {
            "@context": "https://airl-spec.org/v1/context.jsonld",
            "@type": "PROGRAM",
            "id": program_id,
            "templateName": template.name,
            "graph": graph.to_dict(),
            "typeSignature": {
                "in": template.input_types,
                "out": template.output_type,
                "effects": [e.value for e in template.effects],
            },
        }

    # ── Intent graph ──────────────────────────────────────────────────────

    def _build_intent(
        self,
        template: ProgramTemplate,
        program_id: str,
        rng: random.Random,
    ) -> dict:
        return {
            "@context": "https://airl-spec.org/v1/intent.jsonld",
            "@type": "INTENT_GRAPH",
            "id": f"intent-{_uid()}",
            "programId": program_id,
            "goal": {
                "ontologyRef": template.goal_ontology_ref,
                "goalClass": template.goal_class,
                "description": template.description,
                "inputs": [{"type": t} for t in template.input_types],
                "outputs": [{"type": template.output_type}],
                "constraints": [
                    {"type": "EFFECT_BUDGET", "allowed": [e.value for e in template.effects]},
                ],
            },
            "decomposition": [
                f"airl:subgoal:{tag}" for tag in template.tags
            ],
            "difficulty": template.difficulty,
            "tags": template.tags,
        }

    # ── Sidecar / provenance ──────────────────────────────────────────────

    def _build_sidecar(
        self,
        graph: ComputationGraph,
        template: ProgramTemplate,
        program_id: str,
        model_id: str,
        rng: random.Random,
    ) -> dict:
        ts = datetime.now(timezone.utc).isoformat()
        node_provenance = []
        for node in graph.nodes:
            node_provenance.append({
                "nodeRef": node.node_id,
                "INTENT": {
                    "ontologyRef": template.goal_ontology_ref,
                    "goalClass": template.goal_class,
                },
                "CONFIDENCE": node.confidence,
                "GENERATED_BY": {
                    "modelId": model_id,
                    "timestamp": ts,
                },
                "DERIVED_FROM": None,
                "REPLACES": None,
                "VERIFIED_BY": [
                    "airl:verifier:type-check",
                    "airl:verifier:effect-declared",
                    "airl:verifier:structural",
                ],
            })
        return {
            "@context": "https://airl-spec.org/v1/provenance.jsonld",
            "@type": "PROVENANCE_GRAPH",
            "subject": program_id,
            "templateName": template.name,
            "nodes": node_provenance,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Template build methods (one per template)
    # ──────────────────────────────────────────────────────────────────────

    def _build_hello_world(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        messages = [
            "Hello, World!",
            "Hello from AIRL!",
            "Greetings from the AI-Ready Language!",
            f"AIRL program #{rng.randint(1000, 9999)}",
            "The future of AI-native code is here.",
        ]
        msg = rng.choice(messages)

        lit = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_UNICODE, literal_value=msg,
            confidence=_confidence(rng),
        ))
        out = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STROUT,
            value_type=T_UNIT, effects=[EffectType.IO_STDOUT],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(lit.node_id, out.node_id, EdgeKind.DATA, slot=0))
        g.entry_id = out.node_id
        return g

    def _build_echo_stdin(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        inp = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STRIN,
            value_type=T_UNICODE, effects=[EffectType.IO_STDIN],
            confidence=_confidence(rng),
        ))
        out = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STROUT,
            value_type=T_UNIT, effects=[EffectType.IO_STDOUT],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(inp.node_id, out.node_id, EdgeKind.DATA, slot=0))
        g.entry_id = out.node_id
        return g

    def _build_constant_arithmetic(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        a = rng.randint(1, 100)
        b = rng.randint(1, 100)
        op_choice = rng.choice([Op.ADD, Op.SUB, Op.MUL])

        lit_a = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_INT, literal_value=a,
            confidence=_confidence(rng),
        ))
        lit_b = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_INT, literal_value=b,
            confidence=_confidence(rng),
        ))
        result = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=op_choice,
            value_type=T_INT, effects=[],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(lit_a.node_id, result.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(lit_b.node_id, result.node_id, EdgeKind.DATA, slot=1))
        g.entry_id = result.node_id
        return g

    def _build_boolean_logic(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        v1 = rng.choice([True, False])
        v2 = rng.choice([True, False])
        op_choice = rng.choice([Op.AND, Op.OR])

        lit_a = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_BOOL, literal_value=v1,
            confidence=_confidence(rng),
        ))
        lit_b = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_BOOL, literal_value=v2,
            confidence=_confidence(rng),
        ))
        result = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=op_choice,
            value_type=T_BOOL, effects=[],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(lit_a.node_id, result.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(lit_b.node_id, result.node_id, EdgeKind.DATA, slot=1))
        g.entry_id = result.node_id
        return g

    def _build_integer_add_params(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        op_choice = rng.choice([Op.ADD, Op.SUB, Op.MUL, Op.MOD])

        p0 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_INT, param_index=0, param_name="a",
            confidence=_confidence(rng),
        ))
        p1 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_INT, param_index=1, param_name="b",
            confidence=_confidence(rng),
        ))
        result = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=op_choice,
            value_type=T_INT, effects=[],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(p0.node_id, result.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(p1.node_id, result.node_id, EdgeKind.DATA, slot=1))
        g.entry_id = result.node_id
        return g

    def _build_string_concat_params(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        p0 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_UNICODE, param_index=0, param_name="left",
            confidence=_confidence(rng),
        ))
        p1 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_UNICODE, param_index=1, param_name="right",
            confidence=_confidence(rng),
        ))
        result = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.CONCAT,
            value_type=T_UNICODE, effects=[],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(p0.node_id, result.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(p1.node_id, result.node_id, EdgeKind.DATA, slot=1))
        g.entry_id = result.node_id
        return g

    def _build_safe_divide(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        result_type = UnionType((T_INT, T_UNICODE))

        p0 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_INT, param_index=0, param_name="numerator",
            confidence=_confidence(rng),
        ))
        p1 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_INT, param_index=1, param_name="denominator",
            confidence=_confidence(rng),
        ))
        zero = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_INT, literal_value=0,
            confidence=_confidence(rng),
        ))
        guard = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.EQ,
            value_type=T_BOOL, effects=[],
            confidence=_confidence(rng),
        ))
        err_msg = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_UNICODE, literal_value="ERR_DIV_ZERO",
            confidence=_confidence(rng),
        ))
        division = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.DIV,
            value_type=T_INT, effects=[],
            confidence=_confidence(rng),
        ))
        cond = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.COND,
            value_type=result_type,
            branch_true=err_msg.node_id,
            branch_false=division.node_id,
            confidence=_confidence(rng),
        ))

        g.add_edge(Edge(p1.node_id, guard.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(zero.node_id, guard.node_id, EdgeKind.DATA, slot=1))
        g.add_edge(Edge(guard.node_id, cond.node_id, EdgeKind.PREDICATE))
        g.add_edge(Edge(p0.node_id, division.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(p1.node_id, division.node_id, EdgeKind.DATA, slot=1))
        g.entry_id = cond.node_id
        return g

    def _build_int_to_string_emit(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        p0 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_INT, param_index=0, param_name="value",
            confidence=_confidence(rng),
        ))
        coerce = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.INTTOSTR,
            value_type=T_UNICODE, effects=[],
            confidence=_confidence(rng),
        ))
        out = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STROUT,
            value_type=T_UNIT, effects=[EffectType.IO_STDOUT],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(p0.node_id, coerce.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(coerce.node_id, out.node_id, EdgeKind.DATA, slot=0))
        g.entry_id = out.node_id
        return g

    def _build_compare_integers(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        op_choice = rng.choice([Op.LT, Op.LTE, Op.GT, Op.GTE, Op.EQ, Op.NEQ])
        p0 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_INT, param_index=0, param_name="x",
            confidence=_confidence(rng),
        ))
        p1 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_INT, param_index=1, param_name="y",
            confidence=_confidence(rng),
        ))
        result = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=op_choice,
            value_type=T_BOOL, effects=[],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(p0.node_id, result.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(p1.node_id, result.node_id, EdgeKind.DATA, slot=1))
        g.entry_id = result.node_id
        return g

    def _build_conditional_emit(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        true_msgs  = ["Condition is true",  "Yes", "Affirmative", "TRUE path taken"]
        false_msgs = ["Condition is false", "No",  "Negative",    "FALSE path taken"]

        p0 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_BOOL, param_index=0, param_name="condition",
            confidence=_confidence(rng),
        ))
        lit_t = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_UNICODE, literal_value=rng.choice(true_msgs),
            confidence=_confidence(rng),
        ))
        lit_f = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_UNICODE, literal_value=rng.choice(false_msgs),
            confidence=_confidence(rng),
        ))
        out_t = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STROUT,
            value_type=T_UNIT, effects=[EffectType.IO_STDOUT],
            confidence=_confidence(rng),
        ))
        out_f = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STROUT,
            value_type=T_UNIT, effects=[EffectType.IO_STDOUT],
            confidence=_confidence(rng),
        ))
        cond = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.COND,
            value_type=T_UNIT,
            branch_true=out_t.node_id,
            branch_false=out_f.node_id,
            confidence=_confidence(rng),
        ))

        g.add_edge(Edge(p0.node_id, cond.node_id, EdgeKind.PREDICATE))
        g.add_edge(Edge(lit_t.node_id, out_t.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(lit_f.node_id, out_f.node_id, EdgeKind.DATA, slot=0))
        g.entry_id = cond.node_id
        return g

    def _build_string_length_pipeline(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        prefix_options = ["Length: ", "String length is ", "len=", "chars: "]
        p0 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_UNICODE, param_index=0, param_name="input",
            confidence=_confidence(rng),
        ))
        strlen = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STRLEN,
            value_type=T_INT, effects=[],
            confidence=_confidence(rng),
        ))
        to_str = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.INTTOSTR,
            value_type=T_UNICODE, effects=[],
            confidence=_confidence(rng),
        ))
        prefix = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_UNICODE, literal_value=rng.choice(prefix_options),
            confidence=_confidence(rng),
        ))
        concat = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.CONCAT,
            value_type=T_UNICODE, effects=[],
            confidence=_confidence(rng),
        ))
        out = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STROUT,
            value_type=T_UNIT, effects=[EffectType.IO_STDOUT],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(p0.node_id, strlen.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(strlen.node_id, to_str.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(prefix.node_id, concat.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(to_str.node_id, concat.node_id, EdgeKind.DATA, slot=1))
        g.add_edge(Edge(concat.node_id, out.node_id, EdgeKind.DATA, slot=0))
        g.entry_id = out.node_id
        return g

    def _build_arithmetic_chain(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        params = []
        for i, name in enumerate(["a", "b", "c", "d"]):
            p = g.add_node(Node(
                node_id=_uid(), kind=NodeKind.PARAM,
                value_type=T_INT, param_index=i, param_name=name,
                confidence=_confidence(rng),
            ))
            params.append(p)

        # (a OP1 b) OP2 (c OP3 d)
        ops = rng.sample([Op.ADD, Op.SUB, Op.MUL], 3)
        left = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=ops[0],
            value_type=T_INT, effects=[],
            confidence=_confidence(rng),
        ))
        right = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=ops[1],
            value_type=T_INT, effects=[],
            confidence=_confidence(rng),
        ))
        combine = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=ops[2],
            value_type=T_INT, effects=[],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(params[0].node_id, left.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(params[1].node_id, left.node_id, EdgeKind.DATA, slot=1))
        g.add_edge(Edge(params[2].node_id, right.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(params[3].node_id, right.node_id, EdgeKind.DATA, slot=1))
        g.add_edge(Edge(left.node_id, combine.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(right.node_id, combine.node_id, EdgeKind.DATA, slot=1))
        g.entry_id = combine.node_id
        return g

    def _build_read_parse_compute(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        modulus = rng.choice([2, 3, 5, 7, 10, 100])

        inp = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STRIN,
            value_type=T_UNICODE, effects=[EffectType.IO_STDIN],
            confidence=_confidence(rng),
        ))
        parse = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STRPARSE,
            value_type=T_INT, effects=[],
            confidence=_confidence(rng),
        ))
        mod_lit = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_INT, literal_value=modulus,
            confidence=_confidence(rng),
        ))
        mod_op = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.MOD,
            value_type=T_INT, effects=[],
            confidence=_confidence(rng),
        ))
        to_str = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.INTTOSTR,
            value_type=T_UNICODE, effects=[],
            confidence=_confidence(rng),
        ))
        out = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STROUT,
            value_type=T_UNIT, effects=[EffectType.IO_STDOUT],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(inp.node_id, parse.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(parse.node_id, mod_op.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(mod_lit.node_id, mod_op.node_id, EdgeKind.DATA, slot=1))
        g.add_edge(Edge(mod_op.node_id, to_str.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(to_str.node_id, out.node_id, EdgeKind.DATA, slot=0))
        g.entry_id = out.node_id
        return g

    def _build_map_transform(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        op_choice = rng.choice([Op.ABS, Op.NEG])
        scalar = rng.randint(2, 10)

        p0 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_LIST_INT, param_index=0, param_name="items",
            confidence=_confidence(rng),
        ))
        fn = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=op_choice,
            value_type=T_INT, effects=[],
            confidence=_confidence(rng),
        ))
        result = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.MAP,
            value_type=T_LIST_INT, fn_node_id=fn.node_id,
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(p0.node_id, result.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(fn.node_id, result.node_id, EdgeKind.CONTROL))
        g.entry_id = result.node_id
        return g

    def _build_file_read_emit(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        p0 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_UNICODE, param_index=0, param_name="filepath",
            confidence=_confidence(rng),
        ))
        read = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.FILEREAD,
            value_type=T_BYTES, effects=[EffectType.IO_FILE_READ],
            confidence=_confidence(rng),
        ))
        # BYTES → UNICODE via STRPARSE (simplified; real spec would use DECODE)
        decode = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STRPARSE,
            value_type=T_UNICODE, effects=[],
            confidence=_confidence(rng),
        ))
        out = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STROUT,
            value_type=T_UNIT, effects=[EffectType.IO_STDOUT],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(p0.node_id, read.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(read.node_id, decode.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(decode.node_id, out.node_id, EdgeKind.DATA, slot=0))
        g.entry_id = out.node_id
        return g

    def _build_float_math_pipeline(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        prefix_opts = ["sqrt=", "Result: ", "√x = "]
        p0 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_FLOAT, param_index=0, param_name="x",
            confidence=_confidence(rng),
        ))
        sqrt = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.SQRT,
            value_type=T_FLOAT, effects=[],
            confidence=_confidence(rng),
        ))
        rounded = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.ROUND,
            value_type=T_INT, effects=[],
            confidence=_confidence(rng),
        ))
        to_str = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.INTTOSTR,
            value_type=T_UNICODE, effects=[],
            confidence=_confidence(rng),
        ))
        prefix = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_UNICODE, literal_value=rng.choice(prefix_opts),
            confidence=_confidence(rng),
        ))
        concat = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.CONCAT,
            value_type=T_UNICODE, effects=[],
            confidence=_confidence(rng),
        ))
        out = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STROUT,
            value_type=T_UNIT, effects=[EffectType.IO_STDOUT],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(p0.node_id, sqrt.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(sqrt.node_id, rounded.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(rounded.node_id, to_str.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(prefix.node_id, concat.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(to_str.node_id, concat.node_id, EdgeKind.DATA, slot=1))
        g.add_edge(Edge(concat.node_id, out.node_id, EdgeKind.DATA, slot=0))
        g.entry_id = out.node_id
        return g

    def _build_safe_parse_pipeline(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        ok_prefix = rng.choice(["Parsed: ", "Value: ", "Result: "])
        err_prefix = rng.choice(["Parse failed: ", "Error: ", "Invalid: "])

        p0 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_UNICODE, param_index=0, param_name="raw_input",
            confidence=_confidence(rng),
        ))
        parse = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STRPARSE,
            value_type=T_INT, effects=[],
            confidence=_confidence(rng, base=0.88),
        ))
        ok_str = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.INTTOSTR,
            value_type=T_UNICODE, effects=[],
            confidence=_confidence(rng),
        ))
        ok_pfx = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_UNICODE, literal_value=ok_prefix,
            confidence=_confidence(rng),
        ))
        ok_msg = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.CONCAT,
            value_type=T_UNICODE, effects=[],
            confidence=_confidence(rng),
        ))
        err_pfx = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_UNICODE, literal_value=err_prefix,
            confidence=_confidence(rng),
        ))
        err_msg = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.CONCAT,
            value_type=T_UNICODE, effects=[],
            confidence=_confidence(rng),
        ))
        zero = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_INT, literal_value=0,
            confidence=_confidence(rng),
        ))
        guard = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.LT,
            value_type=T_BOOL, effects=[],
            confidence=_confidence(rng),
        ))
        cond = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.COND,
            value_type=T_UNICODE,
            branch_true=err_msg.node_id,
            branch_false=ok_msg.node_id,
            confidence=_confidence(rng),
        ))
        out = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STROUT,
            value_type=T_UNIT, effects=[EffectType.IO_STDOUT],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(p0.node_id, parse.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(parse.node_id, ok_str.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(ok_pfx.node_id, ok_msg.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(ok_str.node_id, ok_msg.node_id, EdgeKind.DATA, slot=1))
        g.add_edge(Edge(err_pfx.node_id, err_msg.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(p0.node_id, err_msg.node_id, EdgeKind.DATA, slot=1))
        g.add_edge(Edge(parse.node_id, guard.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(zero.node_id, guard.node_id, EdgeKind.DATA, slot=1))
        g.add_edge(Edge(guard.node_id, cond.node_id, EdgeKind.PREDICATE))
        g.add_edge(Edge(cond.node_id, out.node_id, EdgeKind.DATA, slot=0))
        g.entry_id = out.node_id
        return g

    def _build_reduce_sum(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        p0 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_LIST_INT, param_index=0, param_name="numbers",
            confidence=_confidence(rng),
        ))
        zero = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_INT, literal_value=0,
            confidence=_confidence(rng),
        ))
        add_fn = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.ADD,
            value_type=T_INT, effects=[],
            confidence=_confidence(rng),
        ))
        reduce = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.REDUCE,
            value_type=T_INT, fn_node_id=add_fn.node_id,
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(p0.node_id, reduce.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(zero.node_id, reduce.node_id, EdgeKind.DATA, slot=1))
        g.add_edge(Edge(add_fn.node_id, reduce.node_id, EdgeKind.CONTROL))
        g.entry_id = reduce.node_id
        return g

    def _build_map_aggregate(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        p0 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_MAP_STR_FLOAT, param_index=0, param_name="data",
            confidence=_confidence(rng),
        ))
        vals = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.MAPVALS,
            value_type=T_LIST_FLOAT, effects=[],
            confidence=_confidence(rng),
        ))
        zero = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_FLOAT, literal_value=0.0,
            confidence=_confidence(rng),
        ))
        add_fn = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.ADD,
            value_type=T_FLOAT, effects=[],
            confidence=_confidence(rng),
        ))
        reduce = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.REDUCE,
            value_type=T_FLOAT, fn_node_id=add_fn.node_id,
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(p0.node_id, vals.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(vals.node_id, reduce.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(zero.node_id, reduce.node_id, EdgeKind.DATA, slot=1))
        g.add_edge(Edge(add_fn.node_id, reduce.node_id, EdgeKind.CONTROL))
        g.entry_id = reduce.node_id
        return g

    def _build_net_fetch_parse_emit(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        recv = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.NETRECV,
            value_type=T_BYTES, effects=[EffectType.IO_NET_RECV],
            confidence=_confidence(rng),
        ))
        decode = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STRPARSE,
            value_type=T_UNICODE, effects=[],
            confidence=_confidence(rng, base=0.89),
        ))
        out = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STROUT,
            value_type=T_UNIT, effects=[EffectType.IO_STDOUT],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(recv.node_id, decode.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(decode.node_id, out.node_id, EdgeKind.DATA, slot=0))
        g.entry_id = out.node_id
        return g

    def _build_crypto_sign_file(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        p_in = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_UNICODE, param_index=0, param_name="input_path",
            confidence=_confidence(rng),
        ))
        p_out = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_UNICODE, param_index=1, param_name="sig_path",
            confidence=_confidence(rng),
        ))
        read = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.FILEREAD,
            value_type=T_BYTES, effects=[EffectType.IO_FILE_READ],
            confidence=_confidence(rng),
        ))
        hash_n = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.CRYPTO_HASH,
            value_type=T_BYTES, effects=[],
            confidence=_confidence(rng),
        ))
        write = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.FILEWRITE,
            value_type=T_UNIT, effects=[EffectType.IO_FILE_WRITE],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(p_in.node_id, read.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(read.node_id, hash_n.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(p_out.node_id, write.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(hash_n.node_id, write.node_id, EdgeKind.DATA, slot=1))
        g.entry_id = write.node_id
        return g

    def _build_ai_query_pipeline(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        prefixes = ["Explain: ", "Summarize: ", "Translate: ", "Analyze: "]
        p0 = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.PARAM,
            value_type=T_UNICODE, param_index=0, param_name="topic",
            confidence=_confidence(rng),
        ))
        prefix = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_UNICODE, literal_value=rng.choice(prefixes),
            confidence=_confidence(rng),
        ))
        prompt = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.CONCAT,
            value_type=T_UNICODE, effects=[],
            confidence=_confidence(rng),
        ))
        query = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.AI_CALL,
            value_type=T_UNICODE, effects=[EffectType.AI_QUERY],
            confidence=_confidence(rng, base=0.91),
        ))
        out = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STROUT,
            value_type=T_UNIT, effects=[EffectType.IO_STDOUT],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(prefix.node_id, prompt.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(p0.node_id, prompt.node_id, EdgeKind.DATA, slot=1))
        g.add_edge(Edge(prompt.node_id, query.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(query.node_id, out.node_id, EdgeKind.DATA, slot=0))
        g.entry_id = out.node_id
        return g

    def _build_timed_random_emit(self, rng: random.Random) -> ComputationGraph:
        g = ComputationGraph()
        clock = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.CLOCK_NOW,
            value_type=T_INT, effects=[EffectType.IO_CLOCK_READ],
            confidence=_confidence(rng),
        ))
        lo = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_INT, literal_value=rng.randint(0, 100),
            confidence=_confidence(rng),
        ))
        hi = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_INT, literal_value=rng.randint(1000, 9999),
            confidence=_confidence(rng),
        ))
        rand = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.RAND_INT,
            value_type=T_INT, effects=[EffectType.IO_RANDOM_READ],
            confidence=_confidence(rng),
        ))
        to_str = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.INTTOSTR,
            value_type=T_UNICODE, effects=[],
            confidence=_confidence(rng),
        ))
        prefix = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.LITERAL,
            value_type=T_UNICODE,
            literal_value=rng.choice(["Random: ", "rand=", "Value: "]),
            confidence=_confidence(rng),
        ))
        concat = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.CONCAT,
            value_type=T_UNICODE, effects=[],
            confidence=_confidence(rng),
        ))
        out = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.STROUT,
            value_type=T_UNIT, effects=[EffectType.IO_STDOUT],
            confidence=_confidence(rng),
        ))
        # clock feeds into rand as "seed influence" via ADD to lo
        seed_add = g.add_node(Node(
            node_id=_uid(), kind=NodeKind.EXEC, op=Op.MOD,
            value_type=T_INT, effects=[],
            confidence=_confidence(rng),
        ))
        g.add_edge(Edge(clock.node_id, seed_add.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(hi.node_id, seed_add.node_id, EdgeKind.DATA, slot=1))
        g.add_edge(Edge(seed_add.node_id, rand.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(hi.node_id, rand.node_id, EdgeKind.DATA, slot=1))
        g.add_edge(Edge(rand.node_id, to_str.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(prefix.node_id, concat.node_id, EdgeKind.DATA, slot=0))
        g.add_edge(Edge(to_str.node_id, concat.node_id, EdgeKind.DATA, slot=1))
        g.add_edge(Edge(concat.node_id, out.node_id, EdgeKind.DATA, slot=0))
        g.entry_id = out.node_id
        return g
