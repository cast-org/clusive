# Generated by Django 2.2.13 on 2021-03-16 13:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0025_paradata_last_view'),
    ]

    operations = [
        migrations.RenameField(
            model_name='paradata',
            old_name='viewCount',
            new_name='view_count',
        ),
    ]
