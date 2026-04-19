#data_models.py

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field

class PractitionerBasic(BaseModel):
    first_name: str
    last_name:  str
    state:      str
    zip_code:   str

class Practitioner(BaseModel):
    full_name: str
    speciality: str
    npi_number: str
    qualification_certification: str
    contact_details: Optional[str] = Field(default="NA")
    office_hour: Optional[str] = Field(default="NA")

class HealthcareProvider(BaseModel):
    name: str
    facility_type: str
    address: str
    contact: str
    operating_hours: str
    website: str
    accepted_insurances: list[str] = Field(default_factory=list)
    practitioners:    list[Practitioner] = Field(default_factory=list)
    affiliations: str
    summary: str
    rating: str

class HealthcareProviderBasic(BaseModel):
    practitioners: list[PractitionerBasic] = Field(default_factory=list)