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

### Where is the access token? [SOLVED]

It appears that [hiding the `client_id` and `secret`](./GoogleSSOAllAuth.md#how-to-fetch-clusives-client_id-and-secret-from-its-database-solved)
helps to fix the problem.  Other factors might include flushing all records from
Clusive's database of the user and their Google crendentials, and removing
Clusive from the user's Google account -- in short, starting from a state where
the user has never signed into Clusive using Google SSO.  When all of the above
are done, and the user signs into Clusive using their Google account
for the first time, a `Social application token` (`socialaccount_socialtoken`)
is created, for example:
```
id: 5
token: random characters
token_secret: random characters
expires_at: 2021-02-23 22:52:22.551781
account_id: 7
app_id = 1
```
The `account_id` cross references a newly created `Social account` (`socialaccount_socialaccount`)
whose `id` is `7`.  That record cross references the newly created `User` (`auth_user`)
record.  The `app_id` cross references the `id` of the `Social App`
(`socialaccount_socialapp`) whose SSO is being used, here Google.

Background:  The usual dialogue between an OAuth2 server (Google) and consumer
(Clusive) is as follows.  Note that many of these requests have no UI associated
with them and users do not see these transactions.  The requests are a
behind-the-scenes exchange of information between Google and Clusive.

1. Clusive sends the user to Google to log into their Google account,
2. After signing in and confirming what they wish to share with Clusive, Google
   sends a message back to Clusive that the user is authentic,
3. Clusive sends back to Google, "okay", and asks for an access token,
4. Google sends back an access token and possibly a refresh token,
5. Clusive stores the access token somewhere in its database, and uses it going
   forward as credentials for future requests.
  
### Storing Clusive's `client_id` and `secret` in its database [SOLVED]

There are two ways to handle the `client_id` and `secret` created by Google
during registration.  The first, and what is used for development, is to add
the information to `settings.py`.  See, for example, this version of
[`settings.py`](https://github.com/klown/clusive/blob/cb48ea1a811c44eb394fdbd0c1c9fe5cd4dae32b/src/clusive_project/settings.py#L67)
on the `CSL-691-django-allauth` branch.

This technique is not secure since the secret is publicy visible.  In fact, the
Git Guardian bot sent an email warning about the security error, calling it an
"Exposed [`Generic High Entropy Secret`](https://github.com/klown/clusive/commit/eaf604e3cf8d82745472b435d7827efe7c242309#diff-e4a4649d300e50c8be8173ce308974ec7dc9db60bca23233eb017c3840920e53R65)".

The more secure technique is to store the information in a `Social Application`
(`socialaccount_socialapp`) record for Google in Clusive's database.  At the
same time the Clusive host (domain?) is required and can be added to the
"Chosen Sites" list using the `/admin` interface.  When running in development
on localhost, the Clusive host value is `127.0.0.1`.  Note that this matches a
`Sites` (`django_site`) record in terms of that `Site`'s `domain` field.  The
`Site` record, in turn, is identifed in Clusive's `setting.py` using the 
`SITE_ID` environment variable.  In summary:
- `Social Application` (`socialaccount_socialapp`) record:
 - has a list of sites listed in `Chosen sites`; add site via Admin UI
 - for development, add `127.0.0.1` to the `Chosen sites` list.
- `Site` (`django_site`) table:
 - has a record whose `Domain name` (`domain`) matches an item in the
   `Social Application`'s `Chosen sites` list -- see previous bullet.
- `settings.py`
 - the `SITE_ID` variable is set to the `id` of the `Site` record described
   in the previous bullet item.
 - for development, the `id` of the `Site` record is `1`, but can be manually
   reset as needed as long as the `SITE_ID` environment variable matches the
   actual `id` of the `SITE` record. 

With Clusive's database and `settings.py` set up as described, the `client_id`
and `secret` can be left out of `settings.py` for the SSO process.

### How to publish Clusive and/or register it as "Internal"?

For development, Clusive's status with respect to Google registration is
"Testing" and is designated as "External".  Google allows only a set of 100
test users for SSO, maximum for External apps.  When Clusive is production
ready, however, it needs to be verified and published.  Note that the
[verification process](https://support.google.com/cloud/answer/9110914) may be
simple here since Clusive is not requesting access to sensitive nor restricted
scopes.  Still, the issue is what are the consequences when the "PUBLISH APP"
button is pressed during Google's registration process?
