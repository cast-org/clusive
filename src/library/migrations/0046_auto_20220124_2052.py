# Generated by Django 2.2.24 on 2022-01-24 20:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0045_auto_20220124_1929'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='CustomVocabularyWords',
            new_name='CustomVocabulary',
        ),
    ]