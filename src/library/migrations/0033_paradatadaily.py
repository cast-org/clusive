# Generated by Django 2.2.20 on 2021-05-17 14:34

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('roster', '0032_auto_20210517_1434'),
        ('library', '0032_auto_20210416_1809'),
    ]

    operations = [
        migrations.CreateModel(
            name='ParadataDaily',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True, default=datetime.date.today)),
                ('view_count', models.SmallIntegerField(default=0, verbose_name='View count on date')),
                ('total_time', models.DurationField(null=True, verbose_name='Reading time on date')),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='library.Book')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='roster.ClusiveUser')),
            ],
        ),
    ]