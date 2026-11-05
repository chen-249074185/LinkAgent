from __future__ import annotations

from typing import Annotated

import typer

from liepin_cli.cli.common import (
    BaseUrlOption,
    InputOption,
    OutputOption,
    TimeoutOption,
    TokenOption,
    execute_get,
    execute_post,
    exit_with_error,
)
from liepin_cli.cli.help_localization import (
    LocalizedTyperGroup,
    apply_localized_command_cls,
)
from liepin_cli.core.errors import LiepinCliError
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

app = typer.Typer(cls=LocalizedTyperGroup, help="简历查询与更新命令。")


@app.command("get", help="获取当前简历。")
def resume_get(
    token: str | None = TokenOption,
    base_url: str | None = BaseUrlOption,
    timeout: float | None = TimeoutOption,
    output: str | None = OutputOption,
) -> None:
    try:
        execute_get(
            "/mcp/get-resume",
            token=token,
            base_url=base_url,
            timeout=timeout,
            output=output,
        )
    except LiepinCliError as exc:
        exit_with_error(exc)


@app.command("update-base-info", help="更新基础资料。")
def update_base_info(
    input_path: InputOption = None,
    token: str | None = TokenOption,
    base_url: str | None = BaseUrlOption,
    timeout: float | None = TimeoutOption,
    output: str | None = OutputOption,
    real_name: Annotated[
        str | None, typer.Option("--real-name", help="姓名。")
    ] = None,
    sex: Annotated[str | None, typer.Option("--sex", help="性别。")] = None,
    birthday: Annotated[
        str | None, typer.Option("--birthday", help="生日，例如 19950101。")
    ] = None,
    city_code: Annotated[
        str | None, typer.Option("--city-code", help="当前所在城市代码。")
    ] = None,
    start_job: Annotated[
        str | None, typer.Option("--start-job", help="参加工作年份，例如 2020。")
    ] = None,
    start_job_month: Annotated[
        str | None,
        typer.Option("--start-job-month", help="参加工作月份，例如 06。"),
    ] = None,
    now_work_status: Annotated[
        str | None, typer.Option("--now-work-status", help="当前求职状态代码。")
    ] = None,
    now_salary: Annotated[
        int | None, typer.Option("--now-salary", help="当前月薪。")
    ] = None,
    now_months: Annotated[
        int | None, typer.Option("--now-months", help="当前年收入月数。")
    ] = None,
    now_salary_secret: Annotated[
        str | None, typer.Option("--now-salary-secret", help="是否隐藏当前薪资。")
    ] = None,
    job_name: Annotated[
        str | None, typer.Option("--job-name", help="当前职位名称。")
    ] = None,
    now_comp: Annotated[
        str | None, typer.Option("--now-comp", help="当前公司名称。")
    ] = None,
    now_indus_code: Annotated[
        str | None, typer.Option("--now-indus-code", help="当前行业代码。")
    ] = None,
    now_job_title_code: Annotated[
        str | None,
        typer.Option("--now-job-title-code", help="当前职能代码。"),
    ] = None,
    name_secret: Annotated[
        str | None, typer.Option("--name-secret", help="是否隐藏姓名。")
    ] = None,
    wechat: Annotated[
        str | None, typer.Option("--wechat", help="微信号。")
    ] = None,
    political_status_code: Annotated[
        str | None, typer.Option("--political-status-code", help="政治面貌代码。")
    ] = None,
) -> None:
    try:
        execute_post(
            "/mcp/update-base-info",
            token=token,
            base_url=base_url,
            timeout=timeout,
            output=output,
            model_cls=UpdateBaseInfoInput,
            input_path=input_path,
            overrides={
                "realName": real_name,
                "sex": sex,
                "birthday": birthday,
                "cityCode": city_code,
                "startJob": start_job,
                "startJobMonth": start_job_month,
                "nowWorkStatus": now_work_status,
                "nowSalary": now_salary,
                "nowMonths": now_months,
                "nowSalarySecret": now_salary_secret,
                "jobName": job_name,
                "nowComp": now_comp,
                "nowIndusCode": now_indus_code,
                "nowJobTitleCode": now_job_title_code,
                "nameSecret": name_secret,
                "wechat": wechat,
                "politicalStatusCode": political_status_code,
            },
        )
    except LiepinCliError as exc:
        exit_with_error(exc)


@app.command("update-self-assess", help="更新自我评价。")
def update_self_assess(
    input_path: InputOption = None,
    token: str | None = TokenOption,
    base_url: str | None = BaseUrlOption,
    timeout: float | None = TimeoutOption,
    output: str | None = OutputOption,
    self_assess: Annotated[
        str | None, typer.Option("--self-assess", help="自我评价内容。")
    ] = None,
) -> None:
    try:
        execute_post(
            "/mcp/update-self-assess",
            token=token,
            base_url=base_url,
            timeout=timeout,
            output=output,
            model_cls=UpdateSelfAssessInput,
            input_path=input_path,
            overrides={"selfAssess": self_assess},
        )
    except LiepinCliError as exc:
        exit_with_error(exc)


@app.command("add-edu-exp", help="新增教育经历。")
def add_edu_exp(
    input_path: InputOption = None,
    token: str | None = TokenOption,
    base_url: str | None = BaseUrlOption,
    timeout: float | None = TimeoutOption,
    output: str | None = OutputOption,
    school: Annotated[str | None, typer.Option("--school", help="学校名称。")] = None,
    major: Annotated[str | None, typer.Option("--major", help="专业名称。")] = None,
    start: Annotated[
        str | None, typer.Option("--start", help="开始时间，例如 201909。")
    ] = None,
    end: Annotated[
        str | None, typer.Option("--end", help="结束时间，例如 202306。")
    ] = None,
    degree: Annotated[str | None, typer.Option("--degree", help="学历代码。")] = None,
    tz: Annotated[str | None, typer.Option("--tz", help="是否统招。")] = None,
    experience: Annotated[
        str | None, typer.Option("--experience", help="在校经历说明。")
    ] = None,
) -> None:
    try:
        execute_post(
            "/mcp/add-edu-exp",
            token=token,
            base_url=base_url,
            timeout=timeout,
            output=output,
            model_cls=AddEduExpInput,
            input_path=input_path,
            overrides={
                "school": school,
                "major": major,
                "start": start,
                "end": end,
                "degree": degree,
                "tz": tz,
                "experience": experience,
            },
        )
    except LiepinCliError as exc:
        exit_with_error(exc)


@app.command("update-edu-exp", help="更新教育经历。")
def update_edu_exp(
    input_path: InputOption = None,
    token: str | None = TokenOption,
    base_url: str | None = BaseUrlOption,
    timeout: float | None = TimeoutOption,
    output: str | None = OutputOption,
    edu_id: Annotated[
        int | None, typer.Option("--edu-id", help="教育经历 ID。")
    ] = None,
    school: Annotated[str | None, typer.Option("--school", help="学校名称。")] = None,
    major: Annotated[str | None, typer.Option("--major", help="专业名称。")] = None,
    start: Annotated[
        str | None, typer.Option("--start", help="开始时间，例如 201909。")
    ] = None,
    end: Annotated[
        str | None, typer.Option("--end", help="结束时间，例如 202306。")
    ] = None,
    degree: Annotated[str | None, typer.Option("--degree", help="学历代码。")] = None,
    tz: Annotated[str | None, typer.Option("--tz", help="是否统招。")] = None,
    experience: Annotated[
        str | None, typer.Option("--experience", help="在校经历说明。")
    ] = None,
) -> None:
    try:
        execute_post(
            "/mcp/update-edu-exp",
            token=token,
            base_url=base_url,
            timeout=timeout,
            output=output,
            model_cls=UpdateEduExpInput,
            input_path=input_path,
            overrides={
                "eduId": edu_id,
                "school": school,
                "major": major,
                "start": start,
                "end": end,
                "degree": degree,
                "tz": tz,
                "experience": experience,
            },
        )
    except LiepinCliError as exc:
        exit_with_error(exc)


@app.command("add-work-exp", help="新增工作经历。")
def add_work_exp(
    input_path: InputOption = None,
    token: str | None = TokenOption,
    base_url: str | None = BaseUrlOption,
    timeout: float | None = TimeoutOption,
    output: str | None = OutputOption,
    comp_name: Annotated[
        str | None, typer.Option("--comp-name", help="公司名称。")
    ] = None,
    industry: Annotated[
        str | None, typer.Option("--industry", help="所属行业。")
    ] = None,
    work_start: Annotated[
        str | None, typer.Option("--work-start", help="开始时间，例如 202301。")
    ] = None,
    work_end: Annotated[
        str | None, typer.Option("--work-end", help="结束时间，例如 202402。")
    ] = None,
    rw_title: Annotated[
        str | None, typer.Option("--rw-title", help="职位名称。")
    ] = None,
    jobtitle: Annotated[
        str | None, typer.Option("--jobtitle", help="职能名称。")
    ] = None,
    dq: Annotated[str | None, typer.Option("--dq", help="工作地点。")] = None,
    dept: Annotated[str | None, typer.Option("--dept", help="所属部门。")] = None,
    report: Annotated[
        str | None, typer.Option("--report", help="汇报对象。")
    ] = None,
    subordinate: Annotated[
        int | None, typer.Option("--subordinate", help="下属人数。")
    ] = None,
    duty: Annotated[str | None, typer.Option("--duty", help="工作职责。")] = None,
    months: Annotated[int | None, typer.Option("--months", help="薪资月数。")] = None,
    salary: Annotated[int | None, typer.Option("--salary", help="月薪。")] = None,
    compkind: Annotated[
        str | None, typer.Option("--compkind", help="公司性质。")
    ] = None,
    compscale: Annotated[
        str | None, typer.Option("--compscale", help="公司规模。")
    ] = None,
    labels: Annotated[str | None, typer.Option("--labels", help="公司标签。")] = None,
    work_type: Annotated[
        int | None, typer.Option("--work-type", help="工作类型。")
    ] = None,
    shield_comp: Annotated[
        bool | None,
        typer.Option("--shield-comp/--no-shield-comp", help="是否屏蔽公司。"),
    ] = None,
) -> None:
    try:
        execute_post(
            "/mcp/add-work-exp",
            token=token,
            base_url=base_url,
            timeout=timeout,
            output=output,
            model_cls=AddWorkExpInput,
            input_path=input_path,
            overrides={
                "compName": comp_name,
                "industry": industry,
                "workStart": work_start,
                "workEnd": work_end,
                "rwTitle": rw_title,
                "jobtitle": jobtitle,
                "dq": dq,
                "dept": dept,
                "report": report,
                "subordinate": subordinate,
                "duty": duty,
                "months": months,
                "salary": salary,
                "compkind": compkind,
                "compscale": compscale,
                "labels": labels,
                "workType": work_type,
                "shieldComp": shield_comp,
            },
        )
    except LiepinCliError as exc:
        exit_with_error(exc)


@app.command("update-work-exp", help="更新工作经历。")
def update_work_exp(
    input_path: InputOption = None,
    token: str | None = TokenOption,
    base_url: str | None = BaseUrlOption,
    timeout: float | None = TimeoutOption,
    output: str | None = OutputOption,
    work_id: Annotated[
        int | None, typer.Option("--work-id", help="工作经历 ID。")
    ] = None,
    comp_name: Annotated[str | None, typer.Option("--comp-name", help="公司名称。")] = None,
    industry: Annotated[str | None, typer.Option("--industry", help="所属行业。")] = None,
    work_start: Annotated[
        str | None, typer.Option("--work-start", help="开始时间，例如 202301。")
    ] = None,
    work_end: Annotated[
        str | None, typer.Option("--work-end", help="结束时间，例如 202402。")
    ] = None,
    rw_title: Annotated[str | None, typer.Option("--rw-title", help="职位名称。")] = None,
    jobtitle: Annotated[str | None, typer.Option("--jobtitle", help="职能名称。")] = None,
    dq: Annotated[str | None, typer.Option("--dq", help="工作地点。")] = None,
    dept: Annotated[str | None, typer.Option("--dept", help="所属部门。")] = None,
    report: Annotated[str | None, typer.Option("--report", help="汇报对象。")] = None,
    subordinate: Annotated[
        int | None, typer.Option("--subordinate", help="下属人数。")
    ] = None,
    duty: Annotated[str | None, typer.Option("--duty", help="工作职责。")] = None,
    months: Annotated[int | None, typer.Option("--months", help="薪资月数。")] = None,
    salary: Annotated[int | None, typer.Option("--salary", help="月薪。")] = None,
    compkind: Annotated[str | None, typer.Option("--compkind", help="公司性质。")] = None,
    compscale: Annotated[str | None, typer.Option("--compscale", help="公司规模。")] = None,
    labels: Annotated[str | None, typer.Option("--labels", help="公司标签。")] = None,
    work_type: Annotated[int | None, typer.Option("--work-type", help="工作类型。")] = None,
    shield_comp: Annotated[
        bool | None,
        typer.Option("--shield-comp/--no-shield-comp", help="是否屏蔽公司。"),
    ] = None,
) -> None:
    try:
        execute_post(
            "/mcp/update-work-exp",
            token=token,
            base_url=base_url,
            timeout=timeout,
            output=output,
            model_cls=UpdateWorkExpInput,
            input_path=input_path,
            overrides={
                "workId": work_id,
                "compName": comp_name,
                "industry": industry,
                "workStart": work_start,
                "workEnd": work_end,
                "rwTitle": rw_title,
                "jobtitle": jobtitle,
                "dq": dq,
                "dept": dept,
                "report": report,
                "subordinate": subordinate,
                "duty": duty,
                "months": months,
                "salary": salary,
                "compkind": compkind,
                "compscale": compscale,
                "labels": labels,
                "workType": work_type,
                "shieldComp": shield_comp,
            },
        )
    except LiepinCliError as exc:
        exit_with_error(exc)


@app.command("add-project-exp", help="新增项目经历。")
def add_project_exp(
    input_path: InputOption = None,
    token: str | None = TokenOption,
    base_url: str | None = BaseUrlOption,
    timeout: float | None = TimeoutOption,
    output: str | None = OutputOption,
    name: Annotated[str | None, typer.Option("--name", help="项目名称。")] = None,
    start: Annotated[
        str | None, typer.Option("--start", help="开始时间，例如 202301。")
    ] = None,
    end: Annotated[
        str | None, typer.Option("--end", help="结束时间，例如 202312。")
    ] = None,
    comp_name: Annotated[
        str | None, typer.Option("--comp-name", help="所属公司名称。")
    ] = None,
    position: Annotated[
        str | None, typer.Option("--position", help="担任角色。")
    ] = None,
    descr: Annotated[str | None, typer.Option("--descr", help="项目描述。")] = None,
    duty: Annotated[str | None, typer.Option("--duty", help="职责说明。")] = None,
    achievement: Annotated[
        str | None, typer.Option("--achievement", help="项目成果。")
    ] = None,
) -> None:
    try:
        execute_post(
            "/mcp/add-project-exp",
            token=token,
            base_url=base_url,
            timeout=timeout,
            output=output,
            model_cls=AddProjectExpInput,
            input_path=input_path,
            overrides={
                "name": name,
                "start": start,
                "end": end,
                "compName": comp_name,
                "position": position,
                "descr": descr,
                "duty": duty,
                "achievement": achievement,
            },
        )
    except LiepinCliError as exc:
        exit_with_error(exc)


@app.command("update-project-exp", help="更新项目经历。")
def update_project_exp(
    input_path: InputOption = None,
    token: str | None = TokenOption,
    base_url: str | None = BaseUrlOption,
    timeout: float | None = TimeoutOption,
    output: str | None = OutputOption,
    exp_id: Annotated[int | None, typer.Option("--id", help="项目经历 ID。")] = None,
    name: Annotated[str | None, typer.Option("--name", help="项目名称。")] = None,
    start: Annotated[
        str | None, typer.Option("--start", help="开始时间，例如 202301。")
    ] = None,
    end: Annotated[
        str | None, typer.Option("--end", help="结束时间，例如 202312。")
    ] = None,
    comp_name: Annotated[str | None, typer.Option("--comp-name", help="所属公司名称。")] = None,
    position: Annotated[str | None, typer.Option("--position", help="担任角色。")] = None,
    descr: Annotated[str | None, typer.Option("--descr", help="项目描述。")] = None,
    duty: Annotated[str | None, typer.Option("--duty", help="职责说明。")] = None,
    achievement: Annotated[
        str | None, typer.Option("--achievement", help="项目成果。")
    ] = None,
) -> None:
    try:
        execute_post(
            "/mcp/update-project-exp",
            token=token,
            base_url=base_url,
            timeout=timeout,
            output=output,
            model_cls=UpdateProjectExpInput,
            input_path=input_path,
            overrides={
                "id": exp_id,
                "name": name,
                "start": start,
                "end": end,
                "compName": comp_name,
                "position": position,
                "descr": descr,
                "duty": duty,
                "achievement": achievement,
            },
        )
    except LiepinCliError as exc:
        exit_with_error(exc)


@app.command("add-job-want", help="新增求职期望。")
def add_job_want(
    input_path: InputOption = None,
    token: str | None = TokenOption,
    base_url: str | None = BaseUrlOption,
    timeout: float | None = TimeoutOption,
    output: str | None = OutputOption,
    jobtitle: Annotated[
        str | None, typer.Option("--jobtitle", help="期望职位名称。")
    ] = None,
    dq: Annotated[str | None, typer.Option("--dq", help="期望工作地点。")] = None,
    industries: Annotated[
        list[str] | None,
        typer.Option("--industries", help="期望行业。"),
    ] = None,
    other_expect_dqs: Annotated[
        list[str] | None,
        typer.Option("--other-expect-dqs", help="其他期望地点。"),
    ] = None,
    want_salary_low: Annotated[
        int | None, typer.Option("--want-salary-low", help="期望最低薪资。")
    ] = None,
    want_salary_high: Annotated[
        int | None, typer.Option("--want-salary-high", help="期望最高薪资。")
    ] = None,
    want_salary_months: Annotated[
        int | None, typer.Option("--want-salary-months", help="期望年收入月数。")
    ] = None,
    work_type: Annotated[
        str | None, typer.Option("--work-type", help="工作类型。")
    ] = None,
    workweek: Annotated[
        int | None, typer.Option("--workweek", help="每周工作天数。")
    ] = None,
    practice_months: Annotated[
        int | None, typer.Option("--practice-months", help="实习月数。")
    ] = None,
) -> None:
    try:
        execute_post(
            "/mcp/add-job-want",
            token=token,
            base_url=base_url,
            timeout=timeout,
            output=output,
            model_cls=AddJobWantInput,
            input_path=input_path,
            overrides={
                "jobtitle": jobtitle,
                "dq": dq,
                "industries": industries,
                "otherExpectDqs": other_expect_dqs,
                "wantSalaryLow": want_salary_low,
                "wantSalaryHigh": want_salary_high,
                "wantSalaryMonths": want_salary_months,
                "workType": work_type,
                "workweek": workweek,
                "practiceMonths": practice_months,
            },
        )
    except LiepinCliError as exc:
        exit_with_error(exc)


@app.command("update-job-want", help="更新求职期望。")
def update_job_want(
    input_path: InputOption = None,
    token: str | None = TokenOption,
    base_url: str | None = BaseUrlOption,
    timeout: float | None = TimeoutOption,
    output: str | None = OutputOption,
    want_id: Annotated[int | None, typer.Option("--id", help="求职期望 ID。")] = None,
    jobtitle: Annotated[str | None, typer.Option("--jobtitle", help="期望职位名称。")] = None,
    dq: Annotated[str | None, typer.Option("--dq", help="期望工作地点。")] = None,
    industries: Annotated[
        list[str] | None,
        typer.Option("--industries", help="期望行业。"),
    ] = None,
    other_expect_dqs: Annotated[
        list[str] | None,
        typer.Option("--other-expect-dqs", help="其他期望地点。"),
    ] = None,
    want_salary_low: Annotated[
        int | None, typer.Option("--want-salary-low", help="期望最低薪资。")
    ] = None,
    want_salary_high: Annotated[
        int | None, typer.Option("--want-salary-high", help="期望最高薪资。")
    ] = None,
    want_salary_months: Annotated[
        int | None, typer.Option("--want-salary-months", help="期望年收入月数。")
    ] = None,
    work_type: Annotated[
        str | None, typer.Option("--work-type", help="工作类型。")
    ] = None,
    workweek: Annotated[
        int | None, typer.Option("--workweek", help="每周工作天数。")
    ] = None,
    practice_months: Annotated[
        int | None, typer.Option("--practice-months", help="实习月数。")
    ] = None,
) -> None:
    try:
        execute_post(
            "/mcp/update-job-want",
            token=token,
            base_url=base_url,
            timeout=timeout,
            output=output,
            model_cls=UpdateJobWantInput,
            input_path=input_path,
            overrides={
                "id": want_id,
                "jobtitle": jobtitle,
                "dq": dq,
                "industries": industries,
                "otherExpectDqs": other_expect_dqs,
                "wantSalaryLow": want_salary_low,
                "wantSalaryHigh": want_salary_high,
                "wantSalaryMonths": want_salary_months,
                "workType": work_type,
                "workweek": workweek,
                "practiceMonths": practice_months,
            },
        )
    except LiepinCliError as exc:
        exit_with_error(exc)


apply_localized_command_cls(app)
