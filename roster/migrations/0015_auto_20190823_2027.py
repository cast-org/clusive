# Generated by Django 2.2.4 on 2019-08-23 20:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('roster', '0014_auto_20190807_1426'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clusiveuser',
            name='periods',
            field=models.ManyToManyField(null=True, to='roster.Period'),
        ),
    ]
