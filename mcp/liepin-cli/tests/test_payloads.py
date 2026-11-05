import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from liepin_cli.core.errors import InvalidInputError
from liepin_cli.core.payloads import load_payload_file, merge_payload
from liepin_cli.models.job import ApplyJobInput, SearchJobInput
from liepin_cli.models.resume import (
    AddEduExpInput,
    AddJobWantInput,
    AddProjectExpInput,
    AddWorkExpInput,
    UpdateBaseInfoInput,
)


def test_load_payload_file_reads_json(tmp_path: Path) -> None:
    path = tmp_path / "payload.json"
    path.write_text(json.dumps({"jobId": 12, "jobKind": "2"}), encoding="utf-8")

    assert load_payload_file(path) == {"jobId": 12, "jobKind": "2"}


def test_load_payload_file_none_returns_empty_dict() -> None:
    assert load_payload_file(None) == {}


def test_load_payload_file_missing_raises_invalid_input(tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    with pytest.raises(InvalidInputError):
        load_payload_file(missing)


def test_load_payload_file_invalid_json_raises_invalid_input(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(InvalidInputError):
        load_payload_file(path)


def test_load_payload_file_non_object_json_root_raises_invalid_input(tmp_path: Path) -> None:
    path = tmp_path / "array.json"
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(InvalidInputError, match="JSON 顶层必须是对象"):
        load_payload_file(path)


def test_load_payload_file_non_utf8_raises_invalid_input(tmp_path: Path) -> None:
    path = tmp_path / "bad-encoding.json"
    path.write_bytes(b"\xff\xfe\x00\x00")
    with pytest.raises(InvalidInputError, match="无法读取输入文件"):
        load_payload_file(path)


def test_merge_payload_prefers_explicit_flags() -> None:
    merged = merge_payload(
        {"jobId": 12, "jobKind": "2"},
        {"jobKind": "1", "unused": None},
    )

    assert merged == {"jobId": 12, "jobKind": "1"}


def test_merge_payload_strips_none_values() -> None:
    merged = merge_payload({"a": 1, "b": None}, {"c": 2})
    assert merged == {"a": 1, "c": 2}


def test_apply_job_model_requires_job_id_and_kind() -> None:
    with pytest.raises(ValidationError):
        ApplyJobInput.model_validate({})


def test_apply_job_model_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ApplyJobInput.model_validate({"jobId": 1, "jobKind": "2", "job_id": 1})


def test_apply_job_model_rejects_invalid_job_kind_values() -> None:
    with pytest.raises(ValidationError):
        ApplyJobInput.model_validate({"jobId": 1, "jobKind": "social"})

    with pytest.raises(ValidationError):
        ApplyJobInput.model_validate({"jobId": 1, "jobKind": "3"})


def test_update_base_info_requires_start_job_pair() -> None:
    with pytest.raises(ValidationError, match="必须同时提供"):
        UpdateBaseInfoInput.model_validate({"startJob": "2020"})

    with pytest.raises(ValidationError, match="必须同时提供"):
        UpdateBaseInfoInput.model_validate({"startJobMonth": "06"})


def test_update_base_info_rejects_invalid_enum_values() -> None:
    with pytest.raises(ValidationError):
        UpdateBaseInfoInput.model_validate({"sex": "未知"})

    with pytest.raises(ValidationError):
        UpdateBaseInfoInput.model_validate({"nowWorkStatus": "9"})

    with pytest.raises(ValidationError):
        UpdateBaseInfoInput.model_validate({"nameSecret": "2"})


def test_add_edu_exp_rejects_invalid_enum_values() -> None:
    with pytest.raises(ValidationError):
        AddEduExpInput.model_validate(
            {"school": "北大", "start": "201909", "end": "202306", "degree": "999"}
        )

    with pytest.raises(ValidationError):
        AddEduExpInput.model_validate(
            {
                "school": "北大",
                "start": "201909",
                "end": "202306",
                "degree": "040",
                "tz": "2",
            }
        )


def test_add_work_exp_rejects_invalid_work_type() -> None:
    with pytest.raises(ValidationError):
        AddWorkExpInput.model_validate(
            {
                "compName": "猎聘",
                "rwTitle": "后端工程师",
                "workStart": "202301",
                "workEnd": "202402",
                "workType": 3,
            }
        )


def test_add_job_want_rejects_invalid_work_type() -> None:
    with pytest.raises(ValidationError):
        AddJobWantInput.model_validate(
            {"jobtitle": "Java", "dq": "上海", "workType": "2"}
        )


def test_update_base_info_rejects_invalid_date_formats() -> None:
    with pytest.raises(ValidationError):
        UpdateBaseInfoInput.model_validate({"birthday": "1990-01-01"})

    with pytest.raises(ValidationError):
        UpdateBaseInfoInput.model_validate({"startJob": "20"})

    with pytest.raises(ValidationError):
        UpdateBaseInfoInput.model_validate(
            {"startJob": "2020", "startJobMonth": "13"}
        )


def test_add_edu_exp_rejects_invalid_yyyymm_dates() -> None:
    with pytest.raises(ValidationError):
        AddEduExpInput.model_validate(
            {"school": "北大", "start": "2019-09", "end": "202306", "degree": "040"}
        )

    with pytest.raises(ValidationError):
        AddEduExpInput.model_validate(
            {"school": "北大", "start": "201909", "end": "202313", "degree": "040"}
        )


def test_add_work_exp_rejects_invalid_yyyymm_dates() -> None:
    with pytest.raises(ValidationError):
        AddWorkExpInput.model_validate(
            {
                "compName": "猎聘",
                "rwTitle": "后端工程师",
                "workStart": "20231",
                "workEnd": "202402",
            }
        )

    with pytest.raises(ValidationError):
        AddWorkExpInput.model_validate(
            {
                "compName": "猎聘",
                "rwTitle": "后端工程师",
                "workStart": "202301",
                "workEnd": "202400",
            }
        )


def test_add_project_exp_rejects_invalid_yyyymm_dates() -> None:
    with pytest.raises(ValidationError):
        AddProjectExpInput.model_validate(
            {"name": "推荐系统", "start": "2023/01", "end": "202312"}
        )

    with pytest.raises(ValidationError):
        AddProjectExpInput.model_validate(
            {"name": "推荐系统", "start": "202301", "end": "202313"}
        )


def test_search_job_rejects_negative_page() -> None:
    with pytest.raises(ValidationError):
        SearchJobInput.model_validate({"page": -1})


def test_update_base_info_rejects_negative_salary_fields() -> None:
    with pytest.raises(ValidationError):
        UpdateBaseInfoInput.model_validate({"nowSalary": -1})

    with pytest.raises(ValidationError):
        UpdateBaseInfoInput.model_validate({"nowMonths": -1})


def test_add_work_exp_rejects_negative_numeric_fields() -> None:
    with pytest.raises(ValidationError):
        AddWorkExpInput.model_validate(
            {
                "compName": "猎聘",
                "rwTitle": "后端工程师",
                "workStart": "202301",
                "workEnd": "202402",
                "subordinate": -1,
            }
        )

    with pytest.raises(ValidationError):
        AddWorkExpInput.model_validate(
            {
                "compName": "猎聘",
                "rwTitle": "后端工程师",
                "workStart": "202301",
                "workEnd": "202402",
                "months": -1,
            }
        )

    with pytest.raises(ValidationError):
        AddWorkExpInput.model_validate(
            {
                "compName": "猎聘",
                "rwTitle": "后端工程师",
                "workStart": "202301",
                "workEnd": "202402",
                "salary": -1,
            }
        )


def test_add_job_want_rejects_negative_numeric_fields() -> None:
    with pytest.raises(ValidationError):
        AddJobWantInput.model_validate(
            {"jobtitle": "Java", "dq": "上海", "wantSalaryLow": -1}
        )

    with pytest.raises(ValidationError):
        AddJobWantInput.model_validate(
            {"jobtitle": "Java", "dq": "上海", "wantSalaryHigh": -1}
        )

    with pytest.raises(ValidationError):
        AddJobWantInput.model_validate(
            {"jobtitle": "Java", "dq": "上海", "wantSalaryMonths": -1}
        )

    with pytest.raises(ValidationError):
        AddJobWantInput.model_validate(
            {"jobtitle": "Java", "dq": "上海", "practiceMonths": -1}
        )


def test_add_job_want_rejects_inverted_salary_range() -> None:
    with pytest.raises(ValidationError, match="不能大于"):
        AddJobWantInput.model_validate(
            {
                "jobtitle": "Java",
                "dq": "上海",
                "wantSalaryLow": 30000,
                "wantSalaryHigh": 20000,
            }
        )
