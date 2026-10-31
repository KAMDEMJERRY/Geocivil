from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(20), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    projects: Mapped[list["Project"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    city: Mapped[str] = mapped_column(String(120))
    building_type: Mapped[str] = mapped_column(String(30), default="maison")
    norm: Mapped[str] = mapped_column(String(20), default="BAEL")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    owner: Mapped[User] = relationship(back_populates="projects")
    soil: Mapped["SoilData"] = relationship(back_populates="project", uselist=False, cascade="all, delete-orphan")
    building: Mapped["BuildingData"] = relationship(back_populates="project", uselist=False, cascade="all, delete-orphan")
    analyses: Mapped[list["Analysis"]] = relationship(cascade="all, delete-orphan", order_by="Analysis.id.desc()")


class SoilData(Base):
    __tablename__ = "soil_data"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True)
    soil_type: Mapped[str] = mapped_column(String(30))
    bearing_capacity_kpa: Mapped[float] = mapped_column(Float)
    water_table_depth_m: Mapped[float] = mapped_column(Float)
    flood_zone: Mapped[bool] = mapped_column(Boolean, default=False)
    geotech_study: Mapped[str] = mapped_column(String(20), default="none")
    project: Mapped[Project] = relationship(back_populates="soil")


class BuildingData(Base):
    __tablename__ = "building_data"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True)
    footprint_m2: Mapped[float] = mapped_column(Float)
    length_width_ratio: Mapped[float] = mapped_column(Float, default=1.5)
    floors: Mapped[int] = mapped_column(Integer, default=0)
    floor_height_m: Mapped[float] = mapped_column(Float, default=3.0)
    column_span_m: Mapped[float] = mapped_column(Float, default=4.0)
    usage: Mapped[str] = mapped_column(String(20), default="habitation")
    roof_type: Mapped[str] = mapped_column(String(20), default="tole")
    roof_slope_pct: Mapped[float] = mapped_column(Float, default=30.0)
    project: Mapped[Project] = relationship(back_populates="building")


class PriceItem(Base):
    __tablename__ = "price_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True)
    label: Mapped[str] = mapped_column(String(120))
    unit: Mapped[str] = mapped_column(String(20))


class CityPrice(Base):
    __tablename__ = "city_prices"
    __table_args__ = (UniqueConstraint("item_id", "city"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("price_items.id", ondelete="CASCADE"))
    city: Mapped[str] = mapped_column(String(120))  # minuscule ; "*" = prix par défaut
    value: Mapped[float] = mapped_column(Float)


class UserPriceOverride(Base):
    __tablename__ = "user_price_overrides"
    __table_args__ = (UniqueConstraint("user_id", "item_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    item_id: Mapped[int] = mapped_column(ForeignKey("price_items.id", ondelete="CASCADE"))
    value: Mapped[float] = mapped_column(Float)


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    engine_version: Mapped[str] = mapped_column(String(20))
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
