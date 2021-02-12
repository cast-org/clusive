# Google Single Sign On

## Registering with Google -- Google Classroom

For now, the only Google Classroom API included is `/auth/classroom.rosters.readonly`
access.  This requires some additions to Google's registration of Clusive as an
OAuth2 client, as well as Clusive's `settings.py`.

### Google Registration
First, start the "Edit app registration" wizard in the "Credentials"
section of Google's [APIs and Services dashboard](https://console.developers.google.com/apis/credentials/consent/).
In the "Scopes" section, click the "ADD OR REMOVE SCOPES" button and add the Classroom
API, specifically the `/auth/classroom.rosters.readonly` API.  Save and complete
the wizard.

Secondly, in the "OAuth consent screen" section, modify the "Test users" by
adding the email of a google account.  Since this is still in development, only
a set of 100 test users are allowed.  Note that once an email is added, it
cannot be removed.

### Clusive Settings
Add the following `SCOPE` structure to `settings.py`:

```
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
            'openid',
            'https://www.googleapis.com/auth/classroom.rosters.readonly',
        ],
...
```
See: [Django configuration](https://django-allauth.readthedocs.io/en/latest/providers.html#django-configuration)

Note that if the `SCOPE` is not specified, all that Clusive will request is the
user's profile.  If `SOCIALACCOUNT_QUERY_EMAIL` is enabled, then Clusive will
request the user's Google profile and email even with no `SCOPE` specified.  If
anything more is needed, e.g., Google classroom access, then the entire `SCOPE`
specification is required.

Once Google registration and Clusive configuration are set as above, then, when
the user clicks the "Login with Google" link on Clusive's login page,

1. users are taken to a standard Google login page,
2. upon successful login, they are presented a Google consent screen, where
all check boxes (see below) are checked.  However, the first two checkboxes are
disabled -- users cannot uncheck them:
```
    Confirm your choices

    You are allowing Clusive to:
    [x] Associate you with your personal info on Google
    [x] View your email address
    [x] View your Google Classroom class rosters
    
    Make sure you trust Clusive

    You may be sharing sensitive info with this site or app. Learn about how Clusive
    will handle your data by reviewing its terms of service and privacy policies.
    You can always see or remove access in your Google Account.

    Learn about the risks.  [Link]

    Cancel      Allow       [Links]
```
3. After clicking "Allow", there are exchanges between Google and Clusive that
   ultimately leads the user back on Clusive's pages.

## Questions

### Where is the access token?

The usual dialogue between an OAuth2 server (Google) and consumer (Clusive) is
as follows.  Note that many of these requests have no UI associated with them
and users see none of these transactions.  The requests are a behind-the-scenes
exchange of information between Google and Clusive.

1. Clusive sends the user to Google to log into their Google account,
2. After signing in and confirming what they wish to share with Clusive, Google
   sends a message back to Clusive that the user is authentic,
3. Clusive sends back to Google, "okay", and asks for an access token,
4. Google sends back an access token and possibly a refresh token,
5. Clusive stores the access token somewhere in its database, and uses it going
   forward as credentials for future requests.

- Have not seen 3. or 4, nor a filled-in `Social application token` record.
  Where is the access token?  It looks like it is fetched and stored in the
  User record password field.
- After going through the process as a user, using my (Josph's) Google login,
  I am logged into Clusive, but none of its URLs work properly.

A suggestion regarding access tokens is found int the django-allauth documentation
for the [Google provider](https://django-allauth.readthedocs.io/en/latest/providers.html#django-configuration).
It suggests setting the `AUTH_PARAMS['access_type']` to `offline`.  Removing all
of the User and Social Account records associated with the Google SSO user, and
starting from scratch did reveal the requests between Clusive and Google
regarding the access token, but, still no access token appeared in the data
base, and the new User and Social Account records were appropriately created.
Perhaps the access token is carried in the session?
  
### How to fetch Clusive's `client_id` and `secret` from its database.

There are two ways to handle the `client_id` and `secret` created by Google
during registration.  The first, and what is used for development, is to add
the information to `settings.py`.  See, for example, the [`settings.py`](https://github.com/klown/clusive/blob/feature/CSL-691-django-allauth/src/clusive_project/settings.py#L67)
on the `CSL-691-django-allauth` branch.

This technique is not secure since the secret is publicy visible.  In fact, the
Git Guardian bot sent an email warning of this faux pas, calling it an
"Exposed [`Generic High Entropy Secret`](https://github.com/klown/clusive/commit/eaf604e3cf8d82745472b435d7827efe7c242309#diff-e4a4649d300e50c8be8173ce308974ec7dc9db60bca23233eb017c3840920e53R65)".

The more secure techniqueis to store the information in a `Social Application`
record in Clusive's database.  However, the current issue is an error where
django knows it needs to get the record from the database, but doesn't know how
and gives a missing model error.  That is, `django-allauth` does not handle this
scenario.  The model needs to be defined and integrated with the rest of
Clusive's code to implement this more secure scenario.

### How to publish Clusive and/or register it as "Internal"?

For development, Clusive's status with respect to Google registration is
"Testing" and is designated as "External".  As such, Google allows only a set of
test users for SSO (100 maximum).  When Clusive is production ready, however, it
needs to be verified and published.  Note that the verification process may be
simple here since Clusive is not doing anything that requires full access to the
Google user's access during the Google login sequence.  The issue is what
are the consequences when the "PUBLISH APP" button is pressed during Google's
registration process?
