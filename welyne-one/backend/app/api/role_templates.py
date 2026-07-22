"""
Gestion des gabarits de rôle (§6-A8, option A validée : templates fixes gérés
en base, pas de génération LLM). Réservé aux admins — un RH ajuste un gabarit
sans toucher au code, cf. app/services/generation/onboarding_checklist.py qui
les consomme.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.role_template import RoleTemplate
from app.models.user import User

router = APIRouter(prefix="/role-templates", tags=["role-templates"])


class RoleTemplateOut(BaseModel):
    id: uuid.UUID
    role_category: str
    required_documents: list[str]
    equipment: list[str]
    accounts_to_create: list[str]
    week_one_agenda: list[str]

    class Config:
        from_attributes = True


class RoleTemplateIn(BaseModel):
    role_category: str
    required_documents: list[str] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)
    accounts_to_create: list[str] = Field(default_factory=list)
    week_one_agenda: list[str] = Field(default_factory=list)


@router.get("", response_model=list[RoleTemplateOut])
def list_role_templates(
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin", "recruteur", "lecteur")),
):
    return db.query(RoleTemplate).order_by(RoleTemplate.role_category).all()


@router.post("", response_model=RoleTemplateOut)
def create_role_template(
    body: RoleTemplateIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    existing = db.query(RoleTemplate).filter_by(role_category=body.role_category).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Cette catégorie existe déjà — utilisez PATCH pour la modifier")

    template = RoleTemplate(**body.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.patch("/{template_id}", response_model=RoleTemplateOut)
def update_role_template(
    template_id: uuid.UUID,
    body: RoleTemplateIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    template = db.get(RoleTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Gabarit introuvable")

    for field, value in body.model_dump().items():
        setattr(template, field, value)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=204)
def delete_role_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    template = db.get(RoleTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Gabarit introuvable")
    db.delete(template)
    db.commit()