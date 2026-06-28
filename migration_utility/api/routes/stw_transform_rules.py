"""STW utility transformation rules — view, edit, and preview."""

from __future__ import annotations

from copy import deepcopy
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from migration_utility.api.deps import get_db_session
from migration_utility.api.routes.rules import _get_project
from migration_utility.api.schemas import (
    StwTariffTableUpdate,
    StwTransformPreviewRead,
    StwTransformPreviewRequest,
    StwTransformRulePatch,
    StwTransformRulesRead,
)
from migration_utility.transforms.stw import (
    get_stw_rules,
    transform_area_code,
    transform_property_type,
    transform_rateband,
)
from migration_utility.transforms.stw.config import update_stw_rule

router = APIRouter(prefix="/projects/{project_id}/stw-transform-rules", tags=["stw-transforms"])


def _read_rules(project) -> StwTransformRulesRead:
    cfg = project.config or {}
    merged = get_stw_rules(cfg)
    return StwTransformRulesRead(
        property_type=merged["property_type"],
        area_code=merged["area_code"],
        rateband=merged["rateband"],
        overrides=cfg.get("stw_transform_rules") or {},
        tariff_table=cfg.get("stw_tariff_table") or [],
    )


@router.get("", response_model=StwTransformRulesRead)
def get_stw_transform_rules(project_id: UUID, db: Session = Depends(get_db_session)):
    project = _get_project(project_id, db)
    return _read_rules(project)


@router.put("/{rule_key}", response_model=StwTransformRulesRead)
def update_stw_transform_rule(
    project_id: UUID,
    rule_key: str,
    body: StwTransformRulePatch,
    db: Session = Depends(get_db_session),
):
    if rule_key not in ("property_type", "area_code", "rateband"):
        raise HTTPException(status_code=400, detail="rule_key must be property_type, area_code, or rateband")
    project = _get_project(project_id, db)
    project.config = update_stw_rule(project.config, rule_key, body.rules)
    db.commit()
    db.refresh(project)
    return _read_rules(project)


@router.put("/tariff-table", response_model=StwTransformRulesRead)
def update_stw_tariff_table(
    project_id: UUID,
    body: StwTariffTableUpdate,
    db: Session = Depends(get_db_session),
):
    project = _get_project(project_id, db)
    cfg = dict(project.config or {})
    cfg["stw_tariff_table"] = body.rows
    project.config = cfg
    db.commit()
    db.refresh(project)
    return _read_rules(project)


@router.post("/reset", response_model=StwTransformRulesRead)
def reset_stw_transform_rules(project_id: UUID, db: Session = Depends(get_db_session)):
    project = _get_project(project_id, db)
    cfg = dict(project.config or {})
    cfg.pop("stw_transform_rules", None)
    cfg.pop("stw_tariff_table", None)
    project.config = cfg
    db.commit()
    db.refresh(project)
    return _read_rules(project)


@router.post("/preview", response_model=StwTransformPreviewRead)
def preview_stw_transform(
    project_id: UUID,
    body: StwTransformPreviewRequest,
    db: Session = Depends(get_db_session),
):
    project = _get_project(project_id, db)
    merged = get_stw_rules(project.config or {})
    record = deepcopy(body.record)
    tariff_table = (project.config or {}).get("stw_tariff_table") or []
    context = {"tariff_table": tariff_table, "tariff_mappings": {}}

    if body.rule_key == "property_type":
        result = transform_property_type(record, merged["property_type"])
    elif body.rule_key == "area_code":
        result = transform_area_code(record, merged["area_code"], context=context)
    else:
        rateband_rules = {**merged["rateband"], "tariff_table": tariff_table}
        result = transform_rateband(record, rateband_rules)

    return StwTransformPreviewRead(rule_key=body.rule_key, result=result, record=record)
