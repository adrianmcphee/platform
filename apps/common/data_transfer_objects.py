from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum

class RewardType(str, Enum):
    USD = "USD"
    POINTS = "POINTS"

class BountyStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"

class BountyPurchaseData(BaseModel):
    id: str
    product_id: str
    title: str
    description: str
    reward_type: RewardType
    reward_in_usd_cents: Optional[int] = Field(None, ge=0)
    reward_in_points: Optional[int] = Field(None, ge=0)
    status: BountyStatus

    @field_validator('reward_in_usd_cents', 'reward_in_points')
    @classmethod
    def validate_reward(cls, v, info):
        if 'reward_type' in info.data:
            if info.data['reward_type'] == RewardType.USD and not info.data.get('reward_in_usd_cents'):
                raise ValueError('USD rewards must specify reward_in_usd_cents')
            if info.data['reward_type'] == RewardType.POINTS and not info.data.get('reward_in_points'):
                raise ValueError('POINTS rewards must specify reward_in_points')
        return v

    class Config:
        use_enum_values = True  # This will use string values for enums in dict() output
