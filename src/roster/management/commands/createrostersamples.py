from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from roster.models import Site, Period, ClusiveUser, BookshareOrgUserAccount

sample_sites = {
    'cast_collegiate': {
        'name': 'CAST Collegiate',
        'city': 'Wakefield',
        'state_or_province': 'MA',
        'country': 'USA',
        'anon_id': 'site1',
        'timezone': 'America/New_York'
    },
    'idrc_institute': {
        'name': 'IDRC Institute',
        'city': 'Toronto',
        'state_or_province': 'ON',
        'country': 'Canada',
        'anon_id': 'site2',
        'timezone': 'America/New_York'
    }
}

sample_periods = {
    'udl_101': {
        'site_anon_id': 'site1',
        'name': 'UDL101: Introduction to Universal Design for Learning',
        'anon_id': 'period1'
    },
    'udl_201': {
        'site_anon_id': 'site1',
        'name': 'UDL201: Advanced Topics in Universal Design for Learning',
        'anon_id': 'period2'
    },
    'incd_101': {
        'site_anon_id': 'site2',
        'name': 'INCD101: Introduction to Inclusive Design',
        'anon_id': 'period3'
    },
    'incd_201': {
        'site_anon_id': 'site2',
        'name': 'INCD201: Advanced Topics in Inclusive Design',
        'anon_id': 'period4'
    }
}

sample_users = {
    'theresa_teacher': {
        'django_user': {
            'first_name': 'Theresa Teacher',
            'username': 'theresateacher',
            'password': 'theresateacher_pass'
        },
        'clusive_user': {
            'anon_id': 'user1',
            'permission': 'TA',
            'role': 'TE',
            'period_anon_ids': [
                'period1', 'period2'
            ]
        }
    },
    'sam_student': {
        'django_user': {
            'first_name': 'Samuel Student',
            'username': 'samstudent',
            'password': 'samstudent_pass'
        },
        'clusive_user': {
            'anon_id': 'user2',
            'permission': 'TA',
            'role': 'ST',
            'period_anon_ids': [
                'period2'
            ]
        }
    },
    'sarah_student': {
        'django_user': {
            'first_name': 'Sarah Student',
            'username': 'sarahstudent',
            'password': 'sarahstudent_pass'
        },
        'clusive_user': {
            'anon_id': 'user3',
            'permission': 'TA',
            'role': 'ST',
            'period_anon_ids': [
                'period1'
            ]
        }
    },
    'sasha_student': {
        'django_user': {
            'first_name': 'Sasha Student',
            'username': 'sashastudent',
            'password': 'sashastudent_pass'
        },
        'clusive_user': {
            'anon_id': 'user4',
            'permission': 'TA',
            'role': 'ST',
            'period_anon_ids': [
                'period1'
            ]
        }
    },
    'sarah_student': {
        'django_user': {
            'first_name': 'Sal Student',
            'username': 'salstudent',
            'password': 'salstudent_pass'
        },
        'clusive_user': {
            'anon_id': 'user5',
            'permission': 'TA',
            'role': 'ST',
            'period_anon_ids': [
                'period1'
            ]
        }
    },
    'sarah_student': {
        'django_user': {
            'first_name': 'Sal Student',
            'username': 'salstudent',
            'password': 'salstudent_pass'
        },
        'clusive_user': {
            'anon_id': 'user5',
            'permission': 'TA',
            'role': 'ST',
            'period_anon_ids': [
                'period1'
            ]
        }
    },
    # Students that match the demo Bookshare organizational account members
    'chris_student': {
        'django_user': {
            'first_name': 'Chris Student',
            'username': 'chrisstudent',
            'password': 'chrisstudent_pass'
        },
        'clusive_user': {
            'anon_id': 'user6',
            'permission': 'TA',
            'role': 'ST',
            'period_anon_ids': [
                'period1'
            ],
        },
        'bookshareOrgAccounts': [{
            'org_user_id': 'partnerorgdemo@bookshare.org',
            'account_id': 'AP5xvS-6c4EqBiN9y_mYfLhc_MKVStR51Gjk6ZkuwjMz-KlXAlpU1F3MYIngzcF8o-gC1IUInEBv'
        }]
    },
    'pat_student': {
        'django_user': {
            'first_name': 'Pat Student',
            'username': 'patstudent',
            'password': 'patstudent_pass'
        },
        'clusive_user': {
            'anon_id': 'user7',
            'permission': 'TA',
            'role': 'ST',
            'period_anon_ids': [
                'period1'
            ],
        },
        'bookshareOrgAccounts': [{
            'org_user_id': 'partnerorgdemo@bookshare.org',
            'account_id': 'AP5xvS-hsqQ_DO6hlc7FBePAUwFBgowLQ-DhbFNHDr0ibrjLiWPu-QKCgGBNOScBOxaC1jv0rsmG'
        }]
    },
    'sandy_student': {
        'django_user': {
            'first_name': 'Sandy Student',
            'username': 'sandystudent',
            'password': 'sandystudent_pass'
        },
        'clusive_user': {
            'anon_id': 'user8',
            'permission': 'TA',
            'role': 'ST',
            'period_anon_ids': [
                'period1'
            ],
        },
        'bookshareOrgAccounts': [{
            'org_user_id': 'partnerorgdemo@bookshare.org',
            'account_id': 'AP5xvS-A0e5OtsMfuGMa02CriX7AA2S2js1Bp3MjsypYWzLMnUEPfiAQAZsDP4lRWZp1z-qHvd_V'
        }]
    },
}

def create_sites_from_dict(sites_dict):
    for site_id, site_values in sites_dict.items():
        try:
            site = Site.objects.get(anon_id=site_values['anon_id'])
            print("Site with anon_id %s already exists" % site_values['anon_id'])
        except Site.DoesNotExist:
            print("Creating site %s" % site_values['anon_id'])
            Site.objects.create(**site_values)

def create_periods_from_dict(periods_dict):
    for period_id, period_values in periods_dict.items():
        try:
            period = Period.objects.get(anon_id=period_values['anon_id'])
            print("Period with anon_id %s already exists" % period_values['anon_id'])
        except Period.DoesNotExist:
            print("Creating period %s" % period_values['anon_id'])
            matching_site = Site.objects.get(anon_id=period_values['site_anon_id'])
            period_values['site'] = matching_site
            period_values.pop('site_anon_id')
            Period.objects.create(**period_values)

def create_users_from_dict(users_dict):
    for user_id, user_values in users_dict.items():
        try:
            user = ClusiveUser.objects.get(anon_id=user_values['clusive_user']['anon_id'])
            print("User with anon_id %s already exists" % user_values['clusive_user']['anon_id'])
        except ClusiveUser.DoesNotExist:
            print("Creating user %s" % user_values['clusive_user']['anon_id'])
            django_user = User.objects.create_user(**user_values['django_user'])
            periods = []
            for period_anon_id in user_values['clusive_user']['period_anon_ids']:
                period = Period.objects.get(anon_id=period_anon_id)
                periods.append(period)

            user_values['clusive_user'].pop('period_anon_ids')

            clusive_user = ClusiveUser.objects.create(user=django_user, **user_values['clusive_user'])
            clusive_user.periods.set(periods)
            clusive_user.save()

# NOTE:  Run after Users and ClusiveUsers have been created 
def create_bookshare_orgaccounts_from_dict(users_dict):
    for user_id, user_values in users_dict.items():
        bookshareOrgAccounts = user_values.get('bookshareOrgAccounts') 
        if bookshareOrgAccounts == None:
            continue

        anon_id = user_values['clusive_user']['anon_id']
        clusive_user = ClusiveUser.objects.get(anon_id=anon_id)
        for bookshareOrgUser in bookshareOrgAccounts:
            org_id = bookshareOrgUser['org_user_id']
            try:
                bookshare_account = BookshareOrgUserAccount.objects.get(
                    clusive_user=clusive_user, org_user_id=org_id
                )
                print(f'Bookshare organizational account {org_id} for ClusiveUser {anon_id} already exists, skipping.')
            except BookshareOrgUserAccount.DoesNotExist:
                print(f'Creating Bookshare organizational account info for {anon_id}, member of {org_id}')
                bookshare_account = BookshareOrgUserAccount.objects.create(clusive_user=clusive_user, **bookshareOrgUser)
                bookshare_account.save()


class Command(BaseCommand):
    help = 'Create sample objects for the Roster app, for testing purposes'

    def handle(self, *args, **options):

        create_sites_from_dict(sample_sites)

        create_periods_from_dict(sample_periods)

        create_users_from_dict(sample_users)

        create_bookshare_orgaccounts_from_dict(sample_users)


