"""Single engine-facing problem contract. Legacy functions are adapted, not duplicated."""
from dataclasses import dataclass
from typing import Callable
from functools import partial
from . import problems, generation, reduction, certificate, max_subarray

@dataclass(frozen=True)
class ProblemSpec:
    metadata: dict
    oracle_id: str
    validate: Callable
    reference: Callable
    check: Callable
    complexity: Callable
    size: Callable
    strategy: Callable
    random_case: Callable
    smaller: Callable
    certificate: Callable
    visualization: str = 'json'

    def public_metadata(self):
        return {**self.metadata, 'oracle_id':self.oracle_id, 'contract_version':self.metadata['id'],
                'visualization':self.visualization,
                'capabilities':{'random_generation':True,'hypothesis_generation':True,'legal_reduction':True,
                                'reference_check':True,'python_line_trace':True,'hostile_code_sandbox':False}}

def legacy(problem_id, oracle_id):
    return ProblemSpec(problems.PROBLEMS[problem_id], oracle_id,
        partial(problems.validate_case,problem_id),
        partial(problems.reference,problem_id),
        partial(problems.check_output,problem_id),
        partial(problems.complexity,problem_id),
        partial(problems.size,problem_id),
        partial(generation.strategy_for,problem_id),
        partial(generation.random_case,problem_id),
        partial(reduction.smaller_cases,problem_id),
        partial(certificate.checked_example,problem_id), 'graph' if problem_id=='dijkstra_v1' else 'array')

REGISTRY = {
    "dijkstra_v1":legacy("dijkstra_v1","networkx_bellman_ford+independent_floyd"),
    "binary_search_v1":legacy("binary_search_v1","linear_membership_checker"),
    max_subarray.ID:ProblemSpec(max_subarray.METADATA,"exhaustive_segments+kadane",
        partial(problems.validate_case,max_subarray.ID),
        partial(problems.reference,max_subarray.ID),
        max_subarray.check,lambda c:(len(c["array"]),sum(abs(v) for v in c["array"])),
        lambda c:{"length":len(c["array"])},max_subarray.strategy,max_subarray.random_case,
        max_subarray.smaller,lambda c,a,e:max_subarray.certificate(c,a),'array')
}

def spec_for(problem_id):
    if problem_id not in REGISTRY:
        raise problems.InvalidCase("Unknown problem")
    return REGISTRY[problem_id]
