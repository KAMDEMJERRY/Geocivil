from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

SoilType = Literal["laterite", "argile", "sable", "gravier", "roche", "marais"]


class Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(default="", max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(Orm):
    id: int
    email: EmailStr
    full_name: str
    role: str


class SoilIn(BaseModel):
    soil_type: SoilType
    bearing_capacity_kpa: float = Field(ge=20, le=1500)
    water_table_depth_m: float = Field(ge=0, le=50)
    flood_zone: bool = False
    geotech_study: Literal["none", "sondages", "rapport"] = "none"


class SoilOut(SoilIn, Orm):
    pass


class BuildingIn(BaseModel):
    footprint_m2: float = Field(ge=10, le=2000)
    length_width_ratio: float = Field(default=1.5, ge=1, le=3)
    floors: int = Field(ge=0, le=2, description="Nombre d'étages (R+N), phase 1 : N ≤ 2")
    floor_height_m: float = Field(default=3.0, ge=2.4, le=4.0)
    column_span_m: float = Field(default=4.0, ge=2.5, le=6.0)
    usage: Literal["habitation", "bureaux", "commerce"] = "habitation"
    roof_type: Literal["tole", "terrasse"] = "tole"
    roof_slope_pct: float = Field(default=30.0, ge=0, le=100)


class BuildingOut(BuildingIn, Orm):
    pass


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    city: str = Field(min_length=1, max_length=120)
    building_type: Literal["maison", "immeuble", "hangar", "ouvrage_annexe"] = "maison"
    soil: SoilIn
    building: BuildingIn

    @field_validator("building_type")
    @classmethod
    def phase1_only(cls, v):
        if v != "maison":
            raise ValueError("Ce type d'ouvrage sera disponible dans une prochaine phase")
        return v


class ProjectOut(Orm):
    id: int
    name: str
    city: str
    building_type: str
    norm: str
    created_at: datetime
    updated_at: datetime
    soil: SoilOut
    building: BuildingOut


class PriceOut(BaseModel):
    key: str
    label: str
    unit: str
    value: float
    source: Literal["default", "city", "user"]


class PriceItemIn(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9_]{2,40}$")
    label: str = Field(max_length=120)
    unit: str = Field(max_length=20)
    default_value: float = Field(ge=0)


class CityPriceIn(BaseModel):
    key: str
    city: str = Field(min_length=1, max_length=120)
    value: float = Field(ge=0)


class OverrideIn(BaseModel):
    key: str
    value: float = Field(ge=0)
