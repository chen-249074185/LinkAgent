from __future__ import annotations

from typing import Literal

from liepin_cli.models.base import NonNegativeInt, SchemaModel


class SearchJobInput(SchemaModel):
    workExperience: str | None = None
    eduLevel: str | None = None
    compNature: str | None = None
    address: str | None = None
    salaryFloor: str | None = None
    salaryCap: str | None = None
    salaryKind: str | None = None
    jobName: str | None = None
    companyName: str | None = None
    page: NonNegativeInt | None = None


class ApplyJobInput(SchemaModel):
    jobId: int
    jobKind: Literal["1", "2"]
