from __future__ import annotations

from liepin_cli.models.job import ApplyJobInput, SearchJobInput
from liepin_cli.models.resume import (
    AddEduExpInput,
    AddJobWantInput,
    AddProjectExpInput,
    AddWorkExpInput,
    UpdateBaseInfoInput,
    UpdateEduExpInput,
    UpdateJobWantInput,
    UpdateProjectExpInput,
    UpdateSelfAssessInput,
    UpdateWorkExpInput,
)


SCHEMA_MODEL_REGISTRY = {
    "add-edu-exp-input.json": AddEduExpInput,
    "add-job-want-input.json": AddJobWantInput,
    "add-project-exp-input.json": AddProjectExpInput,
    "add-work-exp-input.json": AddWorkExpInput,
    "apply-job-input.json": ApplyJobInput,
    "search-job-input.json": SearchJobInput,
    "update-base-info-input.json": UpdateBaseInfoInput,
    "update-edu-exp-input.json": UpdateEduExpInput,
    "update-job-want-input.json": UpdateJobWantInput,
    "update-project-exp-input.json": UpdateProjectExpInput,
    "update-self-assess-input.json": UpdateSelfAssessInput,
    "update-work-exp-input.json": UpdateWorkExpInput,
}
