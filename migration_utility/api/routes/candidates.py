from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from migration_utility.api.deps import get_db_session
from migration_utility.api.schemas import CandidateRead
from migration_utility.datastore.models import Batch, MigrationRun
from migration_utility.selection.service import CandidateService

router = APIRouter(tags=["candidates"])


@router.get("/batches/{batch_id}/candidates", response_model=list[CandidateRead])
def list_batch_candidates(
    batch_id: UUID, db: Session = Depends(get_db_session)
):
    batch = db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return CandidateService(db).list_for_batch(batch_id)


@router.get("/runs/{run_id}/candidates", response_model=list[CandidateRead])
def list_run_candidates(run_id: UUID, db: Session = Depends(get_db_session)):
    run = db.get(MigrationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Migration run not found")
    return CandidateService(db).list_for_run(run_id)
