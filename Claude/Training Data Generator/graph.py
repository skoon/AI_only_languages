"""
AIRL Graph Nodes and Edges
All node types that can appear in an AIRL computation graph.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from .types import AIRLType, EffectType


class NodeKind(str, Enum):
    LITERAL    = "LITERAL"
    EXEC       = "EXEC"
    COND       = "COND"
    MAP        = "MAP"
    REDUCE     = "REDUCE"
    FILTER     = "FILTER"
    FIXPOINT   = "FIXPOINT"
    IMPORT     = "IMPORT"
    PARAM      = "PARAM"


class EdgeKind(str, Enum):
    DATA      = "DATA"
    CONTROL   = "CONTROL"
    PREDICATE = "PREDICATE"


class Op(str, Enum):
    # IO
    STROUT    = "STROUT"
    STRIN     = "STRIN"
    FILEREAD  = "FILEREAD"
    FILEWRITE = "FILEWRITE"
    NETRECV   = "NETRECV"
    NETSEND   = "NETSEND"
    # Arithmetic
    ADD       = "ADD"
    SUB       = "SUB"
    MUL       = "MUL"
    DIV       = "DIV"
    MOD       = "MOD"
    NEG       = "NEG"
    ABS       = "ABS"
    # Comparison
    EQ        = "EQ"
    NEQ       = "NEQ"
    LT        = "LT"
    LTE       = "LTE"
    GT        = "GT"
    GTE       = "GTE"
    # Logic
    AND       = "AND"
    OR        = "OR"
    NOT       = "NOT"
    # String
    CONCAT    = "CONCAT"
    STRLEN    = "STRLEN"
    SUBSTR    = "SUBSTR"
    STRPARSE  = "STRPARSE"
    INTTOSTR  = "INTTOSTR"
    FLOATTOSTR = "FLOATTOSTR"
    # Collection
    LISTLEN   = "LISTLEN"
    LISTGET   = "LISTGET"
    LISTAPPEND = "LISTAPPEND"
    MAPGET    = "MAPGET"
    MAPSET    = "MAPSET"
    MAPKEYS   = "MAPKEYS"
    MAPVALS   = "MAPVALS"
    # Math
    SQRT      = "SQRT"
    POW       = "POW"
    FLOOR     = "FLOOR"
    CEIL      = "CEIL"
    ROUND     = "ROUND"
    # Type coercion (explicit, never implicit)
    INT_TO_FLOAT = "INT_TO_FLOAT"
    FLOAT_TO_INT = "FLOAT_TO_INT"
    # Error
    RAISE_ERR    = "RAISE_ERR"
    UNWRAP_OK    = "UNWRAP_OK"
    UNWRAP_ERR   = "UNWRAP_ERR"
    # Crypto / AI
    CRYPTO_HASH  = "CRYPTO_HASH"
    AI_CALL      = "AI_CALL"
    # Time
    CLOCK_NOW    = "CLOCK_NOW"
    # Random
    RAND_INT     = "RAND_INT"
    RAND_FLOAT   = "RAND_FLOAT"


# Op → (input_types, output_type, effects)
# None in input_types means "any single type" (polymorphic slot)
OP_SIGNATURES: dict[Op, tuple[list, str, list[EffectType]]] = {
    Op.STROUT:      (["UNICODE"],         "UNIT",    [EffectType.IO_STDOUT]),
    Op.STRIN:       ([],                  "UNICODE", [EffectType.IO_STDIN]),
    Op.FILEREAD:    (["UNICODE"],         "BYTES",   [EffectType.IO_FILE_READ]),
    Op.FILEWRITE:   (["UNICODE","BYTES"], "UNIT",    [EffectType.IO_FILE_WRITE]),
    Op.NETRECV:     ([],                  "BYTES",   [EffectType.IO_NET_RECV]),
    Op.NETSEND:     (["BYTES"],           "UNIT",    [EffectType.IO_NET_SEND]),
    Op.ADD:         (["INT64","INT64"],   "INT64",   []),
    Op.SUB:         (["INT64","INT64"],   "INT64",   []),
    Op.MUL:         (["INT64","INT64"],   "INT64",   []),
    Op.DIV:         (["INT64","INT64"],   "INT64",   []),
    Op.MOD:         (["INT64","INT64"],   "INT64",   []),
    Op.NEG:         (["INT64"],           "INT64",   []),
    Op.ABS:         (["INT64"],           "INT64",   []),
    Op.EQ:          ([None, None],        "BOOL",    []),
    Op.NEQ:         ([None, None],        "BOOL",    []),
    Op.LT:          (["INT64","INT64"],   "BOOL",    []),
    Op.LTE:         (["INT64","INT64"],   "BOOL",    []),
    Op.GT:          (["INT64","INT64"],   "BOOL",    []),
    Op.GTE:         (["INT64","INT64"],   "BOOL",    []),
    Op.AND:         (["BOOL","BOOL"],     "BOOL",    []),
    Op.OR:          (["BOOL","BOOL"],     "BOOL",    []),
    Op.NOT:         (["BOOL"],            "BOOL",    []),
    Op.CONCAT:      (["UNICODE","UNICODE"], "UNICODE", []),
    Op.STRLEN:      (["UNICODE"],         "INT64",   []),
    Op.SUBSTR:      (["UNICODE","INT64","INT64"], "UNICODE", []),
    Op.STRPARSE:    (["UNICODE"],         "INT64",   []),
    Op.INTTOSTR:    (["INT64"],           "UNICODE", []),
    Op.FLOATTOSTR:  (["FLOAT64"],         "UNICODE", []),
    Op.LISTLEN:     ([None],              "INT64",   []),
    Op.LISTGET:     ([None,"INT64"],      None,      []),
    Op.LISTAPPEND:  ([None, None],        None,      []),
    Op.MAPGET:      ([None, None],        None,      []),
    Op.MAPSET:      ([None, None, None],  None,      []),
    Op.MAPKEYS:     ([None],              None,      []),
    Op.MAPVALS:     ([None],              None,      []),
    Op.SQRT:        (["FLOAT64"],         "FLOAT64", []),
    Op.POW:         (["FLOAT64","FLOAT64"], "FLOAT64", []),
    Op.FLOOR:       (["FLOAT64"],         "INT64",   []),
    Op.CEIL:        (["FLOAT64"],         "INT64",   []),
    Op.ROUND:       (["FLOAT64"],         "INT64",   []),
    Op.INT_TO_FLOAT:(["INT64"],           "FLOAT64", []),
    Op.FLOAT_TO_INT:(["FLOAT64"],         "INT64",   []),
    Op.RAISE_ERR:   (["UNICODE"],         None,      []),
    Op.UNWRAP_OK:   ([None],              None,      []),
    Op.UNWRAP_ERR:  ([None],              "UNICODE", []),
    Op.CRYPTO_HASH: (["BYTES"],           "BYTES",   []),
    Op.AI_CALL:     (["UNICODE"],         "UNICODE", [EffectType.AI_QUERY]),
    Op.CLOCK_NOW:   ([],                  "INT64",   [EffectType.IO_CLOCK_READ]),
    Op.RAND_INT:    (["INT64","INT64"],   "INT64",   [EffectType.IO_RANDOM_READ]),
    Op.RAND_FLOAT:  ([],                  "FLOAT64", [EffectType.IO_RANDOM_READ]),
}


@dataclass
class Node:
    node_id: str
    kind: NodeKind
    value_type: AIRLType
    confidence: float = 1.0
    # LITERAL fields
    literal_value: Optional[object] = None
    # EXEC fields
    op: Optional[Op] = None
    effects: list[EffectType] = field(default_factory=list)
    # COND fields
    predicate_ids: list[str] = field(default_factory=list)
    branch_true: Optional[str] = None
    branch_false: Optional[str] = None
    # MAP/REDUCE/FILTER fields
    fn_node_id: Optional[str] = None
    # PARAM fields
    param_index: Optional[int] = None
    param_name: Optional[str] = None
    # IMPORT fields
    module_hash: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {
            "id": self.node_id,
            "@type": self.kind.value,
            "valueType": self.value_type.to_str(),
            "confidence": round(self.confidence, 4),
        }
        if self.kind == NodeKind.LITERAL:
            d["data"] = self.literal_value
        elif self.kind == NodeKind.EXEC:
            d["op"] = self.op.value if self.op else None
            d["effects"] = [e.value for e in self.effects]
        elif self.kind == NodeKind.COND:
            d["predicates"] = self.predicate_ids
            d["branchTrue"]  = self.branch_true
            d["branchFalse"] = self.branch_false
        elif self.kind in (NodeKind.MAP, NodeKind.REDUCE, NodeKind.FILTER):
            d["fnNode"] = self.fn_node_id
        elif self.kind == NodeKind.PARAM:
            d["paramIndex"] = self.param_index
            d["paramName"]  = self.param_name
        elif self.kind == NodeKind.IMPORT:
            d["moduleHash"] = self.module_hash
        return d


@dataclass
class Edge:
    from_id: str
    to_id: str
    kind: EdgeKind = EdgeKind.DATA
    slot: Optional[int] = None    # which input slot on the target node

    def to_dict(self) -> dict:
        d = {"from": self.from_id, "to": self.to_id, "type": self.kind.value}
        if self.slot is not None:
            d["slot"] = self.slot
        return d


@dataclass
class ComputationGraph:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    entry_id: Optional[str] = None
    declared_effects: list[EffectType] = field(default_factory=list)

    def add_node(self, node: Node) -> Node:
        self.nodes.append(node)
        return node

    def add_edge(self, edge: Edge) -> Edge:
        self.edges.append(edge)
        return edge

    def node_by_id(self, nid: str) -> Optional[Node]:
        return next((n for n in self.nodes if n.node_id == nid), None)

    def collect_effects(self) -> list[EffectType]:
        seen: set[EffectType] = set()
        result: list[EffectType] = []
        for node in self.nodes:
            for e in node.effects:
                if e not in seen:
                    seen.add(e)
                    result.append(e)
        return result

    def to_dict(self) -> dict:
        return {
            "@type": "COMPUTATION_GRAPH",
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "entry": self.entry_id,
            "declaredEffects": [e.value for e in self.collect_effects()],
        }
