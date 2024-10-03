# Generated by Django 4.2.2 on 2024-10-03 13:09

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('product_management', '0052_remove_bounty_is_active_remove_challenge_reward_type_and_more'),
        ('commerce', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BountyCart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('status', models.CharField(choices=[('Created', 'Created'), ('Pending', 'Pending Admin Action'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')], default='Created', max_length=20)),
                ('requires_admin_approval', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='BountyCartItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('points', models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('usd_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ('bounty', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product_management.bounty')),
                ('cart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='commerce.bountycart')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='OrganisationPointAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('balance', models.PositiveIntegerField(default=0)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PointTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('amount', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('transaction_type', models.CharField(choices=[('GRANT', 'Grant'), ('USE', 'Use')], max_length=5)),
                ('description', models.TextField(blank=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='commerce.organisationpointaccount')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='cart',
            name='creator',
        ),
        migrations.RemoveField(
            model_name='cart',
            name='organisation_account',
        ),
        migrations.RemoveField(
            model_name='contributoraccount',
            name='owner',
        ),
        migrations.RemoveField(
            model_name='contributoraccountcredit',
            name='bounty_claim',
        ),
        migrations.RemoveField(
            model_name='contributoraccountcredit',
            name='contributor_account',
        ),
        migrations.RemoveField(
            model_name='contributoraccountcredit',
            name='contributor_reward',
        ),
        migrations.RemoveField(
            model_name='contributoraccountcredit',
            name='payment_order',
        ),
        migrations.RemoveField(
            model_name='contributoraccountdebit',
            name='contributor_account',
        ),
        migrations.RemoveField(
            model_name='contributoraccountdebit',
            name='payment_order',
        ),
        migrations.RemoveField(
            model_name='contributorreward',
            name='contributor_account',
        ),
        migrations.RemoveField(
            model_name='grant',
            name='approving_bee_keeper',
        ),
        migrations.RemoveField(
            model_name='grant',
            name='nominating_bee_keeper',
        ),
        migrations.RemoveField(
            model_name='grant',
            name='organisation_account',
        ),
        migrations.RemoveField(
            model_name='grant',
            name='organisation_account_credit',
        ),
        migrations.RemoveField(
            model_name='inboundpayment',
            name='sales_order',
        ),
        migrations.RemoveField(
            model_name='organisationaccount',
            name='organisation',
        ),
        migrations.RemoveField(
            model_name='organisationaccountcredit',
            name='organisation_account',
        ),
        migrations.RemoveField(
            model_name='organisationaccountdebit',
            name='organisation_account',
        ),
        migrations.RemoveField(
            model_name='outboundpayment',
            name='payment_order',
        ),
        migrations.RemoveField(
            model_name='paymentorder',
            name='contributor_account',
        ),
        migrations.DeleteModel(
            name='PointPriceConfiguration',
        ),
        migrations.RemoveField(
            model_name='productaccount',
            name='product',
        ),
        migrations.RemoveField(
            model_name='productaccountcredit',
            name='actioned_by',
        ),
        migrations.RemoveField(
            model_name='productaccountcredit',
            name='organisation_account_debit',
        ),
        migrations.RemoveField(
            model_name='productaccountcredit',
            name='product_account',
        ),
        migrations.RemoveField(
            model_name='productaccountdebit',
            name='bounty_claim',
        ),
        migrations.RemoveField(
            model_name='productaccountreservation',
            name='bounty_claim',
        ),
        migrations.RemoveField(
            model_name='salesorder',
            name='cart',
        ),
        migrations.RemoveField(
            model_name='salesorder',
            name='organisation_account',
        ),
        migrations.RemoveField(
            model_name='salesorder',
            name='organisation_account_credit',
        ),
        migrations.AlterModelOptions(
            name='organisation',
            options={},
        ),
        migrations.RemoveField(
            model_name='organisation',
            name='photo',
        ),
        migrations.RemoveField(
            model_name='organisation',
            name='username',
        ),
        migrations.AddField(
            model_name='organisation',
            name='country',
            field=models.CharField(default='US', max_length=2),
        ),
        migrations.AddField(
            model_name='organisation',
            name='vat_number',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.DeleteModel(
            name='Cart',
        ),
        migrations.DeleteModel(
            name='ContributorAccount',
        ),
        migrations.DeleteModel(
            name='ContributorAccountCredit',
        ),
        migrations.DeleteModel(
            name='ContributorAccountDebit',
        ),
        migrations.DeleteModel(
            name='ContributorReward',
        ),
        migrations.DeleteModel(
            name='Grant',
        ),
        migrations.DeleteModel(
            name='InboundPayment',
        ),
        migrations.DeleteModel(
            name='OrganisationAccount',
        ),
        migrations.DeleteModel(
            name='OrganisationAccountCredit',
        ),
        migrations.DeleteModel(
            name='OrganisationAccountDebit',
        ),
        migrations.DeleteModel(
            name='OutboundPayment',
        ),
        migrations.DeleteModel(
            name='PaymentOrder',
        ),
        migrations.DeleteModel(
            name='ProductAccount',
        ),
        migrations.DeleteModel(
            name='ProductAccountCredit',
        ),
        migrations.DeleteModel(
            name='ProductAccountDebit',
        ),
        migrations.DeleteModel(
            name='ProductAccountReservation',
        ),
        migrations.DeleteModel(
            name='SalesOrder',
        ),
        migrations.AddField(
            model_name='organisationpointaccount',
            name='organisation',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='point_account', to='commerce.organisation'),
        ),
        migrations.AddField(
            model_name='bountycart',
            name='organisation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='commerce.organisation'),
        ),
        migrations.AddField(
            model_name='bountycart',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product_management.product'),
        ),
        migrations.AddField(
            model_name='bountycart',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]