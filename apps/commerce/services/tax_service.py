from decimal import Decimal
from typing import Tuple
from ..interfaces import TaxServiceInterface

class TaxService(TaxServiceInterface):
    def calculate_tax(self, amount_usd_cents: int, country_code: str) -> int:
        success, tax_rate = self.get_tax_rate(country_code)
        if not success:
            return 0
        return int(Decimal(amount_usd_cents) * tax_rate)

    def get_tax_rate(self, country_code: str) -> Tuple[bool, Decimal]:
        tax_rates = {
            'US': Decimal('0.0'),
            'GB': Decimal('0.20'),
            'JP': Decimal('0.10'),
            # Add more countries as needed
        }
        if country_code in tax_rates:
            return True, tax_rates[country_code]
        return False, Decimal('0.0')
