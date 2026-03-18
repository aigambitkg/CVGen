"""Job tracking API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from cvgen.api.models import JobStatusResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

# In-memory job store (shared with app)
_jobs: dict[str, dict] = {}


def register_job(job_id: str, job_data: dict) -> None:
    """Register a job in the store."""
    _jobs[job_id] = job_data


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get the status of a submitted job."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobStatusResponse(**job)


@router.get("", response_model=list[JobStatusResponse])
async def list_jobs() -> list[JobStatusResponse]:
    """List all recent jobs."""
    return [JobStatusResponse(**j) for j in _jobs.values()]
