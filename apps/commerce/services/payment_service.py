from typing import Tuple, Optional, Dict, List
import logging
from ..interfaces import PaymentStrategyInterface
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

class PaymentService(PaymentStrategyInterface):
    def __init__(self, payment_gateway):
        self.payment_gateway = payment_gateway

    def process_payment(
        self,
        amount_cents: int,
        payment_details: Dict,
        **kwargs
    ) -> Tuple[bool, str, Optional[str]]:
        try:
            # Validate payment details before processing
            is_valid, error_messages = self.validate_payment_details(payment_details)
            if not is_valid:
                return False, f"Invalid payment details: {', '.join(error_messages)}", None

            # Process payment using the payment gateway
            success, transaction_id = self.payment_gateway.charge(
                amount_cents=amount_cents,
                payment_details=payment_details,
                **kwargs
            )

            if success:
                return True, "Payment processed successfully", transaction_id
            else:
                return False, "Payment processing failed", None

        except Exception as e:
            logger.error(f"Error processing payment: {str(e)}")
            return False, f"Error processing payment: {str(e)}", None

    def validate_payment_details(
        self,
        payment_details: Dict
    ) -> Tuple[bool, List[str]]:
        errors = []

        # Check for required fields
        required_fields = ['payment_method', 'amount']
        for field in required_fields:
            if field not in payment_details:
                errors.append(f"Missing required field: {field}")

        # Validate payment method
        valid_payment_methods = ['credit_card', 'paypal', 'bank_transfer']
        if payment_details.get('payment_method') not in valid_payment_methods:
            errors.append("Invalid payment method")

        # Validate amount
        try:
            amount = Decimal(payment_details.get('amount', '0'))
            if amount <= 0:
                errors.append("Amount must be greater than zero")
        except InvalidOperation:
            errors.append("Invalid amount format")

        # Additional validations based on payment method
        if payment_details.get('payment_method') == 'credit_card':
            if 'card_number' not in payment_details:
                errors.append("Missing credit card number")
            if 'expiry_date' not in payment_details:
                errors.append("Missing expiry date")
            if 'cvv' not in payment_details:
                errors.append("Missing CVV")

        elif payment_details.get('payment_method') == 'paypal':
            if 'paypal_email' not in payment_details:
                errors.append("Missing PayPal email")

        elif payment_details.get('payment_method') == 'bank_transfer':
            if 'bank_account_number' not in payment_details:
                errors.append("Missing bank account number")
            if 'routing_number' not in payment_details:
                errors.append("Missing routing number")

        return len(errors) == 0, errors

    def refund_payment(
        self,
        transaction_id: str,
        amount_cents: int,
        reason: str
    ) -> Tuple[bool, str, Optional[str]]:
        try:
            success, refund_id = self.payment_gateway.refund(
                transaction_id=transaction_id,
                amount_cents=amount_cents,
                reason=reason
            )

            if success:
                return True, "Refund processed successfully", refund_id
            else:
                return False, "Refund processing failed", None

        except Exception as e:
            logger.error(f"Error processing refund: {str(e)}")
            return False, f"Error processing refund: {str(e)}", None

    def get_payment_status(
        self,
        transaction_id: str
    ) -> Tuple[bool, str, Optional[Dict]]:
        try:
            success, status_details = self.payment_gateway.get_transaction_status(transaction_id)

            if success:
                return True, "Payment status retrieved successfully", status_details
            else:
                return False, "Failed to retrieve payment status", None

        except Exception as e:
            logger.error(f"Error retrieving payment status: {str(e)}")
            return False, f"Error retrieving payment status: {str(e)}", None

