import logging
from typing import Dict, Tuple, List, Optional
from django.db import transaction
from django.core.exceptions import ValidationError

from ..interfaces import SkillManagementServiceInterface
from ..models import Skill, Expertise, PersonSkill, Person

logger = logging.getLogger(__name__)

class SkillManagementService(SkillManagementServiceInterface):
    @transaction.atomic
    def add_skill_to_person(
        self,
        person_id: str,
        skill_id: str,
        expertise_ids: List[str]
    ) -> Tuple[bool, str]:
        """Add a skill with expertise to a person"""
        try:
            # Validate inputs
            person = Person.objects.get(id=person_id)
            skill = Skill.objects.get(id=skill_id)
            
            if not skill.active:
                return False, "Skill is not active"
                
            if not skill.selectable:
                return False, "Skill is not selectable"

            # Validate expertises
            expertises = Expertise.objects.filter(
                id__in=expertise_ids,
                skill=skill,
                selectable=True
            )
            
            if len(expertises) != len(expertise_ids):
                return False, "One or more expertise selections are invalid"

            # Create or update PersonSkill
            person_skill, created = PersonSkill.objects.get_or_create(
                person=person,
                skill=skill
            )

            # Set expertises
            person_skill.expertise.set(expertises)
            
            return True, "Skill and expertise added successfully"
            
        except Person.DoesNotExist:
            return False, "Person not found"
        except Skill.DoesNotExist:
            return False, "Skill not found"
        except Exception as e:
            logger.error(f"Error adding skill to person: {str(e)}")
            return False, "Failed to add skill"

    def get_active_skills(self, parent_id: Optional[str] = None) -> List[Dict]:
        """Get active skills, optionally filtered by parent"""
        try:
            queryset = Skill.objects.filter(active=True)
            
            if parent_id:
                queryset = queryset.filter(parent_id=parent_id)
            else:
                queryset = queryset.filter(parent__isnull=True)

            return [
                {
                    'id': skill.id,
                    'name': skill.name,
                    'selectable': skill.selectable,
                    'display_boost_factor': skill.display_boost_factor,
                    'has_children': skill.get_children().exists()
                }
                for skill in queryset.order_by('name')
            ]
            
        except Exception as e:
            logger.error(f"Error fetching active skills: {str(e)}")
            return []

    def get_expertise_for_skill(self, skill_id: str) -> List[Dict]:
        """Get expertise options for a skill"""
        try:
            expertises = Expertise.objects.filter(
                skill_id=skill_id,
                selectable=True
            ).order_by('name')

            return [
                {
                    'id': exp.id,
                    'name': exp.name,
                    'fa_icon': exp.fa_icon,
                    'parent_id': exp.parent_id
                }
                for exp in expertises
            ]
            
        except Exception as e:
            logger.error(f"Error fetching expertise for skill: {str(e)}")
            return []

    def remove_skill_from_person(
        self,
        person_id: str,
        skill_id: str
    ) -> Tuple[bool, str]:
        """Remove a skill from a person"""
        try:
            person_skill = PersonSkill.objects.filter(
                person_id=person_id,
                skill_id=skill_id
            ).first()
            
            if not person_skill:
                return False, "Person does not have this skill"
                
            person_skill.delete()
            return True, "Skill removed successfully"
            
        except Exception as e:
            logger.error(f"Error removing skill from person: {str(e)}")
            return False, "Failed to remove skill"

    def update_person_expertise(
        self,
        person_id: str,
        skill_id: str,
        expertise_ids: List[str]
    ) -> Tuple[bool, str]:
        """Update expertise for an existing person skill"""
        try:
            person_skill = PersonSkill.objects.filter(
                person_id=person_id,
                skill_id=skill_id
            ).first()
            
            if not person_skill:
                return False, "Person does not have this skill"

            # Validate expertises
            expertises = Expertise.objects.filter(
                id__in=expertise_ids,
                skill_id=skill_id,
                selectable=True
            )
            
            if len(expertises) != len(expertise_ids):
                return False, "One or more expertise selections are invalid"

            # Update expertises
            person_skill.expertise.set(expertises)
            
            return True, "Expertise updated successfully"
            
        except Exception as e:
            logger.error(f"Error updating expertise: {str(e)}")
            return False, "Failed to update expertise"

    def get_person_skills(self, person_id: str) -> List[Dict]:
        """Get all skills and expertise for a person"""
        try:
            person_skills = PersonSkill.objects.filter(
                person_id=person_id
            ).select_related('skill').prefetch_related('expertise')

            return [
                {
                    'skill_id': ps.skill.id,
                    'skill_name': ps.skill.name,
                    'expertise': [
                        {
                            'id': exp.id,
                            'name': exp.name,
                            'fa_icon': exp.fa_icon
                        }
                        for exp in ps.expertise.all()
                    ]
                }
                for ps in person_skills
            ]
            
        except Exception as e:
            logger.error(f"Error fetching person skills: {str(e)}")
            return []