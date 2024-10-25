import logging
from typing import Dict, Tuple, Optional
from django.db import transaction
from django.db.models import Avg, Count
from django.core.exceptions import ValidationError

from ..interfaces import FeedbackServiceInterface
from ..models import Feedback, Person

logger = logging.getLogger(__name__)

class FeedbackService(FeedbackServiceInterface):
    @transaction.atomic
    def create_feedback(
        self,
        recipient_id: str,
        provider_id: str,
        message: str,
        stars: int
    ) -> Tuple[bool, str]:
        """Create feedback for a person"""
        try:
            # Validate feedback first
            valid, validation_message = self.validate_feedback(
                recipient_id=recipient_id,
                provider_id=provider_id,
                stars=stars
            )
            
            if not valid:
                return False, validation_message

            # Create feedback
            feedback = Feedback.objects.create(
                recipient_id=recipient_id,
                provider_id=provider_id,
                message=message,
                stars=stars
            )

            return True, "Feedback created successfully"

        except Exception as e:
            logger.error(f"Error creating feedback: {str(e)}")
            return False, f"Failed to create feedback: {str(e)}"

    def get_person_feedback_analytics(self, person_id: str) -> Dict:
        """Get analytics about feedback received by a person"""
        try:
            feedbacks = Feedback.objects.filter(recipient_id=person_id)
            total_feedbacks = feedbacks.count()

            if total_feedbacks == 0:
                return {
                    'feedback_count': 0,
                    'average_stars': 0,
                    'stars_distribution': {i: 0 for i in range(1, 6)},
                    'recent_feedback': [],
                    'top_feedback': []
                }

            # Calculate basic metrics
            aggregates = feedbacks.aggregate(
                feedback_count=Count('id'),
                average_stars=Avg('stars')
            )

            # Calculate star distribution
            stars_counts = feedbacks.values('stars').annotate(count=Count('id'))
            stars_percentages = {i: 0 for i in range(1, 6)}  # Initialize all star levels
            
            for entry in stars_counts:
                percentage = (entry['count'] / total_feedbacks) * 100
                stars_percentages[entry['stars']] = round(percentage, 1)

            # Get recent and top feedback
            recent_feedback = feedbacks.order_by('-id')[:5].values(
                'id', 'message', 'stars', 'provider__full_name'
            )
            
            top_feedback = feedbacks.filter(stars__gte=4).order_by('-id')[:5].values(
                'id', 'message', 'stars', 'provider__full_name'
            )

            return {
                'feedback_count': aggregates['feedback_count'],
                'average_stars': round(aggregates['average_stars'], 1) if aggregates['average_stars'] else 0,
                'stars_distribution': stars_percentages,
                'recent_feedback': list(recent_feedback),
                'top_feedback': list(top_feedback)
            }

        except Exception as e:
            logger.error(f"Error getting feedback analytics: {str(e)}")
            return {}

    def validate_feedback(
        self,
        recipient_id: str,
        provider_id: str,
        stars: int
    ) -> Tuple[bool, str]:
        """Validate feedback before creation"""
        try:
            # Check if recipient exists
            if not Person.objects.filter(id=recipient_id).exists():
                return False, "Recipient not found"

            # Check if provider exists
            if not Person.objects.filter(id=provider_id).exists():
                return False, "Provider not found"

            # Validate stars range
            if not 1 <= stars <= 5:
                return False, "Stars must be between 1 and 5"

            # Check self-feedback
            if recipient_id == provider_id:
                return False, "Cannot provide feedback to yourself"

            # Check for duplicate feedback
            if Feedback.objects.filter(
                recipient_id=recipient_id,
                provider_id=provider_id
            ).exists():
                return False, "Feedback already provided"

            return True, "Feedback validation successful"

        except Exception as e:
            logger.error(f"Error validating feedback: {str(e)}")
            return False, "Failed to validate feedback"

    def get_provider_feedback_history(
        self,
        provider_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get history of feedback provided by a person"""
        try:
            feedbacks = Feedback.objects.filter(
                provider_id=provider_id
            ).order_by('-id')[:limit].values(
                'id',
                'recipient__full_name',
                'message',
                'stars',
                'created_at'
            )

            return list(feedbacks)

        except Exception as e:
            logger.error(f"Error getting provider feedback history: {str(e)}")
            return []

    def get_recipient_feedback_detail(
        self,
        recipient_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get detailed feedback received by a person"""
        try:
            feedbacks = Feedback.objects.filter(
                recipient_id=recipient_id
            ).order_by('-id')[:limit].values(
                'id',
                'provider__full_name',
                'message',
                'stars',
                'created_at'
            )

            return list(feedbacks)

        except Exception as e:
            logger.error(f"Error getting recipient feedback detail: {str(e)}")
            return []

    def delete_feedback(
        self,
        feedback_id: str,
        provider_id: str
    ) -> Tuple[bool, str]:
        """Delete feedback (only by the provider)"""
        try:
            feedback = Feedback.objects.filter(
                id=feedback_id,
                provider_id=provider_id
            ).first()

            if not feedback:
                return False, "Feedback not found or unauthorized"

            feedback.delete()
            return True, "Feedback deleted successfully"

        except Exception as e:
            logger.error(f"Error deleting feedback: {str(e)}")
            return False, "Failed to delete feedback"