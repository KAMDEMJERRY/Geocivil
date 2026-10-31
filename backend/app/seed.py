from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import CityPrice, PriceItem

# (clé, libellé, unité, prix par défaut FCFA) — valeurs indicatives, gérées ensuite par l'admin
DEFAULT_PRICES = [
    ("ciment", "Sac de ciment 50 kg", "sac", 6500),
    ("sable", "Sable", "m³", 12000),
    ("gravier", "Gravier", "m³", 22000),
    ("acier", "Acier HA", "kg", 850),
    ("bloc", "Parpaing 15 cm", "u", 450),
    ("tole", "Couverture tôle posée", "m²", 12000),
    ("charpente", "Charpente", "m²", 8000),
    ("carrelage", "Carrelage posé", "m²", 9000),
    ("peinture", "Peinture", "L", 3500),
    ("porte", "Porte", "u", 60000),
    ("fenetre", "Fenêtre", "u", 45000),
    ("hardcore", "Tout-venant", "m³", 15000),
    ("fouille", "Terrassement", "m³", 3500),
    ("mo_pct", "Main d'œuvre (% matériaux)", "%", 35),
    ("lots_pct", "Plomberie + électricité (% matériaux)", "%", 12),
]


def seed_prices(db: Session) -> None:
    existing = {i.key: i for i in db.scalars(select(PriceItem))}
    for key, label, unit, value in DEFAULT_PRICES:
        if key in existing:
            continue
        item = PriceItem(key=key, label=label, unit=unit)
        db.add(item)
        db.flush()
        db.add(CityPrice(item_id=item.id, city="*", value=value))
    db.commit()
