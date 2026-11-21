"""
Tests for validating SKILL.md frontmatter across all agent kits.

Ensures that every kit's SKILL.md has valid YAML frontmatter with required fields.

Run with: pytest tests/test_skill_frontmatter.py -v
"""

import re
from pathlib import Path

import pytest

# Find the workspace root
WORKSPACE_ROOT = Path(__file__).parent.parent

# All skill files to validate
SKILL_FILES = [
    WORKSPACE_ROOT / "grokbot" / "SKILL.md",
    WORKSPACE_ROOT / "claude" / "skills" / "mission-control" / "SKILL.md",
    WORKSPACE_ROOT / "hermes" / "skills" / "mission-control" / "SKILL.md",
]


def extract_frontmatter(content: str) -> dict | None:
    """
    Extract YAML frontmatter from a markdown file.
    
    Returns:
        dict: Parsed frontmatter, or None if no frontmatter found
    """
    # Match frontmatter between --- delimiters
    match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not match:
        return None
    
    frontmatter_text = match.group(1)
    
    # Simple YAML parser for the fields we care about
    # This avoids adding pyyaml as a dependency
    frontmatter = {}
    current_key = None
    
    for line in frontmatter_text.split('\n'):
        # Skip empty lines
        if not line.strip():
            continue
        
        # Key-value pair
        if ':' in line and not line.startswith(' '):
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            frontmatter[key] = value
            current_key = key
        # Continuation of previous value (for multiline strings)
        elif current_key and line.startswith(' '):
            # Append to previous value (for description fields that might wrap)
            if isinstance(frontmatter[current_key], str):
                frontmatter[current_key] += ' ' + line.strip()
    
    return frontmatter


class TestSkillFrontmatter:
    """Test that all SKILL.md files have valid frontmatter."""

    @pytest.mark.parametrize("skill_path", SKILL_FILES, ids=lambda p: str(p.relative_to(WORKSPACE_ROOT)))
    def test_skill_file_exists(self, skill_path):
        """Test that the skill file exists."""
        assert skill_path.exists(), f"Skill file not found: {skill_path}"

    @pytest.mark.parametrize("skill_path", SKILL_FILES, ids=lambda p: str(p.relative_to(WORKSPACE_ROOT)))
    def test_skill_has_frontmatter(self, skill_path):
        """Test that the skill file has YAML frontmatter."""
        content = skill_path.read_text()
        assert content.startswith('---\n'), f"Skill file must start with YAML frontmatter: {skill_path}"
        
        frontmatter = extract_frontmatter(content)
        assert frontmatter is not None, f"Failed to parse frontmatter in: {skill_path}"

    @pytest.mark.parametrize("skill_path", SKILL_FILES, ids=lambda p: str(p.relative_to(WORKSPACE_ROOT)))
    def test_skill_has_name(self, skill_path):
        """Test that the skill has a 'name' field."""
        content = skill_path.read_text()
        frontmatter = extract_frontmatter(content)
        
        assert 'name' in frontmatter, f"Skill frontmatter must have 'name' field: {skill_path}"
        assert frontmatter['name'], f"Skill 'name' field cannot be empty: {skill_path}"

    @pytest.mark.parametrize("skill_path", SKILL_FILES, ids=lambda p: str(p.relative_to(WORKSPACE_ROOT)))
    def test_skill_has_description(self, skill_path):
        """Test that the skill has a 'description' field."""
        content = skill_path.read_text()
        frontmatter = extract_frontmatter(content)
        
        assert 'description' in frontmatter, f"Skill frontmatter must have 'description' field: {skill_path}"
        assert frontmatter['description'], f"Skill 'description' field cannot be empty: {skill_path}"

    @pytest.mark.parametrize("skill_path", SKILL_FILES, ids=lambda p: str(p.relative_to(WORKSPACE_ROOT)))
    def test_skill_description_not_too_long(self, skill_path):
        """Test that the skill description is concise (recommended max 120 chars)."""
        content = skill_path.read_text()
        frontmatter = extract_frontmatter(content)
        
        description = frontmatter.get('description', '')
        # Hermes docs recommend ≤60 chars, but we'll be lenient at 150
        assert len(description) <= 150, (
            f"Skill description should be concise (≤150 chars): {skill_path}\n"
            f"  Current length: {len(description)}\n"
            f"  Description: {description}"
        )

    def test_all_kits_have_skills(self):
        """Test that we're checking all expected kits."""
        # Verify we found all three kits
        kit_names = [str(p.relative_to(WORKSPACE_ROOT).parts[0]) for p in SKILL_FILES]
        expected_kits = ['grokbot', 'claude', 'hermes']
        
        for expected in expected_kits:
            assert expected in kit_names, f"Missing skill test for {expected} kit"

    def test_grokbot_has_correct_name(self):
        """Test that Grok Bot skill has the expected name."""
        grokbot_skill = WORKSPACE_ROOT / "grokbot" / "SKILL.md"
        content = grokbot_skill.read_text()
        frontmatter = extract_frontmatter(content)
        
        # Grok Bot uses "Mission Control (Grok Bot)" as the name
        assert 'Mission Control' in frontmatter['name'], (
            f"Grok Bot skill should reference Mission Control in name"
        )

    def test_claude_has_correct_name(self):
        """Test that Claude skill has the expected name."""
        claude_skill = WORKSPACE_ROOT / "claude" / "skills" / "mission-control" / "SKILL.md"
        content = claude_skill.read_text()
        frontmatter = extract_frontmatter(content)
        
        # Claude uses "Mission Control" as the name
        assert frontmatter['name'] == 'Mission Control', (
            f"Claude skill should be named 'Mission Control'"
        )

    def test_hermes_has_correct_name(self):
        """Test that Hermes skill has the expected name."""
        hermes_skill = WORKSPACE_ROOT / "hermes" / "skills" / "mission-control" / "SKILL.md"
        content = hermes_skill.read_text()
        frontmatter = extract_frontmatter(content)
        
        # Hermes uses kebab-case: "mission-control"
        assert frontmatter['name'] == 'mission-control', (
            f"Hermes skill should be named 'mission-control' (kebab-case)"
        )

    def test_hermes_has_required_env_vars(self):
        """Test that Hermes skill declares required environment variables."""
        hermes_skill = WORKSPACE_ROOT / "hermes" / "skills" / "mission-control" / "SKILL.md"
        content = hermes_skill.read_text()
        
        # Hermes supports required_environment_variables in frontmatter
        # Check that it's declared (the format is more complex, so just check presence)
        assert 'required_environment_variables:' in content, (
            f"Hermes skill should declare required_environment_variables"
        )
        
        # Check for the expected variables
        assert 'MC_AGENT' in content, "Hermes skill should require MC_AGENT"
        assert 'MC_PRIVATE_KEY' in content, "Hermes skill should require MC_PRIVATE_KEY"
