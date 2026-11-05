import json
from pathlib import Path

from liepin_cli.skill_distribution import (
    build_distribution_bundle,
    build_repo_skills_dir_files,
    install_skill,
    write_distribution_bundle,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _relative_files(root: Path) -> list[str]:
    return sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
    )


def test_build_distribution_bundle_contains_expected_files() -> None:
    bundle = build_distribution_bundle(REPO_ROOT)

    assert set(bundle) == {"SKILL.md", "reference.md", "README.md"}
    assert bundle["SKILL.md"].startswith("---\n")
    assert "name: liepin-cli" in bundle["SKILL.md"]
    assert "liepin-cli setup" in bundle["reference.md"]
    assert "~/.cursor/skills/liepin-cli/" in bundle["README.md"]
    assert "skills/liepin-cli/" in bundle["README.md"]
    assert "liepin-cli skill install" in bundle["README.md"]
    assert "liepin-cli-export-skill" not in bundle["README.md"]


def test_build_repo_skills_dir_files_include_multi_platform_install_assets() -> None:
    repo_skills_files = build_repo_skills_dir_files(REPO_ROOT)

    assert set(repo_skills_files) == {
        "README.md",
        "SKILL.md",
        "reference.md",
        "install-targets.json",
    }
    targets_data = json.loads(repo_skills_files["install-targets.json"])
    assert targets_data["skillName"] == "liepin-cli"
    assert "generatedFrom" not in targets_data
    assert [target["id"] for target in targets_data["targets"]] == [
        "cursor-project",
        "cursor-home",
        "claude-home",
        "codex-home",
        "opencode-home",
        "cowork-generic",
    ]
    assert {target["status"] for target in targets_data["targets"]} == {
        "documented",
        "generic",
    }
    assert all(
        target["copy_from"] == "skills/liepin-cli"
        for target in targets_data["targets"]
    )
    assert "Claude Code" in repo_skills_files["README.md"]
    assert "Codex" in repo_skills_files["README.md"]
    assert "Cowork" in repo_skills_files["README.md"]


def test_write_distribution_bundle_creates_project_and_repo_outputs(
    tmp_path,
) -> None:
    project_skill_dir = tmp_path / ".cursor" / "skills" / "liepin-cli"
    repo_skills_dir = tmp_path / "skills" / "liepin-cli"

    write_distribution_bundle(
        repo_root=REPO_ROOT,
        project_skill_dir=project_skill_dir,
        repo_skills_dir=repo_skills_dir,
    )

    assert (project_skill_dir / "SKILL.md").exists()
    assert (project_skill_dir / "reference.md").exists()
    assert (repo_skills_dir / "SKILL.md").exists()
    assert (repo_skills_dir / "reference.md").exists()
    assert (repo_skills_dir / "README.md").exists()
    assert (repo_skills_dir / "install-targets.json").exists()

    assert (
        project_skill_dir / "SKILL.md"
    ).read_text(encoding="utf-8") == (
        repo_skills_dir / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert (
        project_skill_dir / "reference.md"
    ).read_text(encoding="utf-8") == (
        repo_skills_dir / "reference.md"
    ).read_text(encoding="utf-8")
    assert _relative_files(project_skill_dir) == sorted(
        [
            "SKILL.md",
            "reference.md",
        ]
    )
    assert _relative_files(repo_skills_dir) == sorted(
        [
            "README.md",
            "SKILL.md",
            "install-targets.json",
            "reference.md",
        ]
    )


def test_distribution_bundle_is_generated_from_project_source_not_existing_skill(
    tmp_path,
) -> None:
    project_skill_dir = tmp_path / "generated-project-skill"
    repo_skills_dir = tmp_path / "skills" / "liepin-cli"

    write_distribution_bundle(
        repo_root=REPO_ROOT,
        project_skill_dir=project_skill_dir,
        repo_skills_dir=repo_skills_dir,
    )

    skill_text = (repo_skills_dir / "SKILL.md").read_text(encoding="utf-8")
    reference_text = (repo_skills_dir / "reference.md").read_text(encoding="utf-8")

    assert "liepin-cli job apply --job-id <id> --job-kind <kind>" in skill_text
    assert "### Resume Commands" in reference_text
    assert "### Job Commands" in reference_text


def test_install_skill_writes_user_cursor_when_global(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    install_skill(REPO_ROOT, global_cursor=True)
    dest = tmp_path / ".cursor" / "skills" / "liepin-cli"
    assert (dest / "SKILL.md").exists()
    assert (dest / "reference.md").exists()
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == (
        (REPO_ROOT / ".cursor" / "skills" / "liepin-cli" / "SKILL.md").read_text(encoding="utf-8")
    )


def test_write_distribution_bundle_removes_stale_generated_files(tmp_path) -> None:
    project_skill_dir = tmp_path / ".cursor" / "skills" / "liepin-cli"
    repo_skills_dir = tmp_path / "skills" / "liepin-cli"

    (project_skill_dir / "nested" / "old.txt").parent.mkdir(parents=True, exist_ok=True)
    (project_skill_dir / "nested" / "old.txt").write_text("stale", encoding="utf-8")
    (repo_skills_dir / "stale.txt").parent.mkdir(parents=True, exist_ok=True)
    (repo_skills_dir / "stale.txt").write_text("stale", encoding="utf-8")

    write_distribution_bundle(
        repo_root=REPO_ROOT,
        project_skill_dir=project_skill_dir,
        repo_skills_dir=repo_skills_dir,
    )

    assert not (project_skill_dir / "nested" / "old.txt").exists()
    assert not (repo_skills_dir / "stale.txt").exists()


def test_checked_in_generated_artifacts_match_current_bundle() -> None:
    bundle = build_distribution_bundle(REPO_ROOT)
    repo_skills_files = build_repo_skills_dir_files(REPO_ROOT)

    assert bundle["SKILL.md"] == repo_skills_files["SKILL.md"]
    assert bundle["reference.md"] == repo_skills_files["reference.md"]

    skills_dir = REPO_ROOT / "skills" / "liepin-cli"
    for name, expected in repo_skills_files.items():
        assert (skills_dir / name).read_text(encoding="utf-8") == expected

    for filename in ("SKILL.md", "reference.md"):
        expected = bundle[filename]
        project_skill_path = REPO_ROOT / ".cursor" / "skills" / "liepin-cli" / filename
        if project_skill_path.exists():
            assert project_skill_path.read_text(encoding="utf-8") == expected
