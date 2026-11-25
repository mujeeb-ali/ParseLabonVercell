"""Parse-tree construction and derivation extraction shared by both parsers."""

from __future__ import annotations

from typing import Any

_MAX_DERIVATION_STEPS = 600


class TreeBuilder:
    def __init__(self) -> None:
        self.nodes: dict[int, dict[str, Any]] = {}
        self.next_id = 0

    def create(self, symbol: str, terminal: bool, created_step: int, parent: int | None = None) -> int:
        nid = self.next_id
        self.next_id += 1
        self.nodes[nid] = {
            "id": nid,
            "symbol": symbol,
            "terminal": terminal,
            "children": [],
            "parent": parent,
            "productionIndex": None,
            "productionText": None,
            "createdStep": created_step,
            "matchedStep": None,
            "expandedStep": None,
        }
        if parent is not None:
            self.nodes[parent]["children"].append(nid)
        return nid

    def expand(self, node_id: int, production: dict[str, Any], step: int, is_terminal) -> list[int]:
        self.nodes[node_id]["productionIndex"] = production["index"]
        self.nodes[node_id]["productionText"] = production["text"]
        self.nodes[node_id]["expandedStep"] = step
        created = []
        for sym in production["rhs"]:
            created.append(self.create(sym, is_terminal(sym), step, node_id))
        return created

    def reduce_node(
        self,
        symbol: str,
        child_ids: list[int],
        production: dict[str, Any],
        step: int,
    ) -> int:
        nid = self.create(symbol, False, step)
        self.nodes[nid]["children"] = list(child_ids)
        for cid in child_ids:
            self.nodes[cid]["parent"] = nid
        self.nodes[nid]["productionIndex"] = production["index"]
        self.nodes[nid]["productionText"] = production["text"]
        self.nodes[nid]["expandedStep"] = step
        return nid

    def nested(self, node_id: int | None = None) -> dict[str, Any] | None:
        if node_id is None:
            return None
        node = self.nodes[node_id]
        return {
            "id": node["id"],
            "symbol": node["symbol"],
            "terminal": node["terminal"],
            "productionIndex": node["productionIndex"],
            "productionText": node["productionText"],
            "createdStep": node["createdStep"],
            "matchedStep": node["matchedStep"],
            "expandedStep": node["expandedStep"],
            "children": [self.nested(c) for c in node["children"]],
        }

    def leaves(self, node_id: int) -> list[str]:
        node = self.nodes[node_id]
        if not node["children"]:
            return [node["symbol"]]
        out: list[str] = []
        for c in node["children"]:
            out.extend(self.leaves(c))
        return out


def _render(frontier: list[dict[str, Any]]) -> str:
    return " ".join(n["symbol"] for n in frontier) if frontier else "\u03b5"


def derivations(tree: dict[str, Any] | None) -> dict[str, Any]:
    """Extract leftmost and rightmost derivations from a completed parse tree."""
    if tree is None:
        return {"leftmost": {"forms": [], "rules": []}, "rightmost": {"forms": [], "rules": []}}

    def walk(side: str) -> dict[str, Any]:
        frontier = [tree]
        forms = [_render(frontier)]
        rules: list[dict[str, Any]] = []
        steps = 0
        while steps < _MAX_DERIVATION_STEPS:
            candidates = [i for i, node in enumerate(frontier) if not node["terminal"]]
            if not candidates:
                break
            index = candidates[0] if side == "left" else candidates[-1]
            node = frontier[index]
            children = node.get("children") or []
            frontier = frontier[:index] + children + frontier[index + 1 :]
            forms.append(_render(frontier))
            rules.append(
                {
                    "symbol": node["symbol"],
                    "productionIndex": node["productionIndex"],
                    "productionText": node["productionText"],
                }
            )
            steps += 1
        return {"forms": forms, "rules": rules, "truncated": steps >= _MAX_DERIVATION_STEPS}

    return {"leftmost": walk("left"), "rightmost": walk("right")}
