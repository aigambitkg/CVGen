"""Circuit execution API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from cvgen.api.models import CircuitRequest, CircuitResponse, GateRequest
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import GateType, JobConfig

router = APIRouter(prefix="/circuits", tags=["circuits"])

GATE_MAP = {
    "h": "h", "x": "x", "y": "y", "z": "z", "s": "s", "t": "t",
    "rx": "rx", "ry": "ry", "rz": "rz",
    "cx": "cx", "cz": "cz", "swap": "swap", "ccx": "ccx",
    "measure": "measure",
}


def _build_circuit(req: CircuitRequest) -> QuantumCircuit:
    """Convert an API request into a QuantumCircuit."""
    qc = QuantumCircuit(req.num_qubits)

    for gate in req.gates:
        gate_name = gate.gate.lower()
        if gate_name not in GATE_MAP:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown gate: {gate.gate}. Supported: {list(GATE_MAP.keys())}",
            )

        try:
            if gate_name == "h":
                qc.h(gate.targets[0])
            elif gate_name == "x":
                qc.x(gate.targets[0])
            elif gate_name == "y":
                qc.y(gate.targets[0])
            elif gate_name == "z":
                qc.z(gate.targets[0])
            elif gate_name == "s":
                qc.s(gate.targets[0])
            elif gate_name == "t":
                qc.t(gate.targets[0])
            elif gate_name == "rx":
                qc.rx(gate.targets[0], gate.params[0])
            elif gate_name == "ry":
                qc.ry(gate.targets[0], gate.params[0])
            elif gate_name == "rz":
                qc.rz(gate.targets[0], gate.params[0])
            elif gate_name == "cx":
                qc.cx(gate.targets[0], gate.targets[1])
            elif gate_name == "cz":
                qc.cz(gate.targets[0], gate.targets[1])
            elif gate_name == "swap":
                qc.swap(gate.targets[0], gate.targets[1])
            elif gate_name == "ccx":
                qc.ccx(gate.targets[0], gate.targets[1], gate.targets[2])
            elif gate_name == "measure":
                for t in gate.targets:
                    qc.measure(t, t)
        except (IndexError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid gate parameters for {gate.gate}: {e}")

    return qc


@router.post("/execute", response_model=CircuitResponse)
async def execute_circuit(req: CircuitRequest) -> CircuitResponse:
    """Execute a quantum circuit and return measurement results."""
    from cvgen.api.app import get_backend

    qc = _build_circuit(req)

    # Add measure_all if no explicit measurements
    has_measure = any(g.gate.lower() == "measure" for g in req.gates)
    if not has_measure:
        qc.measure_all()

    backend = get_backend(req.backend)
    config = JobConfig(
        shots=req.shots,
        seed=req.seed,
        return_statevector=req.return_statevector,
    )

    try:
        result = backend.execute(qc, config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Circuit execution failed: {e}")

    return CircuitResponse(
        counts=result.counts,
        shots=result.shots,
        probabilities=result.probabilities,
        most_likely=result.most_likely(),
        metadata=result.metadata,
    )
