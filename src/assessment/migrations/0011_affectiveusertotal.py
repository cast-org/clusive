# Generated by Django 2.2.21 on 2021-06-12 09:35

from django.db import migrations, models
import django.db.models.deletion

from assessment.models import affect_words


def update_total(total, check):
    for word in affect_words:
        if getattr(check, word + '_option_response'):
            setattr(total, word, getattr(total, word) + 1)

def create_totals_for_all_users(apps, schema_editor):
    AffectiveCheckResponse = apps.get_model('assessment', 'AffectiveCheckResponse')
    AffectiveUserTotal = apps.get_model('assessment', 'AffectiveUserTotal')
    totes = {}
    for cr in AffectiveCheckResponse.objects.all():
        if not cr.user in totes:
            totes[cr.user] = AffectiveUserTotal(user=cr.user)
        tot = totes[cr.user]
        update_total(tot, cr)
    for tot in totes.values():
        tot.save()


class Migration(migrations.Migration):

    dependencies = [
        ('roster', '0035_userstats_logins'),
        ('assessment', '0010_auto_20210608_1708'),
    ]

    operations = [
        migrations.CreateModel(
            name='AffectiveUserTotal',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('annoyed', models.IntegerField(default=0)),
                ('bored', models.IntegerField(default=0)),
                ('calm', models.IntegerField(default=0)),
                ('confused', models.IntegerField(default=0)),
                ('curious', models.IntegerField(default=0)),
                ('disappointed', models.IntegerField(default=0)),
                ('frustrated', models.IntegerField(default=0)),
                ('happy', models.IntegerField(default=0)),
                ('interested', models.IntegerField(default=0)),
                ('okay', models.IntegerField(default=0)),
                ('sad', models.IntegerField(default=0)),
                ('surprised', models.IntegerField(default=0)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='roster.ClusiveUser')),
            ],
        ),
        migrations.RunPython(create_totals_for_all_users, migrations.RunPython.noop),
    ]