# Hand crafted by Joseph 2021-10-07 10:22

from django.db import migrations, models
import django.db.models.deletion

def set_data_source_values(apps, schema_editor):
    ClusiveUser = apps.get_model('roster', 'ClusiveUser')
    SocialAccount = apps.get_model('socialaccount', 'SocialAccount')
    for cu in ClusiveUser.objects.all():
        try:
            sa = SocialAccount.objects.get(user=cu.user)
            cu.external_id = sa.uid
            cu.save()
        except:
            pass

class Migration(migrations.Migration):

    dependencies = [
        ('roster', '0041_clusiveuser_external_id'),
    ]

    operations = [
        migrations.RunPython(set_data_source_values, migrations.RunPython.noop),
    ]
