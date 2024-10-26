from decimal import Decimal
from ..interfaces import FeeServiceInterface

class FeeService(FeeServiceInterface):
    def calculate_platform_fee(self, amount_usd_cents: int) -> int:
        fee_rate = self.get_platform_fee_rate()
        fee_amount = int(Decimal(amount_usd_cents) * fee_rate)
        return max(fee_amount, 100)  # Minimum fee of $1

    def get_platform_fee_rate(self) -> Decimal:
        return Decimal('0.05')  # 5% platform fee
