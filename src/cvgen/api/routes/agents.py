"""Agent API routes — Grover search and VQE optimization."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from cvgen.api.models import GroverRequest, GroverResponse, VQERequest, VQEResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/grover", response_model=GroverResponse)
async def run_grover_search(req: GroverRequest) -> GroverResponse:
    """Run Grover's quantum search algorithm."""
    from cvgen.agents.quantum_agent import QuantumAgent, SearchTask
    from cvgen.api.app import get_backend

    backend = get_backend(req.backend)
    agent = QuantumAgent(backend, shots=req.shots)

    search_space = 2 ** req.num_qubits
    for t in req.target_states:
        if t < 0 or t >= search_space:
            raise HTTPException(
                status_code=400,
                detail=f"Target state {t} out of range [0, {search_space - 1}]",
            )

    target_set = set(req.target_states)
    task = SearchTask(
        num_qubits=req.num_qubits,
        oracle_fn=lambda x, _ts=target_set: x in _ts,
        max_solutions=len(req.target_states),
    )

    try:
        solutions = agent.run_search(task)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Grover search failed: {e}")

    return GroverResponse(
        solutions=solutions,
        num_qubits=req.num_qubits,
        search_space_size=search_space,
        total_steps=len(agent._quantum_results),
        success=len(solutions) > 0,
    )


@router.post("/vqe", response_model=VQEResponse)
async def run_vqe_optimization(req: VQERequest) -> VQEResponse:
    """Run Variational Quantum Eigensolver optimization."""
    from cvgen.agents.hybrid_agent import HybridAgent, VariationalTask
    from cvgen.api.app import get_backend

    backend = get_backend(req.backend)
    agent = HybridAgent(backend, shots=req.shots)

    task = VariationalTask(
        num_qubits=req.num_qubits,
        cost_observable=req.cost_observable,
        ansatz_depth=req.ansatz_depth,
        max_iterations=req.max_iterations,
        optimizer_method=req.optimizer,
    )

    try:
        result = agent.run(task)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VQE optimization failed: {e}")

    vqe_result = result.value or {}
    return VQEResponse(
        optimal_cost=vqe_result.get("optimal_cost", 0.0),
        optimal_params=vqe_result.get("optimal_params", []),
        converged=vqe_result.get("converged", False),
        num_evaluations=vqe_result.get("num_evaluations", 0),
        cost_history=agent.opt_history.costs,
        success=result.success,
    )
