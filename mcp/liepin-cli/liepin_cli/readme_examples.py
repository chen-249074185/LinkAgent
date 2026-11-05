from __future__ import annotations

import shlex
from pathlib import Path


def _readme_text(readme_path: str) -> str:
    return Path(readme_path).read_text(encoding="utf-8")


def _extract_fenced_block_after_marker(
    readme_path: str, marker: str, fence_type: str
) -> str:
    content = _readme_text(readme_path)
    marker_index = content.index(marker)
    fence_start = content.index(f"```{fence_type}", marker_index)
    block_start = fence_start + len(f"```{fence_type}\n")
    fence_end = content.index("\n```", block_start)
    return content[block_start:fence_end]


def extract_fenced_block_after_label(readme_path: str, label: str, fence_type: str) -> str:
    return _extract_fenced_block_after_marker(readme_path, label, fence_type)


def extract_shell_commands_after_marker(readme_path: str, marker: str) -> list[list[str]]:
    block = _extract_fenced_block_after_marker(readme_path, marker, "bash")
    commands: list[list[str]] = []
    current_parts: list[str] = []

    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            if current_parts:
                commands.append(_parse_shell_command(current_parts))
                current_parts = []
            continue

        if line.endswith("\\"):
            current_parts.append(line[:-1].rstrip())
            continue

        current_parts.append(line)
        commands.append(_parse_shell_command(current_parts))
        current_parts = []

    if current_parts:
        commands.append(_parse_shell_command(current_parts))

    return commands


def _parse_shell_command(parts: list[str]) -> list[str]:
    command = " ".join(parts).strip()
    if command.startswith("liepin-cli "):
        command = command[len("liepin-cli ") :]
    return shlex.split(command)
