"""
rule_engine.py
==============
Lightweight forward-chaining rule engine for AgriXAI Module 6.

Replaces Experta (which is incompatible with Python 3.10+). Provides:
  - Fact:       a dataclass-like dict with a kind tag
  - WorkingMemory: stores facts, supports query by kind + predicate
  - Rule:       (name, salience, condition_fn, action_fn)
  - Engine:     fixed-point forward chaining with conflict resolution by salience

Design notes
------------
We deliberately avoid the RETE algorithm. For Module 6 we have <50 rules and
<200 facts at any time, so a naive O(rules x facts) match per cycle is fine
and far easier to debug than RETE. Rules can declare a `salience` (priority);
ties broken by insertion order. The engine halts when a full pass adds no new
facts (fixed point) or after `max_cycles` (safety).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional
import itertools
import logging

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Facts
# ---------------------------------------------------------------------------

class Fact(dict):
    """A fact is a dict with a mandatory 'kind' key.

    Example:
        Fact(kind="prediction", class_name="Wheat_Yellow_Rust", confidence=0.51)
    """

    def __init__(self, kind: str, **kwargs):
        super().__init__(kind=kind, **kwargs)
        self._id = next(_FACT_ID)

    @property
    def kind(self) -> str:
        return self["kind"]

    @property
    def id(self) -> int:
        return self._id

    def __repr__(self) -> str:
        body = ", ".join(f"{k}={v!r}" for k, v in self.items() if k != "kind")
        return f"Fact[{self.kind}]({body})"


_FACT_ID = itertools.count(1)


# ---------------------------------------------------------------------------
# Working memory
# ---------------------------------------------------------------------------

class WorkingMemory:
    """In-memory fact store. Indexed by `kind` for fast retrieval."""

    def __init__(self) -> None:
        self._by_kind: Dict[str, List[Fact]] = {}
        self._all: List[Fact] = []

    def add(self, fact: Fact) -> Fact:
        self._all.append(fact)
        self._by_kind.setdefault(fact.kind, []).append(fact)
        return fact

    def add_many(self, facts: Iterable[Fact]) -> None:
        for f in facts:
            self.add(f)

    def query(
        self,
        kind: str,
        predicate: Optional[Callable[[Fact], bool]] = None,
    ) -> List[Fact]:
        bucket = self._by_kind.get(kind, [])
        if predicate is None:
            return list(bucket)
        return [f for f in bucket if predicate(f)]

    def first(
        self,
        kind: str,
        predicate: Optional[Callable[[Fact], bool]] = None,
    ) -> Optional[Fact]:
        results = self.query(kind, predicate)
        return results[0] if results else None

    def exists(self, kind: str, predicate: Optional[Callable[[Fact], bool]] = None) -> bool:
        return bool(self.query(kind, predicate))

    def all(self) -> List[Fact]:
        return list(self._all)

    def __len__(self) -> int:
        return len(self._all)


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

@dataclass
class Rule:
    """A forward-chaining production rule.

    condition: callable (wm) -> bindings dict | None
        Return None or {} (empty) to indicate "did not fire".
        Return a non-empty dict of bindings to indicate "fires" — these
        bindings are passed to the action.

    action: callable (wm, bindings) -> list[Fact]
        Returns NEW facts to add. May return [] if it only mutates state.
    """

    name: str
    condition: Callable[[WorkingMemory], Optional[Dict[str, Any]]]
    action: Callable[[WorkingMemory, Dict[str, Any]], List[Fact]]
    salience: int = 0
    fired: List[int] = field(default_factory=list)  # WM sizes at which this rule fired


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class Engine:
    """Forward-chaining engine with salience-ordered conflict resolution."""

    def __init__(self, max_cycles: int = 50) -> None:
        self.rules: List[Rule] = []
        self.wm = WorkingMemory()
        self.max_cycles = max_cycles
        self.trace: List[str] = []  # human-readable firing log

    # ---- registration -----------------------------------------------------

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    def assert_fact(self, fact: Fact) -> None:
        self.wm.add(fact)

    def assert_facts(self, facts: Iterable[Fact]) -> None:
        self.wm.add_many(facts)

    # ---- execution --------------------------------------------------------

    def run(self) -> WorkingMemory:
        """Run until fixed point or max_cycles, whichever comes first.

        A rule fires at most once per `run()` call. This prevents infinite
        loops when actions add facts that re-satisfy the same condition.
        Use `reset()` to clear fired state for a new diagnosis.
        """
        fired_names: set = set()
        for cycle in range(self.max_cycles):
            ordered_rules = sorted(
                self.rules, key=lambda r: (-r.salience, self.rules.index(r))
            )
            any_fired = False

            for rule in ordered_rules:
                if rule.name in fired_names:
                    continue
                try:
                    bindings = rule.condition(self.wm)
                except Exception as e:  # pragma: no cover
                    log.exception("Rule %s condition raised: %s", rule.name, e)
                    fired_names.add(rule.name)  # don't retry a broken rule
                    continue
                if not bindings:
                    continue
                try:
                    new_facts = rule.action(self.wm, bindings) or []
                except Exception as e:  # pragma: no cover
                    log.exception("Rule %s action raised: %s", rule.name, e)
                    fired_names.add(rule.name)
                    continue
                for f in new_facts:
                    self.wm.add(f)
                fired_names.add(rule.name)
                rule.fired.append(len(self.wm))
                self.trace.append(
                    f"[cycle {cycle}] {rule.name} fired -> "
                    f"+{len(new_facts)} facts (wm={len(self.wm)})"
                )
                any_fired = True
                # Restart the cycle so higher-salience rules see new facts.
                break

            if not any_fired:
                log.debug("Fixed point reached after %d cycles", cycle)
                break
        else:
            log.warning("Engine hit max_cycles=%d without fixed point", self.max_cycles)

        return self.wm

    def reset(self) -> None:
        self.wm = WorkingMemory()
        self.trace = []
        for r in self.rules:
            r.fired.clear()
