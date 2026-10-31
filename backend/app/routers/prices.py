from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import admin_user, current_user
from ..models import CityPrice, PriceItem, User, UserPriceOverride
from ..schemas import CityPriceIn, OverrideIn, PriceItemIn, PriceOut

router = APIRouter(tags=["prix"])


def _item(db: Session, key: str) -> PriceItem:
    it = db.scalar(select(PriceItem).where(PriceItem.key == key))
    if not it:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Poste inconnu : {key}")
    return it


def _norm(city: str) -> str:
    return city.strip().lower()


def effective_prices(db: Session, user_id: int | None, city: str) -> list[PriceOut]:
    city = _norm(city)
    rows = db.scalars(select(CityPrice).where(CityPrice.city.in_(["*", city]))).all()
    default = {r.item_id: r.value for r in rows if r.city == "*"}
    local = {r.item_id: r.value for r in rows if r.city == city}
    mine = {}
    if user_id:
        mine = {o.item_id: o.value for o in db.scalars(select(UserPriceOverride).where(UserPriceOverride.user_id == user_id))}
    out = []
    for it in db.scalars(select(PriceItem).order_by(PriceItem.id)):
        if it.id in mine:
            v, s = mine[it.id], "user"
        elif it.id in local:
            v, s = local[it.id], "city"
        elif it.id in default:
            v, s = default[it.id], "default"
        else:
            continue
        out.append(PriceOut(key=it.key, label=it.label, unit=it.unit, value=v, source=s))
    return out


@router.get("/prices", response_model=list[PriceOut])
def prices(city: str = "*", db: Session = Depends(get_db), user: User = Depends(current_user)):
    return effective_prices(db, user.id, city)


@router.put("/prices/overrides", response_model=PriceOut)
def set_override(data: OverrideIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    it = _item(db, data.key)
    o = db.scalar(select(UserPriceOverride).where(UserPriceOverride.user_id == user.id, UserPriceOverride.item_id == it.id))
    if o:
        o.value = data.value
    else:
        db.add(UserPriceOverride(user_id=user.id, item_id=it.id, value=data.value))
    db.commit()
    return PriceOut(key=it.key, label=it.label, unit=it.unit, value=data.value, source="user")


@router.delete("/prices/overrides/{key}", status_code=204)
def clear_override(key: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    it = _item(db, key)
    o = db.scalar(select(UserPriceOverride).where(UserPriceOverride.user_id == user.id, UserPriceOverride.item_id == it.id))
    if o:
        db.delete(o)
        db.commit()
    return Response(status_code=204)


@router.post("/admin/price-items", status_code=201)
def create_item(data: PriceItemIn, db: Session = Depends(get_db), _: User = Depends(admin_user)):
    if db.scalar(select(PriceItem).where(PriceItem.key == data.key)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce poste existe déjà")
    it = PriceItem(key=data.key, label=data.label, unit=data.unit)
    db.add(it)
    db.flush()
    db.add(CityPrice(item_id=it.id, city="*", value=data.default_value))
    db.commit()
    return {"key": it.key}


@router.put("/admin/prices")
def set_city_price(data: CityPriceIn, db: Session = Depends(get_db), _: User = Depends(admin_user)):
    it, city = _item(db, data.key), _norm(data.city)
    cp = db.scalar(select(CityPrice).where(CityPrice.item_id == it.id, CityPrice.city == city))
    if cp:
        cp.value = data.value
    else:
        db.add(CityPrice(item_id=it.id, city=city, value=data.value))
    db.commit()
    return {"key": it.key, "city": city, "value": data.value}
