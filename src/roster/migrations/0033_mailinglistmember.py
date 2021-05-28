# Generated by Django 2.2.20 on 2021-05-27 15:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('roster', '0032_auto_20210517_1434'),
    ]

    operations = [
        migrations.CreateModel(
            name='MailingListMember',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sync_date', models.DateTimeField(null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='roster.ClusiveUser')),
            ],
        ),
    ]
