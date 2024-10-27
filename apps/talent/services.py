from django.db.models import Avg, Count

from .models import Feedback, Person, BountyClaim
from apps.product_management.models import Bounty


class FeedbackService:
    @staticmethod
    def create(**kwargs):
        feedback = Feedback(**kwargs)
        feedback.save()

        return feedback

    @staticmethod
    def get_analytics_for_person(person: Person) -> dict:
        """
        Generates the analytics that a Talent receives through the time he/she spent
        on the platform.
        """
        feedbacks = Feedback.objects.filter(recipient=person)

        total_feedbacks = feedbacks.count()

        if total_feedbacks == 0:
            total_feedbacks = 1

        feedback_aggregates = feedbacks.aggregate(feedback_count=Count("id"), average_stars=Avg("stars"))

        # Calculate percentages
        feedback_aggregates["average_stars"] = (
            round(feedback_aggregates["average_stars"], 1) if feedback_aggregates["average_stars"] is not None else 0
        )

        stars_counts = feedbacks.values("stars").annotate(count=Count("id"))

        stars_percentages = {star: int(round(0 / total_feedbacks * 100, 2)) for star in range(1, 6)}

        for entry in stars_counts:
            stars_percentages[entry["stars"]] = round(entry["count"] / total_feedbacks * 100, 1)

        feedback_aggregates.update(stars_percentages)

        return feedback_aggregates


class TalentService:
    def handle_bounty_claim_created(self, payload):
        person = Person.objects.get(id=payload['person_id'])
        bounty = Bounty.objects.get(id=payload['bounty_id'])
        BountyClaim.objects.create(
            bounty=bounty,
            person=person,
            status=BountyClaim.Status.REQUESTED
        )

    def handle_bounty_claim_status_changed(self, payload):
        claim = BountyClaim.objects.get(bounty_id=payload['bounty_id'], person_id=payload['person_id'])
        claim.status = payload['new_status']
        claim.save()

        if payload['new_status'] == "GRANTED":
            # Update other claims for this bounty
            BountyClaim.objects.filter(bounty_id=payload['bounty_id']).exclude(person_id=payload['person_id']).update(status="REJECTED")
