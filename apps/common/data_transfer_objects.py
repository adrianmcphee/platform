from dataclasses import dataclass
from typing import Optional

@dataclass
class BountyPurchaseData:
    id: str
    title: str
    description: str
    reward_type: str
    reward_in_usd_cents: Optional[int]
    reward_in_points: Optional[int]
    status: str

