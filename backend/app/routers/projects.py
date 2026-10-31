from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..engine.analysis import VERSION, analyze
from ..models import Analysis, BuildingData, Project, SoilData, User
from ..schemas import ProjectIn, ProjectOut

router = APIRouter(prefix="/projects", tags=["projets"])


def _own(db: Session, user: User, pid: int) -> Project:
    p = db.get(Project, pid)
    if not p or p.owner_id != user.id:  # 404 aussi si le projet appartient à un autre
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Projet introuvable")
    return p


@router.post("", response_model=ProjectOut, status_code=201)
def create(data: ProjectIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = Project(owner_id=user.id, name=data.name, city=data.city, building_type=data.building_type,
                soil=SoilData(**data.soil.model_dump()), building=BuildingData(**data.building.model_dump()))
    db.add(p)
    db.commit()
    return p


@router.get("", response_model=list[ProjectOut])
def list_mine(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.scalars(select(Project).where(Project.owner_id == user.id).order_by(Project.updated_at.desc())).all()


@router.get("/{pid}", response_model=ProjectOut)
def get_one(pid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _own(db, user, pid)


@router.put("/{pid}", response_model=ProjectOut)
def update(pid: int, data: ProjectIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _own(db, user, pid)
    p.name, p.city, p.building_type = data.name, data.city, data.building_type
    for k, v in data.soil.model_dump().items():
        setattr(p.soil, k, v)
    for k, v in data.building.model_dump().items():
        setattr(p.building, k, v)
    db.commit()
    return p


@router.delete("/{pid}", status_code=204)
def delete(pid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.delete(_own(db, user, pid))
    db.commit()
    return Response(status_code=204)


@router.post("/{pid}/analysis")
def run_analysis(pid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _own(db, user, pid)
    try:
        result = analyze(p.soil, p.building)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    db.add(Analysis(project_id=p.id, engine_version=VERSION, result=result))
    db.commit()
    return result


@router.get("/{pid}/analysis")
def last_analysis(pid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _own(db, user, pid)
    if not p.analyses:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucune analyse pour ce projet")
    return p.analyses[0].result
