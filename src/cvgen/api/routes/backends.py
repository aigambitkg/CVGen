"""Backend management API routes."""

from __future__ import annotations

from fastapi import APIRouter

from cvgen.api.models import BackendInfo, BackendListResponse

router = APIRouter(prefix="/backends", tags=["backends"])


@router.get("", response_model=BackendListResponse)
async def list_backends() -> BackendListResponse:
    """List all available quantum backends."""
    from cvgen.api.app import backend_registry

    infos = []
    for name, backend in backend_registry.items():
        caps = backend.capabilities
        infos.append(
            BackendInfo(
                name=name,
                max_qubits=caps.max_qubits,
                supported_gates=[g.value for g in caps.supported_gates],
                supports_statevector=caps.supports_statevector,
                backend_type=_classify_backend(name),
                status="available",
            )
        )

    return BackendListResponse(backends=infos, default_backend="simulator")


def _classify_backend(name: str) -> str:
    """Classify backend type from name."""
    if "ibm" in name or "braket" in name or "azure" in name:
        return "cloud"
    if "pilot" in name or "qpanda" in name:
        return "hardware"
    return "simulator"
