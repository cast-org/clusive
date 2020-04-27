# Methods to read a CSV file and return a list of user accounts to create

# Try to thread a path through the various different naming conventions:
# OneRoster: sourcedId, orgSourcedIds (schools), role, email, givenName, familyName, middleName, identifier
# Clusive Model: site, periods, anon_id, permission, username, password, first_name, last_name, email
# CAST Standard: type, site, period, username, password, first name, last name, subjectid, email, permission
from django.contrib import messages

from roster.models import Site, Period, ClusiveUser, ResearchPermissions, Roles

FIELDS = {
    'role':       { 'alt': ['type'], 'required': False,
                    'doc': 'User\'s role: student, teacher, or parent (can be abbreviated to s, t, or p). '
                           'Default: student.'},
    'site':       { 'alt': [], 'required': True,
                    'doc': 'Institution or group this account is connected with (typically name of school).', },
    'period':     { 'alt': [], 'required': True,
                    'doc': 'Class period or subgroup within the site.', },
    'username':   { 'alt': ['user name'], 'required': True,
                    'doc': 'Username for login. Must be globally unique.', },
    'password':   { 'alt': [], 'required': False,
                    'doc': 'Cleartext password. Default: a random password will be assigned.', },
    'first_name': { 'alt': ['first name', 'firstname'], 'required': True,
                    'doc': 'User\'s given name.', },
    'last_name':  { 'alt': ['last name', 'lastname'], 'required': True,
                    'doc': 'User\'s family name.', },
    'email':      { 'alt': [], 'required': False,
                    'doc': 'Email address. Default: none.', },
    'anon_id':    { 'alt': ['anon id', 'anonid', 'subjectid', 'subject id'], 'required': False,
                    'doc': 'Anonymous identifier. Must be globally unique. Default: set to username.', },
    'permission': { 'alt': [], 'required': False,
                    'doc': 'Whether this user\'s data can be used in research.  '
                           'Possible values: pending, permissioned, declined, withdrew, test_account, guest '
                           '(these can be abbreviated to the first 4 letters). Default: test_account.', },
}


def get_field(row, field):
    if row.get(field):
        return row.get(field)
    for alt in FIELDS[field]['alt']:
        if row.get(alt):
            return row.get(alt)
    return None


def parse_file(csvreader):
    """Go through the given CSV DictReader and return information about users, sites, periods it includes.

    Returned dict has two entries: errors, sites and users.
    errors is a string that can be shown to the user explaining errors found.
    Actual creation of users should only be performed if errors is None.

    sites is a dict of sites, pointing to a list of periods they should contain.

    users is a list of user descriptors, in the order they were found in the CSV.
    Each user descriptor will have all the fields necessary to create the user, if valid values were supplied,
    or an error property describing any problems encountered.
    """

    sites = {}
    users = []
    errors = []

    # Read CSV and create list of potential users, checking for problems along the way.
    file_errors = False
    usernames = set()
    anon_ids = set()
    duplicate_usernames = False
    duplicate_anon_ids = False
    for row in csvreader:
        potential_user = parse_row(row)
        users.append(potential_user)
        potential_user = ClusiveUser.add_defaults(potential_user)

        # Check whether it conflicts with anything in database
        uniqueness_errs = ClusiveUser.check_uniqueness_errors(potential_user)
        if uniqueness_errs:
            potential_user['errors'].append(uniqueness_errs)

        # Check if username & anon_id are unique within this file.
        username = potential_user.get('username')
        if username in usernames:
            potential_user['errors'].append('Username previously used in this file')
        else:
            if username:
                usernames.add(username)
        anon_id = potential_user.get('anon_id')
        if anon_id in anon_ids:
            potential_user['errors'].append('Anon_id previously used in this file')
        else:
            if anon_id:
                anon_ids.add(anon_id)

        if potential_user['errors']:
            file_errors = True

        # Record in map of sites and periods
        site_name = potential_user.get('site')
        period_name = potential_user.get('period')
        if site_name:
            site_info = sites.get(site_name)
            if not site_info:
                site_info = { 'periods' : {} }
                sites[site_name] = site_info
            if period_name:
                period_info = site_info['periods'].get(period_name)
                if not period_info:
                    site_info['periods'][period_name] = {}
    if file_errors:
        errors.append('Errors found in file, see table below')

    # Check that sites and periods already exist (currently we don't auto create them)
    site_errors = False
    for site_name, site_info in sites.items():
        if Site.objects.filter(name=site_name).exists():
            for period_name, period_info in site_info['periods'].items():
                if not Period.objects.filter(site__name=site_name, name=period_name).exists():
                    period_info['errors'] = 'Does not exist'
                    site_errors = True
        else:
            site_info['errors'] = 'Does not exist'
            for period_name, period_info in site_info['periods'].items():
                period_info['errors'] = 'Does not exist'
            site_errors = True
    if site_errors:
        errors.append('Create needed sites and/or periods')

    return {
        'errors' : errors,
        'sites': sites,
        'users': users,
    }


def parse_row(row):
    values = { 'errors': [] }
    for name,props in FIELDS.items():
        val = get_field(row, name)
        values[name] = val
        if not val and props['required']:
            values['errors'].append('Missing field: ' + name)
        if val:
            # Clean up string if there is one.
            val = val.strip()
            values[name] = val
            # Do type conversion when necessary
            if name == 'role':
                role = {'s': Roles.STUDENT, 't': Roles.TEACHER, 'p': Roles.PARENT}.get(val[:1].lower())
                if role:
                    values['role'] = role
                else:
                    values['role'] = val
                    values['errors'].append('Role is not a legal value.')
            elif name == 'permission':
                permission = { 'perm': ResearchPermissions.PERMISSIONED,
                               'pend': ResearchPermissions.PENDING,
                               'decl': ResearchPermissions.DECLINED,
                               'with': ResearchPermissions.WITHDREW,
                               'test': ResearchPermissions.TEST_ACCOUNT,
                               'gues': ResearchPermissions.GUEST,
                               }.get(val[:4].lower())
                if permission:
                    values['permission'] = permission
                else:
                    values['errors'].append('Permission is not a legal value.')
        else:
            values[name] = None
    return values
