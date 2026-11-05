from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from liepin_cli.models.base import (
    DateYmd,
    Month2,
    NonNegativeInt,
    SchemaModel,
    Year4,
    YearMonth,
)


class UpdateBaseInfoInput(SchemaModel):
    realName: str | None = None
    sex: Literal["男", "女"] | None = None
    birthday: DateYmd | None = None
    cityCode: str | None = None
    startJob: Year4 | None = None
    startJobMonth: Month2 | None = None
    nowWorkStatus: Literal["0", "1", "2", "3", "4", "5", "6", "7"] | None = None
    nowSalary: NonNegativeInt | None = None
    nowMonths: NonNegativeInt | None = None
    nowSalarySecret: Literal["0", "1"] | None = None
    jobName: str | None = None
    nowComp: str | None = None
    nowIndusCode: str | None = None
    nowJobTitleCode: str | None = None
    nameSecret: Literal["0", "1"] | None = None
    wechat: str | None = None
    politicalStatusCode: Literal["1", "2", "3", "4", "5", "6"] | None = None

    @model_validator(mode="after")
    def validate_start_job_pair(self) -> "UpdateBaseInfoInput":
        has_start_job = self.startJob is not None
        has_start_job_month = self.startJobMonth is not None
        if has_start_job != has_start_job_month:
            raise ValueError("`startJob` 和 `startJobMonth` 必须同时提供")
        return self


class UpdateSelfAssessInput(SchemaModel):
    selfAssess: str


class AddEduExpInput(SchemaModel):
    school: str
    major: str | None = None
    start: YearMonth
    end: YearMonth
    degree: Literal["090", "080", "060", "050", "040", "030", "020", "010"]
    tz: Literal["0", "1"] | None = None
    experience: str | None = None


class UpdateEduExpInput(AddEduExpInput):
    eduId: int
    school: str | None = None
    start: YearMonth | None = None
    end: YearMonth | None = None
    degree: Literal["090", "080", "060", "050", "040", "030", "020", "010"] | None = None


class AddWorkExpInput(SchemaModel):
    compName: str
    industry: str | None = None
    workStart: YearMonth
    workEnd: YearMonth
    rwTitle: str
    jobtitle: str | None = None
    dq: str | None = None
    dept: str | None = None
    report: str | None = None
    subordinate: NonNegativeInt | None = None
    duty: str | None = None
    months: NonNegativeInt | None = None
    salary: NonNegativeInt | None = None
    compkind: str | None = None
    compscale: str | None = None
    shieldComp: bool | None = None
    labels: str | None = None
    workType: Literal[1, 2] | None = None


class UpdateWorkExpInput(AddWorkExpInput):
    workId: int
    compName: str | None = None
    workStart: YearMonth | None = None
    workEnd: YearMonth | None = None
    rwTitle: str | None = None


class AddProjectExpInput(SchemaModel):
    name: str
    start: YearMonth
    end: YearMonth
    compName: str | None = None
    position: str | None = None
    descr: str | None = None
    duty: str | None = None
    achievement: str | None = None


class UpdateProjectExpInput(AddProjectExpInput):
    id: int
    name: str | None = None
    start: YearMonth | None = None
    end: YearMonth | None = None


class AddJobWantInput(SchemaModel):
    industries: list[str] | None = None
    jobtitle: str
    dq: str
    wantSalaryLow: NonNegativeInt | None = None
    wantSalaryHigh: NonNegativeInt | None = None
    wantSalaryMonths: NonNegativeInt | None = None
    workType: Literal["0", "1"] | None = None
    otherExpectDqs: list[str] | None = None
    workweek: int | None = None
    practiceMonths: NonNegativeInt | None = None

    @model_validator(mode="after")
    def validate_salary_range(self) -> "AddJobWantInput":
        if (
            self.wantSalaryLow is not None
            and self.wantSalaryHigh is not None
            and self.wantSalaryLow > self.wantSalaryHigh
        ):
            raise ValueError("`wantSalaryLow` 不能大于 `wantSalaryHigh`")
        return self


class UpdateJobWantInput(AddJobWantInput):
    id: int
    jobtitle: str | None = None
    dq: str | None = None
