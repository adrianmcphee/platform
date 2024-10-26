from django.db import transaction
from apps.commerce.models import (
    Organisation,
    OrganisationWallet,
    OrganisationWalletTransaction,
    OrganisationPointAccount,
    PointTransaction,
    TaxRate
)

class OrganisationService:
    def create_organisation(self, name, country, tax_id=None):
        with transaction.atomic():
            organisation = Organisation.objects.create(
                name=name,
                country=country,
                tax_id=tax_id
            )
            OrganisationWallet.objects.create(organisation=organisation)
            OrganisationPointAccount.objects.create(organisation=organisation)
        return organisation

    def get_organisation(self, org_id):
        return Organisation.objects.get(id=org_id)

    def update_organisation(self, org_id, **kwargs):
        organisation = self.get_organisation(org_id)
        for key, value in kwargs.items():
            setattr(organisation, key, value)
        organisation.save()
        return organisation

    def get_organisation_wallet(self, org_id):
        return OrganisationWallet.objects.get(organisation_id=org_id)

    def add_funds_to_wallet(self, org_id, amount_cents, description, payment_method=None, transaction_id=None):
        wallet = self.get_organisation_wallet(org_id)
        with transaction.atomic():
            wallet.balance_usd_cents += amount_cents
            wallet.save()
            OrganisationWalletTransaction.objects.create(
                wallet=wallet,
                amount_cents=amount_cents,
                transaction_type=OrganisationWalletTransaction.TransactionType.CREDIT,
                description=description,
                payment_method=payment_method,
                transaction_id=transaction_id
            )
        return wallet

    def deduct_funds_from_wallet(self, org_id, amount_cents, description, related_order=None):
        wallet = self.get_organisation_wallet(org_id)
        if wallet.balance_usd_cents < amount_cents:
            raise ValueError("Insufficient funds in the wallet")
        
        with transaction.atomic():
            wallet.balance_usd_cents -= amount_cents
            wallet.save()
            OrganisationWalletTransaction.objects.create(
                wallet=wallet,
                amount_cents=amount_cents,
                transaction_type=OrganisationWalletTransaction.TransactionType.DEBIT,
                description=description,
                related_order=related_order
            )
        return wallet

    def get_organisation_point_account(self, org_id):
        return OrganisationPointAccount.objects.get(organisation_id=org_id)

    def add_points_to_account(self, org_id, points, description):
        point_account = self.get_organisation_point_account(org_id)
        with transaction.atomic():
            point_account.balance += points
            point_account.save()
            PointTransaction.objects.create(
                account=point_account,
                amount=points,
                transaction_type=PointTransaction.TransactionType.GRANT,
                description=description
            )
        return point_account

    def deduct_points_from_account(self, org_id, points, description):
        point_account = self.get_organisation_point_account(org_id)
        if point_account.balance < points:
            raise ValueError("Insufficient points in the account")
        
        with transaction.atomic():
            point_account.balance -= points
            point_account.save()
            PointTransaction.objects.create(
                account=point_account,
                amount=points,
                transaction_type=PointTransaction.TransactionType.USE,
                description=description
            )
        return point_account

    def get_tax_rate(self, country_code):
        try:
            return TaxRate.objects.get(country_code=country_code)
        except TaxRate.DoesNotExist:
            return None

    def get_organisation_transactions(self, org_id, transaction_type=None):
        wallet = self.get_organisation_wallet(org_id)
        transactions = wallet.transactions.all()
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        return transactions

    def get_organisation_point_transactions(self, org_id, transaction_type=None):
        point_account = self.get_organisation_point_account(org_id)
        transactions = point_account.org_transactions.all()
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        return transactions
