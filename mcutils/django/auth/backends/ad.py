"""
python-ldap

### ACTIVE DIRECTORY SETTINGS

# AD_DNS_NAME should set to the AD DNS name of the domain (ie; example.com)
# If you are not using the AD server as your DNS, it can also be set to
# FQDN or IP of the AD server.

AD_DNS_NAME = 'example.com'
AD_LDAP_PORT = 389

AD_SEARCH_DN = 'CN=Users,dc=example,dc=com'

# This is the NT4/Samba domain name
AD_NT4_DOMAIN = 'EXAMPLE'

AD_SEARCH_FIELDS = ['mail', 'givenName', 'sn', 'sAMAccountName']

AD_LDAP_URL = 'ldap://%s:%s' % (AD_DNS_NAME, AD_LDAP_PORT)
"""
import logging
from django.contrib.auth.models import User
from django.conf import settings
try:
    import ldap
except ImportError:
    ldap = None


AD_DNS_NAME = getattr(settings, 'AD_DNS_NAME', '')
AD_LDAP_PORT = getattr(settings, 'AD_LDAP_PORT', 389)
DFAULT_AD_SEARCH_DN = 'CN=Users' + ',dc='.join(('.' + AD_DNS_NAME).split('.'))
AD_NT4_DOMAIN = getattr(settings, 'AD_NT4_DOMAIN',
        AD_DNS_NAME.split('.')[0].upper())
AD_SEARCH_DN = getattr(settings, 'AD_SEARCH_DN', DFAULT_AD_SEARCH_DN)
AD_SEARCH_FIELDS = getattr(settings, 'AD_SEARCH_FIELDS',
        ['mail', 'givenName', 'sn', 'sAMAccountName'])
AD_LDAP_URL = getattr(settings, 'AD_LDAP_URL',
        'ldap://%s:%s' % (AD_DNS_NAME, AD_LDAP_PORT))

logger = logging.getLogger()


class ActiveDirectoryBackend:

    def authenticate(self, username=None, password=None):
        logger.debug('trying to authenticate \"%s\" via Active Directory',
                username)
        if not self.is_valid(username, password):
            return None

        logger.warning('auth backend overwrites auth.User object for %s '
                'with Active Directory data.' % username)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            if ldap is None:
                return None
            user = None

        if not user:
            l = ldap.initialize(AD_LDAP_URL)
            l.simple_bind_s(username, password)
            result = l.search_ext_s(AD_SEARCH_DN, ldap.SCOPE_SUBTREE,
                    'sAMAccountName=%s' % username, AD_SEARCH_FIELDS)[0][1]
            l.unbind_s()

            # givenName == First Name
            if 'givenName' in result:
                first_name = result['givenName'][0]
            else:
                first_name = None

            # sn == Last Name (Surname)
            if 'sn' in result:
                last_name = result['sn'][0]
            else:
                last_name = None

            # mail == Email Address
            if 'mail' in result:
                email = result['mail'][0]
            else:
                email = None

            user = User(username=username, first_name=first_name,
                    last_name=last_name, email=email)
            user.is_staff = False
            user.is_superuser = False
            user.set_password(password)
            user.save()

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def is_valid(self, username=None, password=None):
        ## Disallowing null or blank string as password
        ## as per comment: http://www.djangosnippets.org/snippets/501/#c868
        if not password or ldap is None:
            return False
        binddn = '%s@%s' % (username, AD_NT4_DOMAIN)
        try:
            l = ldap.initialize(AD_LDAP_URL)
            l.simple_bind_s(binddn, password)
            l.unbind_s()
            return True
        except ldap.INVALID_CREDENTIALS:
            logger.info('Active Directory authentication for \"%s\"" failed '
                    '(invalid credentials).', username)
            return False
        except ldap.LDAPError:
            logger.info('Active Directory authentication for \"%s\"" failed.',
                    username)
            return False
