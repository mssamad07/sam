"""
SkillRegistry for registering, retrieving, and discovering skills in Sam.
Provides duplicate registration protection and clean isolation.
"""

from sam_capabilities.base import BaseSkill
from sam_core.logger import get_logger

logger = get_logger("capabilities.registry")


class SkillRegistry:
    """Central registry for all active skills in the system."""

    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        """
        Register a new skill.
        Raises ValueError if a skill with the same name is already registered.
        """
        if skill.name in self._skills:
            raise ValueError(f"Skill '{skill.name}' is already registered in registry.")

        self._skills[skill.name] = skill
        logger.info(f"Registered skill '{skill.name}' (v{skill.version})")

    def get_skill(self, skill_name: str) -> BaseSkill | None:
        """Retrieve a registered skill by name, or None if not found."""
        return self._skills.get(skill_name)

    def has_skill(self, skill_name: str) -> bool:
        """Check if a skill is registered."""
        return skill_name in self._skills

    def list_skills(self) -> list[BaseSkill]:
        """Return a list of all currently registered skills."""
        return list(self._skills.values())

    def unregister(self, skill_name: str) -> bool:
        """
        Unregister a skill by name.
        Returns True if the skill was removed, False if not found.
        """
        if skill_name in self._skills:
            del self._skills[skill_name]
            logger.info(f"Unregistered skill '{skill_name}'")
            return True
        return False

    def clear(self) -> None:
        """Remove all registered skills (useful for test isolation)."""
        self._skills.clear()

    @property
    def count(self) -> int:
        """Return the number of registered skills."""
        return len(self._skills)


# Global singleton instance
skill_registry = SkillRegistry()
