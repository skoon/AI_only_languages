"""
AIRL Type System
Defines all primitive and composite types in the AIRL spec.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PrimitiveType(str, Enum):
    INT64   = "INT64"
    FLOAT64 = "FLOAT64"
    BOOL    = "BOOL"
    BYTES   = "BYTES"
    UNICODE = "UNICODE"
    UNIT    = "UNIT"


class EffectType(str, Enum):
    IO_STDIN        = "IO_STDIN"
    IO_STDOUT       = "IO_STDOUT"
    IO_STDERR       = "IO_STDERR"
    IO_FILE_READ    = "IO_FILE_READ"
    IO_FILE_WRITE   = "IO_FILE_WRITE"
    IO_FILE_APPEND  = "IO_FILE_APPEND"
    IO_NET_CONNECT  = "IO_NET_CONNECT"
    IO_NET_LISTEN   = "IO_NET_LISTEN"
    IO_NET_SEND     = "IO_NET_SEND"
    IO_NET_RECV     = "IO_NET_RECV"
    IO_CLOCK_READ   = "IO_CLOCK_READ"
    IO_RANDOM_READ  = "IO_RANDOM_READ"
    PROC_SPAWN      = "PROC_SPAWN"
    CRYPTO_SIGN     = "CRYPTO_SIGN"
    CRYPTO_VERIFY   = "CRYPTO_VERIFY"
    AI_EMIT         = "AI_EMIT"
    AI_QUERY        = "AI_QUERY"


@dataclass(frozen=True)
class AIRLType:
    """Base for all AIRL types."""
    def to_dict(self) -> dict:
        raise NotImplementedError

    def to_str(self) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class Primitive(AIRLType):
    kind: PrimitiveType

    def to_dict(self) -> dict:
        return {"kind": "primitive", "type": self.kind.value}

    def to_str(self) -> str:
        return self.kind.value


@dataclass(frozen=True)
class ListType(AIRLType):
    element: AIRLType

    def to_dict(self) -> dict:
        return {"kind": "LIST", "element": self.element.to_dict()}

    def to_str(self) -> str:
        return f"LIST[{self.element.to_str()}]"


@dataclass(frozen=True)
class MapType(AIRLType):
    key: AIRLType
    value: AIRLType

    def to_dict(self) -> dict:
        return {"kind": "MAP", "key": self.key.to_dict(), "value": self.value.to_dict()}

    def to_str(self) -> str:
        return f"MAP[{self.key.to_str()},{self.value.to_str()}]"


@dataclass(frozen=True)
class OptionType(AIRLType):
    inner: AIRLType

    def to_dict(self) -> dict:
        return {"kind": "OPTION", "inner": self.inner.to_dict()}

    def to_str(self) -> str:
        return f"OPTION[{self.inner.to_str()}]"


@dataclass(frozen=True)
class UnionType(AIRLType):
    variants: tuple[AIRLType, ...]

    def to_dict(self) -> dict:
        return {"kind": "UNION", "variants": [v.to_dict() for v in self.variants]}

    def to_str(self) -> str:
        return f"UNION[{','.join(v.to_str() for v in self.variants)}]"


@dataclass(frozen=True)
class TupleType(AIRLType):
    elements: tuple[AIRLType, ...]

    def to_dict(self) -> dict:
        return {"kind": "TUPLE", "elements": [e.to_dict() for e in self.elements]}

    def to_str(self) -> str:
        return f"TUPLE[{','.join(e.to_str() for e in self.elements)}]"


@dataclass(frozen=True)
class FuncType(AIRLType):
    inputs: tuple[AIRLType, ...]
    output: AIRLType
    effects: tuple[EffectType, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "kind": "FUNC",
            "inputs": [i.to_dict() for i in self.inputs],
            "output": self.output.to_dict(),
            "effects": [e.value for e in self.effects],
        }

    def to_str(self) -> str:
        fx = f", EFFECTS: [{','.join(e.value for e in self.effects)}]" if self.effects else ""
        ins = ",".join(i.to_str() for i in self.inputs)
        return f"FUNC[IN: {ins}, OUT: {self.output.to_str()}{fx}]"


# ── Commonly reused type singletons ──────────────────────────────────────────

T_INT    = Primitive(PrimitiveType.INT64)
T_FLOAT  = Primitive(PrimitiveType.FLOAT64)
T_BOOL   = Primitive(PrimitiveType.BOOL)
T_BYTES  = Primitive(PrimitiveType.BYTES)
T_UNICODE = Primitive(PrimitiveType.UNICODE)
T_UNIT   = Primitive(PrimitiveType.UNIT)

T_LIST_INT     = ListType(T_INT)
T_LIST_FLOAT   = ListType(T_FLOAT)
T_LIST_UNICODE = ListType(T_UNICODE)
T_MAP_STR_FLOAT = MapType(T_UNICODE, T_FLOAT)
T_MAP_STR_INT   = MapType(T_UNICODE, T_INT)
T_OPTION_INT    = OptionType(T_INT)
T_OPTION_UNICODE = OptionType(T_UNICODE)

ERR_DIV_ZERO    = Primitive(PrimitiveType.UNICODE)   # typed error sentinel
ERR_NOT_FOUND   = Primitive(PrimitiveType.UNICODE)
ERR_PARSE_FAIL  = Primitive(PrimitiveType.UNICODE)

RESULT_INT      = UnionType((T_INT, ERR_DIV_ZERO))
RESULT_UNICODE  = UnionType((T_UNICODE, ERR_NOT_FOUND))
RESULT_FLOAT    = UnionType((T_FLOAT, ERR_PARSE_FAIL))
