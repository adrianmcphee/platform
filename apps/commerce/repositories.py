from abc import ABC, abstractmethod
from typing import Optional

class OrganisationRepository(ABC):
    @abstractmethod
    def get_by_id(self, org_id: str) -> Optional[dict]:
        pass

class DjangoOrganisationRepository(OrganisationRepository):
    def get_by_id(self, org_id: str) -> Optional[dict]:
        from apps.commerce.models import Organisation
        org = Organisation.objects.filter(id=org_id).first()
        if org:
            return {'id': org.id, 'name': org.name}
        return None

class MockOrganisationRepository(OrganisationRepository):
    def get_by_id(self, org_id: str) -> Optional[dict]:
        return {'id': org_id, 'name': 'Test Organisation'}

