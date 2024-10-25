import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.conf import settings

from ..interfaces import TaxServiceInterface, FeeServiceInterface
from ..models import TaxRate

logger = logging.getLogger(__name__)

class TaxAndFeeService(TaxServiceInterface, FeeServiceInterface):
    # Cache keys
    TAX_RATE_CACHE_KEY = "tax_rate_{country_code}"
    PLATFORM_FEE_RATE_CACHE_KEY = "platform_fee_rate"
    
    # Cache duration (24 hours)
    CACHE_DURATION = 86400
    
    # Default platform fee rate (can be configured in settings)
    DEFAULT_PLATFORM_FEE_RATE = Decimal('0.10')  # 10%
    
    # Minimum amounts for fee calculation
    MIN_AMOUNT_FOR_FEES = 100  # $1.00 in cents

    def calculate_tax(
        self,
        amount_cents: int,
        country_code: str
    ) -> int:
        """Calculate tax amount in cents"""
        try:
            if amount_cents < 0:
                raise ValidationError("Amount cannot be negative")

            rate = self.get_rate(country_code)
            if rate is None:
                logger.warning(f"No tax rate found for country {country_code}")
                return 0

            tax_amount = int(round(Decimal(amount_cents) * rate))
            return max(0, tax_amount)

        except Exception as e:
            logger.error(f"Error calculating tax: {str(e)}")
            return 0

    def get_rate(self, country_code: str) -> Optional[Decimal]:
        """Get tax rate for a country"""
        try:
            # Check cache first
            cache_key = self.TAX_RATE_CACHE_KEY.format(country_code=country_code)
            rate = cache.get(cache_key)
            
            if rate is not None:
                return Decimal(str(rate))

            # Get from database
            tax_rate = TaxRate.objects.filter(country_code=country_code).first()
            if tax_rate:
                # Cache the rate
                cache.set(cache_key, str(tax_rate.rate), self.CACHE_DURATION)
                return tax_rate.rate

            return None

        except Exception as e:
            logger.error(f"Error getting tax rate: {str(e)}")
            return None

    def update_tax_rate(
        self,
        country_code: str,
        rate: Decimal,
        name: str
    ) -> Tuple[bool, str]:
        """Update or create tax rate for country"""
        try:
            if not 0 <= rate <= 1:
                return False, "Rate must be between 0 and 1"

            with transaction.atomic():
                tax_rate, created = TaxRate.objects.update_or_create(
                    country_code=country_code,
                    defaults={
                        'rate': rate,
                        'name': name
                    }
                )

                # Invalidate cache
                cache_key = self.TAX_RATE_CACHE_KEY.format(country_code=country_code)
                cache.delete(cache_key)

                action = "created" if created else "updated"
                return True, f"Tax rate {action} successfully"

        except Exception as e:
            logger.error(f"Error updating tax rate: {str(e)}")
            return False, str(e)

    def calculate_platform_fee(
        self,
        amount_cents: int
    ) -> int:
        """Calculate platform fee in cents"""
        try:
            if amount_cents < 0:
                raise ValidationError("Amount cannot be negative")

            if amount_cents < self.MIN_AMOUNT_FOR_FEES:
                return 0

            rate = self.get_current_rate()
            fee_amount = int(round(Decimal(amount_cents) * rate))
            return max(0, fee_amount)

        except Exception as e:
            logger.error(f"Error calculating platform fee: {str(e)}")
            return 0

    def get_current_rate(self) -> Decimal:
        """Get current platform fee rate"""
        try:
            # Check cache first
            rate = cache.get(self.PLATFORM_FEE_RATE_CACHE_KEY)
            
            if rate is not None:
                return Decimal(str(rate))

            # Get from settings or use default
            rate = getattr(settings, 'PLATFORM_FEE_RATE', self.DEFAULT_PLATFORM_FEE_RATE)
            
            # Cache the rate
            cache.set(self.PLATFORM_FEE_RATE_CACHE_KEY, str(rate), self.CACHE_DURATION)
            
            return Decimal(str(rate))

        except Exception as e:
            logger.error(f"Error getting platform fee rate: {str(e)}")
            return self.DEFAULT_PLATFORM_FEE_RATE

    def update_platform_fee_rate(
        self,
        new_rate: Decimal
    ) -> Tuple[bool, str]:
        """Update platform fee rate"""
        try:
            if not 0 <= new_rate <= 1:
                return False, "Rate must be between 0 and 1"

            # Update in settings (implementation depends on settings storage method)
            # This is a placeholder - actual implementation would depend on how settings are managed
            setattr(settings, 'PLATFORM_FEE_RATE', new_rate)

            # Invalidate cache
            cache.delete(self.PLATFORM_FEE_RATE_CACHE_KEY)

            return True, "Platform fee rate updated successfully"

        except Exception as e:
            logger.error(f"Error updating platform fee rate: {str(e)}")
            return False, str(e)

    def get_fee_breakdown(
        self,
        amount_cents: int,
        country_code: str
    ) -> Dict:
        """Get detailed breakdown of fees and taxes"""
        try:
            platform_fee = self.calculate_platform_fee(amount_cents)
            tax_amount = self.calculate_tax(amount_cents, country_code)
            
            subtotal = amount_cents
            total = subtotal + platform_fee + tax_amount

            return {
                'subtotal_cents': subtotal,
                'platform_fee_cents': platform_fee,
                'tax_cents': tax_amount,
                'total_cents': total,
                'platform_fee_rate': float(self.get_current_rate()),
                'tax_rate': float(self.get_rate(country_code) or 0),
                'country_code': country_code
            }

        except Exception as e:
            logger.error(f"Error getting fee breakdown: {str(e)}")
            return {
                'subtotal_cents': amount_cents,
                'platform_fee_cents': 0,
                'tax_cents': 0,
                'total_cents': amount_cents,
                'platform_fee_rate': 0,
                'tax_rate': 0,
                'country_code': country_code
            }

    def validate_tax_exemption(
        self,
        tax_id: str,
        country_code: str
    ) -> Tuple[bool, str]:
        """Validate tax exemption status"""
        # This is a placeholder - actual implementation would depend on tax validation requirements
        try:
            # Basic format validation
            if not tax_id or len(tax_id) < 5:
                return False, "Invalid tax ID format"

            # Country-specific validation could be added here
            # For now, just return true if format is valid
            return True, "Tax ID validated successfully"

        except Exception as e:
            logger.error(f"Error validating tax exemption: {str(e)}")
            return False, str(e)

    def get_tax_rates(
        self,
        active_only: bool = True
    ) -> List[Dict]:
        """Get list of all tax rates"""
        try:
            rates = TaxRate.objects.all()
            
            return [{
                'country_code': rate.country_code,
                'name': rate.name,
                'rate': float(rate.rate),
            } for rate in rates]

        except Exception as e:
            logger.error(f"Error getting tax rates: {str(e)}")
            return []