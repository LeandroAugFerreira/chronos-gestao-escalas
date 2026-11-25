from fastapi import APIRouter, Depends
from app.api.dependencies import require
from app.schemas.labor_transition import TransitionInput
from app.services.labor_transition import compare, metadata

router = APIRouter(prefix="/api/v1/labor-transition", tags=["Chronos 2.0 · transição normativa"])


@router.get("")
def references(principal=Depends(require("org:read"))):
    return metadata()


@router.post("/compare")
def comparison(payload: TransitionInput, principal=Depends(require("org:read"))):
    # Stateless comparison: no payroll lookup, persistence or changes to rules.
    return compare(payload)
