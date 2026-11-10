"""E10.0 opt-in search engine adapter for Noesis.

The E06 Synthesizer remains unchanged. This module exposes an explicit
semantic-signature synthesis API with a conservative fallback. The caller
must supply learned/random libraries; no evaluation target is used to
construct the search frontier.
"""
from dataclasses import dataclass
from noesis_synth import Synthesizer
from run_e09_budget_portfolio import search
from noesis_constructive_search import synthesize_boolean,synthesize_bitvector

@dataclass(frozen=True)
class SearchConfig:
    budget:int=8000
    attempt_cap:int=2000
    base_depth:int=5
    deep_depth:int=7
    enabled:bool=False

    def validate(self):
        if (self.budget<4 or self.attempt_cap<4 or self.base_depth<1
            or self.deep_depth<=self.base_depth):
            raise ValueError("invalid search configuration")

class AdaptiveSearchEngine:
    """Opt-in candidate search. Does not mutate the legacy synthesizer."""
    def __init__(self,learned=(),random_macros=(),config=None):
        self.learned=tuple(learned)
        self.random_macros=tuple(random_macros)
        self.config=config if config is not None else SearchConfig()
        self.config.validate()
        self.legacy=Synthesizer()
        self.last_report=None

    def candidates(self,examples,semantics):
        if semantics not in ("boolean","bitvector"):
            raise ValueError("unsupported semantics")
        if not self.config.enabled:
            self.last_report={"mode":"legacy","policy":None,
                              "work":0,"attempts":0}
            return set(self.legacy.base)
        policy="plain_deep" if semantics=="boolean" else "learned_75"
        r=search(self.learned,self.random_macros,examples,semantics,
                 self.config.budget,self.config.attempt_cap,
                 policy if policy=="plain_deep" else 75,
                 self.config.base_depth,self.config.deep_depth)
        self.last_report={"mode":"experimental","policy":policy,
                          "work":r["work"],"attempts":r["attempts"],
                          "unique_signatures":len(r["seen"])}
        return r["seen"]

    def contains(self,signature,examples,semantics):
        """Diagnostic membership; not a constructive synthesis result."""
        return signature in self.candidates(examples,semantics)

    def synthesize(self,observations):
        """Return an observation-consistent Boolean AST.

        Experimental synthesis is opt-in. If no verified candidate is found,
        fall back to E06, with explicit provenance in last_report.
        """
        if not self.config.enabled:
            p=self.legacy.synthesize(observations)
            self.last_report={"mode":"legacy_constructive","policy":None,
                              "work":0,"attempts":0}
            return p
        result=synthesize_boolean(
            observations,self.learned,self.random_macros,
            self.config.budget,self.config.attempt_cap,
            self.config.base_depth,self.config.deep_depth)
        if result.verified:
            self.last_report={"mode":"adaptive_constructive",
                              "policy":result.policy,"work":result.work,
                              "attempts":result.attempts,
                              "unique_signatures":result.unique_signatures,
                              "verified":True}
            return result.program
        p=self.legacy.synthesize(observations)
        self.last_report={"mode":"legacy_fallback","policy":result.policy,
                          "work":result.work,"attempts":result.attempts,
                          "unique_signatures":result.unique_signatures,
                          "verified":p is not None}
        return p

    def synthesize_bitvector(self,examples,outputs):
        """Opt-in observational 8-bit synthesis, no legacy BV fallback."""
        if not self.config.enabled:
            raise RuntimeError("bitvector synthesis requires enabled=True")
        result=synthesize_bitvector(
            examples,outputs,self.learned,self.random_macros,
            self.config.budget,self.config.attempt_cap,
            self.config.base_depth,self.config.deep_depth)
        self.last_report={"mode":"adaptive_bitvector",
                          "policy":result.policy,"work":result.work,
                          "attempts":result.attempts,
                          "unique_signatures":result.unique_signatures,
                          "verified":result.verified}
        return result.program
