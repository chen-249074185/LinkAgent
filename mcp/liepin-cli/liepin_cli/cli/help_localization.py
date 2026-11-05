from __future__ import annotations

from contextlib import contextmanager

import typer
import typer.rich_utils as rich_utils
from typer.core import TyperCommand, TyperGroup

_HELP_TEXT_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("Show this message and exit.", "显示帮助信息并退出。"),
    ("Install completion for the current shell.", "为当前 shell 安装补全。"),
    (
        "Show completion for the current shell, to copy it or customize the installation.",
        "显示当前 shell 的补全脚本，便于复制或自定义安装。",
    ),
    ("Usage:", "用法："),
    ("Options", "选项"),
    ("Commands", "命令"),
    ("Arguments", "参数"),
    ("[OPTIONS]", "[选项]"),
    ("COMMAND [ARGS]...", "命令 [参数]..."),
    ("[ARGS]...", "[参数]..."),
)

_HIDDEN_HELP_OPTION_NAMES = {
    "--help",
    "--install-completion",
    "--show-completion",
    "--token",
    "--input",
    "--base-url",
    "--timeout",
    "--output",
}


def localize_help_text(help_text: str) -> str:
    localized = help_text
    for source, target in _HELP_TEXT_REPLACEMENTS:
        localized = localized.replace(source, target)
    return localized


@contextmanager
def localized_rich_panels():
    original_options = rich_utils.OPTIONS_PANEL_TITLE
    original_commands = rich_utils.COMMANDS_PANEL_TITLE
    original_arguments = rich_utils.ARGUMENTS_PANEL_TITLE
    rich_utils.OPTIONS_PANEL_TITLE = "选项"
    rich_utils.COMMANDS_PANEL_TITLE = "命令"
    rich_utils.ARGUMENTS_PANEL_TITLE = "参数"
    try:
        yield
    finally:
        rich_utils.OPTIONS_PANEL_TITLE = original_options
        rich_utils.COMMANDS_PANEL_TITLE = original_commands
        rich_utils.ARGUMENTS_PANEL_TITLE = original_arguments


class LocalizedHelpMixin:
    @staticmethod
    def _should_hide_param(param) -> bool:
        option_names = {
            *getattr(param, "opts", ()),
            *getattr(param, "secondary_opts", ()),
        }
        return bool(option_names & _HIDDEN_HELP_OPTION_NAMES)

    def format_help(self, ctx, formatter) -> None:
        with localized_rich_panels():
            return super().format_help(ctx, formatter)

    def get_usage(self, ctx: typer.Context) -> str:
        return localize_help_text(super().get_usage(ctx))

    def get_help(self, ctx: typer.Context) -> str:
        return localize_help_text(super().get_help(ctx))

    def get_help_option(self, ctx: typer.Context):
        option = super().get_help_option(ctx)
        if option and option.help:
            option.help = localize_help_text(option.help)
        if option:
            option.hidden = True
        return option

    def get_params(self, ctx: typer.Context):
        params = super().get_params(ctx)
        for param in params:
            help_text = getattr(param, "help", None)
            if help_text:
                param.help = localize_help_text(help_text)
            if self._should_hide_param(param):
                param.hidden = True
        return params


class LocalizedTyperGroup(LocalizedHelpMixin, TyperGroup):
    pass


class LocalizedTyperCommand(LocalizedHelpMixin, TyperCommand):
    pass


def apply_localized_command_cls(app: typer.Typer) -> None:
    for command_info in app.registered_commands:
        command_info.cls = LocalizedTyperCommand
