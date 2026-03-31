import platform
from dataclasses import dataclass
from enum import Enum


PathGroup = tuple[str, ...]


def _paths(*values: str) -> PathGroup:
    return values


@dataclass(frozen=True)
class EditorInfo:
    name: str
    config_dirs: PathGroup
    config_files: PathGroup
    usr_config_dirs: PathGroup
    usr_config_files: PathGroup
    agent_dirs: PathGroup
    agent_files: PathGroup
    usr_agent_dirs: PathGroup
    usr_agent_files: PathGroup
    instructions_dirs: PathGroup
    instructions_files: PathGroup
    usr_instructions_dirs: PathGroup
    usr_instructions_files: PathGroup
    skills_dirs: PathGroup
    skills_files: PathGroup
    usr_skills_dirs: PathGroup
    usr_skills_files: PathGroup
    hooks_dirs: PathGroup
    hooks_files: PathGroup
    usr_hooks_dirs: PathGroup
    usr_hooks_files: PathGroup


mac_vscode = EditorInfo(
    name="vscode",
    config_dirs=_paths(".vscode"),
    config_files=_paths(),
    usr_config_dirs=_paths("~/Library/Application Support/Code/User"),
    usr_config_files=_paths(),
    agent_dirs=_paths(".github/agents", ".claude/agents"),
    agent_files=_paths(),
    usr_agent_dirs=_paths("~/.copilot/agents", "~/.claude/agents"),
    usr_agent_files=_paths(),
    instructions_dirs=_paths(
        ".github/instructions",
        ".claude/rules",
    ),
    instructions_files=_paths(
        ".github/copilot-instructions.md",
        "AGENTS.md",
        "CLAUDE.md",
        ".claude/CLAUDE.md",
    ),
    usr_instructions_dirs=_paths(
        "~/.copilot/instructions",
        "~/.claude/rules",
    ),
    usr_instructions_files=_paths("~/.claude/CLAUDE.md"),
    skills_dirs=_paths(".github/skills", ".claude/skills", ".agents/skills"),
    skills_files=_paths(),
    usr_skills_dirs=_paths("~/.copilot/skills", "~/.claude/skills", "~/.agents/skills"),
    usr_skills_files=_paths(),
    hooks_dirs=_paths(".github/hooks"),
    hooks_files=_paths(".claude/settings.json", ".claude/settings.local.json"),
    usr_hooks_dirs=_paths("~/.copilot/hooks"),
    usr_hooks_files=_paths("~/.claude/settings.json"),
)

win_vscode = EditorInfo(
    name="vscode",
    config_dirs=_paths(".vscode"),
    config_files=_paths(),
    usr_config_dirs=_paths("%APPDATA%\\Code\\User"),
    usr_config_files=_paths(),
    agent_dirs=_paths(".github/agents", ".claude/agents"),
    agent_files=_paths(),
    usr_agent_dirs=_paths("~/.copilot/agents", "~/.claude/agents"),
    usr_agent_files=_paths(),
    instructions_dirs=_paths(
        ".github/instructions",
        ".claude/rules",
    ),
    instructions_files=_paths(
        ".github/copilot-instructions.md",
        "AGENTS.md",
        "CLAUDE.md",
        ".claude/CLAUDE.md",
    ),
    usr_instructions_dirs=_paths(
        "~/.copilot/instructions",
        "~/.claude/rules",
    ),
    usr_instructions_files=_paths("~/.claude/CLAUDE.md"),
    skills_dirs=_paths(".github/skills", ".claude/skills", ".agents/skills"),
    skills_files=_paths(),
    usr_skills_dirs=_paths("~/.copilot/skills", "~/.claude/skills", "~/.agents/skills"),
    usr_skills_files=_paths(),
    hooks_dirs=_paths(".github/hooks"),
    hooks_files=_paths(".claude/settings.json", ".claude/settings.local.json"),
    usr_hooks_dirs=_paths("~/.copilot/hooks"),
    usr_hooks_files=_paths("~/.claude/settings.json"),
)

mac_cursor = EditorInfo(
    name="cursor",
    config_dirs=_paths(".cursor"),
    config_files=_paths(),
    usr_config_dirs=_paths("~/.cursor"),
    usr_config_files=_paths(),
    agent_dirs=_paths(".cursor/agents", ".claude/agents", ".codex/agents"),
    agent_files=_paths(),
    usr_agent_dirs=_paths("~/.cursor/agents", "~/.claude/agents", "~/.codex/agents"),
    usr_agent_files=_paths(),
    instructions_dirs=_paths(".cursor/rules"),
    instructions_files=_paths("AGENTS.md"),
    usr_instructions_dirs=_paths(),
    usr_instructions_files=_paths(),
    skills_dirs=_paths(
        ".agents/skills", ".cursor/skills", ".claude/skills", ".codex/skills"
    ),
    skills_files=_paths(),
    usr_skills_dirs=_paths("~/.cursor/skills", "~/.claude/skills", "~/.codex/skills"),
    usr_skills_files=_paths(),
    hooks_dirs=_paths(),
    hooks_files=_paths(".cursor/hooks.json"),
    usr_hooks_dirs=_paths(),
    usr_hooks_files=_paths("~/.cursor/hooks.json"),
)

win_cursor = EditorInfo(
    name="cursor",
    config_dirs=_paths(".cursor"),
    config_files=_paths(),
    usr_config_dirs=_paths("~/.cursor"),
    usr_config_files=_paths(),
    agent_dirs=_paths(".cursor/agents", ".claude/agents", ".codex/agents"),
    agent_files=_paths(),
    usr_agent_dirs=_paths("~/.cursor/agents", "~/.claude/agents", "~/.codex/agents"),
    usr_agent_files=_paths(),
    instructions_dirs=_paths(".cursor/rules"),
    instructions_files=_paths("AGENTS.md"),
    usr_instructions_dirs=_paths(),
    usr_instructions_files=_paths(),
    skills_dirs=_paths(
        ".agents/skills", ".cursor/skills", ".claude/skills", ".codex/skills"
    ),
    skills_files=_paths(),
    usr_skills_dirs=_paths("~/.cursor/skills", "~/.claude/skills", "~/.codex/skills"),
    usr_skills_files=_paths(),
    hooks_dirs=_paths(),
    hooks_files=_paths(".cursor/hooks.json"),
    usr_hooks_dirs=_paths(),
    usr_hooks_files=_paths("~/.cursor/hooks.json"),
)

mac_windsurf = EditorInfo(
    name="windsurf",
    config_dirs=_paths(".windsurf"),
    config_files=_paths(),
    usr_config_dirs=_paths("~/.codeium/windsurf"),
    usr_config_files=_paths(),
    agent_dirs=_paths(),
    agent_files=_paths("AGENTS.md"),
    usr_agent_dirs=_paths(),
    usr_agent_files=_paths(),
    instructions_dirs=_paths(".windsurf/rules"),
    instructions_files=_paths("AGENTS.md"),
    usr_instructions_dirs=_paths(),
    usr_instructions_files=_paths("~/.codeium/windsurf/memories/global_rules.md"),
    skills_dirs=_paths(".windsurf/skills"),
    skills_files=_paths(),
    usr_skills_dirs=_paths("~/.codeium/windsurf/skills"),
    usr_skills_files=_paths(),
    hooks_dirs=_paths(),
    hooks_files=_paths(),
    usr_hooks_dirs=_paths(),
    usr_hooks_files=_paths(),
)

win_windsurf = EditorInfo(
    name="windsurf",
    config_dirs=_paths(".windsurf"),
    config_files=_paths(),
    usr_config_dirs=_paths("~/.codeium/windsurf"),
    usr_config_files=_paths(),
    agent_dirs=_paths(),
    agent_files=_paths("AGENTS.md"),
    usr_agent_dirs=_paths(),
    usr_agent_files=_paths(),
    instructions_dirs=_paths(".windsurf/rules"),
    instructions_files=_paths("AGENTS.md"),
    usr_instructions_dirs=_paths(),
    usr_instructions_files=_paths("~/.codeium/windsurf/memories/global_rules.md"),
    skills_dirs=_paths(".windsurf/skills"),
    skills_files=_paths(),
    usr_skills_dirs=_paths("~/.codeium/windsurf/skills"),
    usr_skills_files=_paths(),
    hooks_dirs=_paths(),
    hooks_files=_paths(),
    usr_hooks_dirs=_paths(),
    usr_hooks_files=_paths(),
)

mac_antigravity = EditorInfo(
    name="antigravity",
    config_dirs=_paths(".agents", ".agent"),
    config_files=_paths(),
    usr_config_dirs=_paths("~/.gemini/antigravity"),
    usr_config_files=_paths(),
    agent_dirs=_paths(),
    agent_files=_paths("agents.md"),
    usr_agent_dirs=_paths(),
    usr_agent_files=_paths(),
    instructions_dirs=_paths(".agents/rules", ".agent/rules"),
    instructions_files=_paths(),
    usr_instructions_dirs=_paths(),
    usr_instructions_files=_paths("~/.gemini/GEMINI.md"),
    skills_dirs=_paths(".agents/skills", ".agent/skills"),
    skills_files=_paths(),
    usr_skills_dirs=_paths("~/.gemini/antigravity/skills"),
    usr_skills_files=_paths(),
    hooks_dirs=_paths(),
    hooks_files=_paths(),
    usr_hooks_dirs=_paths(),
    usr_hooks_files=_paths(),
)

win_antigravity = EditorInfo(
    name="antigravity",
    config_dirs=_paths(".agents", ".agent"),
    config_files=_paths(),
    usr_config_dirs=_paths("~/.gemini/antigravity"),
    usr_config_files=_paths(),
    agent_dirs=_paths(),
    agent_files=_paths("agents.md"),
    usr_agent_dirs=_paths(),
    usr_agent_files=_paths(),
    instructions_dirs=_paths(".agents/rules", ".agent/rules"),
    instructions_files=_paths(),
    usr_instructions_dirs=_paths(),
    usr_instructions_files=_paths("~/.gemini/GEMINI.md"),
    skills_dirs=_paths(".agents/skills", ".agent/skills"),
    skills_files=_paths(),
    usr_skills_dirs=_paths("~/.gemini/antigravity/skills"),
    usr_skills_files=_paths(),
    hooks_dirs=_paths(),
    hooks_files=_paths(),
    usr_hooks_dirs=_paths(),
    usr_hooks_files=_paths(),
)

mac_claude_code = EditorInfo(
    name="claude_code",
    config_dirs=_paths(),
    config_files=_paths(".claude/settings.json", ".claude/settings.local.json"),
    usr_config_dirs=_paths(),
    usr_config_files=_paths("~/.claude/settings.json"),
    agent_dirs=_paths(".claude/agents"),
    agent_files=_paths(),
    usr_agent_dirs=_paths("~/.claude/agents"),
    usr_agent_files=_paths(),
    instructions_dirs=_paths(".claude/rules"),
    instructions_files=_paths("CLAUDE.md", ".claude/CLAUDE.md"),
    usr_instructions_dirs=_paths("~/.claude/rules"),
    usr_instructions_files=_paths("~/.claude/CLAUDE.md"),
    skills_dirs=_paths(".claude/skills"),
    skills_files=_paths(),
    usr_skills_dirs=_paths("~/.claude/skills"),
    usr_skills_files=_paths(),
    hooks_dirs=_paths(),
    hooks_files=_paths(".claude/settings.json", ".claude/settings.local.json"),
    usr_hooks_dirs=_paths(),
    usr_hooks_files=_paths("~/.claude/settings.json"),
)

win_claude_code = EditorInfo(
    name="claude_code",
    config_dirs=_paths(),
    config_files=_paths(".claude/settings.json", ".claude/settings.local.json"),
    usr_config_dirs=_paths(),
    usr_config_files=_paths("~/.claude/settings.json"),
    agent_dirs=_paths(".claude/agents"),
    agent_files=_paths(),
    usr_agent_dirs=_paths("~/.claude/agents"),
    usr_agent_files=_paths(),
    instructions_dirs=_paths(".claude/rules"),
    instructions_files=_paths("CLAUDE.md", ".claude/CLAUDE.md"),
    usr_instructions_dirs=_paths("~/.claude/rules"),
    usr_instructions_files=_paths("~/.claude/CLAUDE.md"),
    skills_dirs=_paths(".claude/skills"),
    skills_files=_paths(),
    usr_skills_dirs=_paths("~/.claude/skills"),
    usr_skills_files=_paths(),
    hooks_dirs=_paths(),
    hooks_files=_paths(".claude/settings.json", ".claude/settings.local.json"),
    usr_hooks_dirs=_paths(),
    usr_hooks_files=_paths("~/.claude/settings.json"),
)



class VSCODE_EDITORS(Enum):
    VSCODE = mac_vscode if platform.system() == "Darwin" else win_vscode
    CURSOR = mac_cursor if platform.system() == "Darwin" else win_cursor
    WINDSURF = mac_windsurf if platform.system() == "Darwin" else win_windsurf
    ANTIGRAVITY = mac_antigravity if platform.system() == "Darwin" else win_antigravity
    CLAUDE_CODE = mac_claude_code if platform.system() == "Darwin" else win_claude_code
