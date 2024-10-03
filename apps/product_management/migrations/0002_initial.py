# Generated by Django 4.2.2 on 2024-10-03 20:02

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('product_management', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('talent', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='productcontributoragreementtemplate',
            name='created_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='talent.person'),
        ),
        migrations.AddField(
            model_name='productcontributoragreementtemplate',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contributor_agreement_templates', to='product_management.product'),
        ),
        migrations.AddField(
            model_name='productcontributoragreement',
            name='agreement_template',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product_management.productcontributoragreementtemplate'),
        ),
        migrations.AddField(
            model_name='productcontributoragreement',
            name='person',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contributor_agreement', to='talent.person'),
        ),
        migrations.AddField(
            model_name='productarea',
            name='attachments',
            field=models.ManyToManyField(blank=True, to='product_management.fileattachment'),
        ),
        migrations.AddField(
            model_name='productarea',
            name='comments_start',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, to='talent.capabilitycomment'),
        ),
        migrations.AddField(
            model_name='productarea',
            name='product_tree',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='product_areas', to='product_management.producttree'),
        ),
        migrations.AddField(
            model_name='product',
            name='attachments',
            field=models.ManyToManyField(blank=True, to='product_management.fileattachment'),
        ),
        migrations.AddField(
            model_name='product',
            name='content_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='initiative',
            name='product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='product_management.product'),
        ),
        migrations.AddField(
            model_name='ideavote',
            name='idea',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product_management.idea'),
        ),
        migrations.AddField(
            model_name='ideavote',
            name='voter',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='idea',
            name='person',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='talent.person'),
        ),
        migrations.AddField(
            model_name='idea',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product_management.product'),
        ),
        migrations.AddField(
            model_name='contributorguide',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_contributor_guide', to='product_management.product'),
        ),
        migrations.AddField(
            model_name='contributorguide',
            name='skill',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='skill_contributor_guide', to='talent.skill'),
        ),
        migrations.AddField(
            model_name='competitionentryrating',
            name='entry',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='product_management.competitionentry'),
        ),
        migrations.AddField(
            model_name='competitionentryrating',
            name='rater',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='given_ratings', to='talent.person'),
        ),
        migrations.AddField(
            model_name='competitionentry',
            name='bounty',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='competition_entries', to='product_management.bounty'),
        ),
        migrations.AddField(
            model_name='competitionentry',
            name='submitter',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='competition_entries', to='talent.person'),
        ),
        migrations.AddField(
            model_name='competition',
            name='attachments',
            field=models.ManyToManyField(blank=True, to='product_management.fileattachment'),
        ),
        migrations.AddField(
            model_name='competition',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product_management.product'),
        ),
        migrations.AddField(
            model_name='competition',
            name='product_area',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='product_management.productarea'),
        ),
        migrations.AddField(
            model_name='challengedependency',
            name='preceding_challenge',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product_management.challenge'),
        ),
        migrations.AddField(
            model_name='challengedependency',
            name='subsequent_challenge',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='Challenge', to='product_management.challenge'),
        ),
        migrations.AddField(
            model_name='challenge',
            name='attachments',
            field=models.ManyToManyField(blank=True, to='product_management.fileattachment'),
        ),
        migrations.AddField(
            model_name='challenge',
            name='comments_start',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, to='talent.challengecomment'),
        ),
        migrations.AddField(
            model_name='challenge',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='created_by', to='talent.person'),
        ),
        migrations.AddField(
            model_name='challenge',
            name='initiative',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='product_management.initiative'),
        ),
        migrations.AddField(
            model_name='challenge',
            name='product',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='product_management.product'),
        ),
        migrations.AddField(
            model_name='challenge',
            name='product_area',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='product_management.productarea'),
        ),
        migrations.AddField(
            model_name='challenge',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='updated_by', to='talent.person'),
        ),
        migrations.AddField(
            model_name='bug',
            name='person',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='talent.person'),
        ),
        migrations.AddField(
            model_name='bug',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product_management.product'),
        ),
        migrations.AddField(
            model_name='bounty',
            name='attachments',
            field=models.ManyToManyField(blank=True, to='product_management.fileattachment'),
        ),
        migrations.AddField(
            model_name='bounty',
            name='challenge',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='product_management.challenge'),
        ),
        migrations.AddField(
            model_name='bounty',
            name='claimed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='bounty_claimed_by', to='talent.person'),
        ),
        migrations.AddField(
            model_name='bounty',
            name='competition',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='product_management.competition'),
        ),
        migrations.AddField(
            model_name='bounty',
            name='expertise',
            field=models.ManyToManyField(related_name='bounty_expertise', to='talent.expertise'),
        ),
        migrations.AddField(
            model_name='bounty',
            name='skill',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='bounty_skill', to='talent.skill'),
        ),
        migrations.AlterUniqueTogether(
            name='ideavote',
            unique_together={('voter', 'idea')},
        ),
        migrations.AlterUniqueTogether(
            name='competitionentryrating',
            unique_together={('entry', 'rater')},
        ),
    ]
