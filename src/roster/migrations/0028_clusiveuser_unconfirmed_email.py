# Generated by Django 2.2.13 on 2021-03-19 17:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('roster', '0027_auto_20210217_1114'),
    ]

    operations = [
        migrations.AddField(
            model_name='clusiveuser',
            name='unconfirmed_email',
            field=models.BooleanField(default=False),
        ),
    ]