from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from enum import Enum

class RewardType(str, Enum):
    USD = "USD"
    POINTS = "POINTS"

class BountyStatus(str, Enum):
    FUNDED = "FUNDED"
    OPEN = "OPEN"
    CLAIMED = "CLAIMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class BountyPurchaseData(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    product_id: str
    title: str
    description: str
    reward_type: RewardType
    reward_in_usd_cents: Optional[int] = None
    reward_in_points: Optional[int] = None
    skill_id: str
    expertise_ids: List[str]

    @field_validator('reward_in_usd_cents', 'reward_in_points')
    @classmethod
    def validate_reward(cls, v, info):
        if 'reward_type' in info.data:
            if info.data['reward_type'] == RewardType.USD:
                if info.field_name == 'reward_in_usd_cents' and not v:
                    raise ValueError('USD rewards must specify reward_in_usd_cents')
            elif info.data['reward_type'] == RewardType.POINTS:
                if info.field_name == 'reward_in_points' and not v:
                    raise ValueError('POINTS rewards must specify reward_in_points')
        return v
