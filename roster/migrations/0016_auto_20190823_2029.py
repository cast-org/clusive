# Generated by Django 2.2.4 on 2019-08-23 20:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('roster', '0015_auto_20190823_2027'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clusiveuser',
            name='periods',
            field=models.ManyToManyField(blank=True, to='roster.Period'),
        ),
    ]
