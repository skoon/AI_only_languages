"""
AIRL Verifier
Checks computation graphs for structural and type correctness.
Produces structured verification reports.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from .graph import ComputationGraph, Node, NodeKind, Op, OP_SIGNATURES
from .types import EffectType


class PassStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class Issue:
    severity: PassStatus
    code: str
    message: str
    node_id: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"severity": self.severity.value, "code": self.code, "message": self.message}
        if self.node_id:
            d["nodeId"] = self.node_id
        return d


@dataclass
class PassResult:
    name: str
    status: PassStatus
    issues: list[Issue] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "pass": self.name,
            "status": self.status.value,
            "issues": [i.to_dict() for i in self.issues],
            **self.meta,
        }


@dataclass
class VerificationReport:
    program_id: str
    passes: list[PassResult] = field(default_factory=list)

    @property
    def overall_status(self) -> PassStatus:
        statuses = [p.status for p in self.passes]
        if PassStatus.FAIL in statuses:
            return PassStatus.FAIL
        if PassStatus.WARN in statuses:
            return PassStatus.WARN
        return PassStatus.PASS

    def to_dict(self) -> dict:
        return {
            "@type": "VERIFICATION_REPORT",
            "programId": self.program_id,
            "overallStatus": self.overall_status.value,
            "passes": [p.to_dict() for p in self.passes],
        }


class Verifier:
    """
    Runs all verification passes over a ComputationGraph.
    Passes run in order; later passes may skip if earlier ones fail.
    """

    def verify(self, graph: ComputationGraph, program_id: str) -> VerificationReport:
        report = VerificationReport(program_id=program_id)

        structural = self._pass_structural(graph)
        report.passes.append(structural)

        type_check = self._pass_type_check(graph)
        report.passes.append(type_check)

        effect_audit = self._pass_effect_audit(graph)
        report.passes.append(effect_audit)

        dead_nodes = self._pass_dead_node(graph)
        report.passes.append(dead_nodes)

        entry_check = self._pass_entry_point(graph)
        report.passes.append(entry_check)

        confidence = self._pass_confidence(graph)
        report.passes.append(confidence)

        return report

    # ── Pass: Structural ─────────────────────────────────────────────────────

    def _pass_structural(self, graph: ComputationGraph) -> PassResult:
        issues: list[Issue] = []
        node_ids = {n.node_id for n in graph.nodes}

        # Check all edge endpoints reference real nodes
        for edge in graph.edges:
            if edge.from_id not in node_ids:
                issues.append(Issue(
                    PassStatus.FAIL, "E001",
                    f"Edge references unknown source node '{edge.from_id}'",
                    edge.from_id,
                ))
            if edge.to_id not in node_ids:
                issues.append(Issue(
                    PassStatus.FAIL, "E002",
                    f"Edge references unknown target node '{edge.to_id}'",
                    edge.to_id,
                ))

        # Check for cycles (topological sort)
        cycle_nodes = self._detect_cycles(graph, node_ids)
        for nid in cycle_nodes:
            issues.append(Issue(
                PassStatus.FAIL, "E003",
                f"Cycle detected involving node '{nid}'",
                nid,
            ))

        status = PassStatus.FAIL if any(i.severity == PassStatus.FAIL for i in issues) else PassStatus.PASS
        return PassResult(
            name="structural",
            status=status,
            issues=issues,
            meta={"nodesChecked": len(graph.nodes), "edgesChecked": len(graph.edges)},
        )

    def _detect_cycles(self, graph: ComputationGraph, node_ids: set) -> list[str]:
        """Returns list of node IDs involved in cycles."""
        adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}
        for edge in graph.edges:
            if edge.from_id in adjacency:
                adjacency[edge.from_id].append(edge.to_id)

        visited: set[str] = set()
        in_stack: set[str] = set()
        cycle_nodes: list[str] = []

        def dfs(node: str):
            visited.add(node)
            in_stack.add(node)
            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in in_stack:
                    cycle_nodes.append(neighbor)
            in_stack.discard(node)

        for nid in node_ids:
            if nid not in visited:
                dfs(nid)

        return cycle_nodes

    # ── Pass: Type Check ─────────────────────────────────────────────────────

    def _pass_type_check(self, graph: ComputationGraph) -> PassResult:
        issues: list[Issue] = []
        checked = 0

        for node in graph.nodes:
            checked += 1
            if node.kind == NodeKind.EXEC and node.op:
                sig = OP_SIGNATURES.get(node.op)
                if sig is None:
                    issues.append(Issue(
                        PassStatus.WARN, "T001",
                        f"No signature found for op '{node.op.value}' — cannot type-check",
                        node.node_id,
                    ))
                    continue
                expected_out = sig[1]
                if expected_out and node.value_type.to_str() != expected_out:
                    # Polymorphic ops (None output) are allowed
                    issues.append(Issue(
                        PassStatus.WARN, "T002",
                        f"Node '{node.node_id}' op '{node.op.value}' "
                        f"declared output '{node.value_type.to_str()}' "
                        f"but signature expects '{expected_out}'",
                        node.node_id,
                    ))

            if node.kind == NodeKind.LITERAL and node.literal_value is None:
                issues.append(Issue(
                    PassStatus.WARN, "T003",
                    f"LITERAL node '{node.node_id}' has null value",
                    node.node_id,
                ))

        status = (
            PassStatus.FAIL if any(i.severity == PassStatus.FAIL for i in issues)
            else PassStatus.WARN if issues
            else PassStatus.PASS
        )
        return PassResult(
            name="type-check",
            status=status,
            issues=issues,
            meta={"nodesChecked": checked},
        )

    # ── Pass: Effect Audit ───────────────────────────────────────────────────

    def _pass_effect_audit(self, graph: ComputationGraph) -> PassResult:
        issues: list[Issue] = []
        declared = set(graph.collect_effects())
        program_declared = set(graph.declared_effects)

        # Effects used but not declared at program level
        for effect in declared:
            if effect not in program_declared and graph.declared_effects:
                issues.append(Issue(
                    PassStatus.WARN, "FX001",
                    f"Effect '{effect.value}' used in graph but not in program declaration",
                ))

        # Check op effects match node effect declarations
        for node in graph.nodes:
            if node.kind == NodeKind.EXEC and node.op:
                sig = OP_SIGNATURES.get(node.op)
                if sig:
                    required_effects = set(sig[2])
                    declared_effects = set(node.effects)
                    missing = required_effects - declared_effects
                    for eff in missing:
                        issues.append(Issue(
                            PassStatus.FAIL, "FX002",
                            f"Node '{node.node_id}' uses op '{node.op.value}' "
                            f"which requires effect '{eff.value}' but it is not declared",
                            node.node_id,
                        ))

        status = (
            PassStatus.FAIL if any(i.severity == PassStatus.FAIL for i in issues)
            else PassStatus.WARN if issues
            else PassStatus.PASS
        )
        return PassResult(
            name="effect-audit",
            status=status,
            issues=issues,
            meta={"effectsDeclared": len(declared)},
        )

    # ── Pass: Dead Node Detection ────────────────────────────────────────────

    def _pass_dead_node(self, graph: ComputationGraph) -> PassResult:
        issues: list[Issue] = []

        if not graph.entry_id:
            return PassResult(
                name="dead-node",
                status=PassStatus.WARN,
                issues=[Issue(PassStatus.WARN, "D000", "No entry point set; cannot determine reachability")],
            )

        # BFS backwards from entry
        reachable: set[str] = set()
        queue = [graph.entry_id]
        # Build reverse adjacency (target → sources)
        reverse: dict[str, list[str]] = {}
        for edge in graph.edges:
            reverse.setdefault(edge.to_id, []).append(edge.from_id)

        # BFS forward from entry (nodes entry depends on = upstream)
        forward: dict[str, list[str]] = {}
        for edge in graph.edges:
            forward.setdefault(edge.from_id, []).append(edge.to_id)

        # Walk all nodes reachable *from* the entry via reverse edges
        visited: set[str] = set()
        q = [graph.entry_id]
        while q:
            cur = q.pop()
            if cur in visited:
                continue
            visited.add(cur)
            for src in reverse.get(cur, []):
                q.append(src)
        reachable = visited

        dead = [n.node_id for n in graph.nodes if n.node_id not in reachable]
        for nid in dead:
            issues.append(Issue(
                PassStatus.WARN, "D001",
                f"Node '{nid}' is not reachable from entry point",
                nid,
            ))

        status = PassStatus.WARN if dead else PassStatus.PASS
        return PassResult(
            name="dead-node",
            status=status,
            issues=issues,
            meta={"deadNodes": dead, "reachableNodes": len(reachable)},
        )

    # ── Pass: Entry Point ────────────────────────────────────────────────────

    def _pass_entry_point(self, graph: ComputationGraph) -> PassResult:
        issues: list[Issue] = []
        node_ids = {n.node_id for n in graph.nodes}

        if not graph.entry_id:
            issues.append(Issue(PassStatus.FAIL, "EP001", "No entry point declared"))
        elif graph.entry_id not in node_ids:
            issues.append(Issue(
                PassStatus.FAIL, "EP002",
                f"Entry point '{graph.entry_id}' does not reference a known node",
                graph.entry_id,
            ))

        status = PassStatus.FAIL if issues else PassStatus.PASS
        return PassResult(name="entry-point", status=status, issues=issues)

    # ── Pass: Confidence ─────────────────────────────────────────────────────

    def _pass_confidence(self, graph: ComputationGraph) -> PassResult:
        issues: list[Issue] = []
        LOW_THRESHOLD = 0.75

        low_conf = [n for n in graph.nodes if n.confidence < LOW_THRESHOLD]
        for node in low_conf:
            issues.append(Issue(
                PassStatus.WARN, "C001",
                f"Node '{node.node_id}' has low confidence score {node.confidence:.2f} "
                f"(threshold: {LOW_THRESHOLD}). Recommend secondary verification.",
                node.node_id,
            ))

        avg_conf = (
            sum(n.confidence for n in graph.nodes) / len(graph.nodes)
            if graph.nodes else 1.0
        )
        status = PassStatus.WARN if low_conf else PassStatus.PASS
        return PassResult(
            name="confidence",
            status=status,
            issues=issues,
            meta={
                "averageConfidence": round(avg_conf, 4),
                "lowConfidenceNodes": len(low_conf),
            },
        )
