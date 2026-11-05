from __future__ import annotations

from typing import Annotated

import typer

from liepin_cli.cli.common import (
    BaseUrlOption,
    InputOption,
    OutputOption,
    TimeoutOption,
    TokenOption,
    execute_post,
    exit_with_error,
)
from liepin_cli.cli.help_localization import (
    LocalizedTyperGroup,
    apply_localized_command_cls,
)
from liepin_cli.core.errors import LiepinCliError
from liepin_cli.models.job import ApplyJobInput, SearchJobInput

app = typer.Typer(cls=LocalizedTyperGroup, help="职位搜索与投递命令。")


@app.command("search", help="搜索职位。")
def job_search(
    input_path: InputOption = None,
    token: str | None = TokenOption,
    base_url: str | None = BaseUrlOption,
    timeout: float | None = TimeoutOption,
    output: str | None = OutputOption,
    work_experience: Annotated[
        str | None, typer.Option("--work-experience", help="工作经验要求。")
    ] = None,
    edu_level: Annotated[
        str | None, typer.Option("--edu-level", help="学历要求。")
    ] = None,
    comp_nature: Annotated[
        str | None, typer.Option("--comp-nature", help="公司性质或类型。")
    ] = None,
    address: Annotated[
        str | None, typer.Option("--address", help="工作地点。")
    ] = None,
    salary_floor: Annotated[
        str | None, typer.Option("--salary-floor", help="最低薪资。")
    ] = None,
    salary_cap: Annotated[
        str | None, typer.Option("--salary-cap", help="最高薪资。")
    ] = None,
    salary_kind: Annotated[
        str | None, typer.Option("--salary-kind", help="薪资类型。")
    ] = None,
    job_name: Annotated[
        str | None, typer.Option("--job-name", help="职位关键词。")
    ] = None,
    company_name: Annotated[
        str | None, typer.Option("--company-name", help="公司名称。")
    ] = None,
    page: Annotated[
        int | None, typer.Option("--page", help="结果页码，首页通常为 0。")
    ] = None,
) -> None:
    try:
        execute_post(
            "/mcp/search-job",
            token=token,
            base_url=base_url,
            timeout=timeout,
            output=output,
            model_cls=SearchJobInput,
            input_path=input_path,
            overrides={
                "workExperience": work_experience,
                "eduLevel": edu_level,
                "compNature": comp_nature,
                "address": address,
                "salaryFloor": salary_floor,
                "salaryCap": salary_cap,
                "salaryKind": salary_kind,
                "jobName": job_name,
                "companyName": company_name,
                "page": page,
            },
        )
    except LiepinCliError as exc:
        exit_with_error(exc)


@app.command("apply", help="投递职位。")
def job_apply(
    input_path: InputOption = None,
    token: str | None = TokenOption,
    base_url: str | None = BaseUrlOption,
    timeout: float | None = TimeoutOption,
    output: str | None = OutputOption,
    job_id: Annotated[
        int | None, typer.Option("--job-id", help="职位 ID。必填。")
    ] = None,
    job_kind: Annotated[
        str | None,
        typer.Option(
            "--job-kind",
            help="职位类型编号，例如 1 或 2。必填；可直接复用职位搜索结果中的类型值。",
        ),
    ] = None,
) -> None:
    try:
        execute_post(
            "/mcp/apply-job",
            token=token,
            base_url=base_url,
            timeout=timeout,
            output=output,
            model_cls=ApplyJobInput,
            input_path=input_path,
            overrides={
                "jobId": job_id,
                "jobKind": job_kind,
            },
        )
    except LiepinCliError as exc:
        exit_with_error(exc)


apply_localized_command_cls(app)
