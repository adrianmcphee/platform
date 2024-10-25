import logging
from typing import Dict, Tuple, List, Optional
from django.db import transaction
from django.core.exceptions import ValidationError
import os

from ..interfaces import PersonManagementServiceInterface
from ..models import Person

logger = logging.getLogger(__name__)

class PersonManagementService(PersonManagementServiceInterface):
    # Class-level constants moved from Person model
    STATUS_POINT_MAPPING = {
        Person.PersonStatus.DRONE: 0,
        Person.PersonStatus.HONEYBEE: 50,
        Person.PersonStatus.TRUSTED_BEE: 500,
        Person.PersonStatus.QUEEN_BEE: 2000,
        Person.PersonStatus.BEEKEEPER: 8000,
    }

    STATUS_PRIVILEGES_MAPPING = {
        Person.PersonStatus.DRONE: "Earn points by completing bounties, submitting Ideas & Bugs",
        Person.PersonStatus.HONEYBEE: "Earn payment for payment-eligible bounties on openunited.com",
        Person.PersonStatus.TRUSTED_BEE: "Early Access to claim top tasks",
        Person.PersonStatus.QUEEN_BEE: "A grant of 1000 points for your own open product on OpenUnited",
        Person.PersonStatus.BEEKEEPER: "Invite new products to openunited.com and grant points",
    }

    def calculate_points_status(self, points: int) -> str:
        """Calculate person's status based on points"""
        for status in reversed(self.STATUS_POINT_MAPPING.keys()):
            current_points = self.STATUS_POINT_MAPPING.get(status)
            if current_points <= points:
                return status
        return Person.PersonStatus.DRONE

    def get_points_privileges(self, status: str) -> str:
        """Get privileges for a given status"""
        return self.STATUS_PRIVILEGES_MAPPING.get(status, "")

    @transaction.atomic
    def add_points(self, person_id: str, points: int) -> Tuple[bool, str]:
        """Add points to person's account"""
        try:
            person = Person.objects.select_for_update().get(id=person_id)
            
            if points < 0:
                return False, "Cannot add negative points"
                
            old_status = self.calculate_points_status(person.points)
            person.points += points
            new_status = self.calculate_points_status(person.points)
            
            person.save()
            
            # Log status change if applicable
            if old_status != new_status:
                logger.info(f"Person {person_id} status changed from {old_status} to {new_status}")
            
            return True, f"Successfully added {points} points"
            
        except Person.DoesNotExist:
            return False, "Person not found"
        except Exception as e:
            logger.error(f"Error adding points: {str(e)}")
            return False, "Failed to add points"

    @transaction.atomic
    def update_profile(self, person_id: str, profile_data: Dict) -> Tuple[bool, str]:
        """Update person's profile information"""
        try:
            person = Person.objects.select_for_update().get(id=person_id)
            
            # Handle photo update/deletion
            if 'photo' in profile_data:
                if person.photo:
                    self._delete_photo(person)
                if profile_data['photo']:
                    person.photo = profile_data.pop('photo')
            
            # Update other fields
            for field, value in profile_data.items():
                if hasattr(person, field):
                    setattr(person, field, value)
            
            # Check profile completion
            person.completed_profile = self._check_profile_completion(person)
            person.save()
            
            return True, "Profile updated successfully"
            
        except Person.DoesNotExist:
            return False, "Person not found"
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            return False, "Failed to update profile"

    def get_profile_completion_status(self, person_id: str) -> Tuple[bool, List[str]]:
        """Check profile completion and return missing fields"""
        try:
            person = Person.objects.get(id=person_id)
            missing_fields = []
            
            required_fields = {
                'full_name': "Full Name",
                'preferred_name': "Preferred Name",
                'headline': "Headline",
                'overview': "Overview"
            }
            
            for field, display_name in required_fields.items():
                if not getattr(person, field):
                    missing_fields.append(display_name)
            
            # At least one link is required
            if not any([person.github_link, person.linkedin_link, 
                       person.twitter_link, person.website_link]):
                missing_fields.append("At least one social/professional link")
                
            return len(missing_fields) == 0, missing_fields
            
        except Person.DoesNotExist:
            return False, ["Person not found"]
        except Exception as e:
            logger.error(f"Error checking profile completion: {str(e)}")
            return False, ["Error checking profile completion"]

    def _delete_photo(self, person: Person) -> None:
        """Helper method to delete person's photo"""
        if person.photo:
            path = person.photo.path
            if os.path.exists(path):
                os.remove(path)
            person.photo.delete(save=False)

    def _check_profile_completion(self, person: Person) -> bool:
        """Helper method to check if profile is complete"""
        is_complete, missing = self.get_profile_completion_status(person.id)
        return is_complete

    def get_display_points(self, person_id: str) -> str:
        """Get display format for person's points"""
        try:
            person = Person.objects.get(id=person_id)
            status = self.calculate_points_status(person.points)
            statuses = list(self.STATUS_POINT_MAPPING.keys())
            
            # If highest status
            if status == statuses[-1]:
                return f">= {self.STATUS_POINT_MAPPING.get(status)}"
                
            # Get next status requirements
            index = statuses.index(status) + 1
            return f"< {self.STATUS_POINT_MAPPING.get(statuses[index])}"
            
        except Person.DoesNotExist:
            return "N/A"
        except Exception as e:
            logger.error(f"Error getting display points: {str(e)}")
            return "Error"