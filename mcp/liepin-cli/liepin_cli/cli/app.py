import typer

from liepin_cli.cli.auth import app as auth_app
from liepin_cli.cli.help_localization import (
    LocalizedTyperGroup,
    apply_localized_command_cls,
)
from liepin_cli.cli.job import app as job_app
from liepin_cli.cli.resume import app as resume_app
from liepin_cli.cli.setup import setup
from liepin_cli.cli.skill import skill_app

app = typer.Typer(cls=LocalizedTyperGroup, help="猎聘简历与职位 CLI。")

app.command(help="首次配置或刷新登录状态。")(setup)
app.add_typer(auth_app, name="auth", help="管理认证。")
app.add_typer(resume_app, name="resume", help="查询或更新简历。")
app.add_typer(job_app, name="job", help="搜索职位、投递职位。")
app.add_typer(skill_app, name="skill", help="生成并安装 Agent Skill。")

apply_localized_command_cls(app)
