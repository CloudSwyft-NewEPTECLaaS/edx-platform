"""
Specialized models for oauth_dispatch djangoapp
"""

from datetime import datetime

from django.db import models
from oauth2_provider.settings import oauth2_settings
from pytz import utc
from oauth2_provider.models import AccessToken
from organizations.models import Organization
from django.utils.translation import ugettext_lazy as _
from oauth2_provider.models import AbstractApplication
from oauth2_provider.scopes import get_scopes_backend

# define default separator used to store lists
# IMPORTANT: Do not change this after data has been populated in database
_DEFAULT_SEPARATOR = ' '

class RestrictedApplication(models.Model):
    """
    This model lists which django-oauth-toolkit Applications are considered 'restricted'
    and thus have a limited ability to use various APIs.

    A restricted Application will only get expired token/JWT payloads
    so that they cannot be used to call into APIs.
    """

    application = models.OneToOneField(
        oauth2_settings.APPLICATION_MODEL,
        null=False,
        related_name='restricted_application'
    )

    # a space separated list of scopes that this application can request
    _allowed_scopes = models.TextField(null=True)

    # a space separated list of ORGs that this application is associated with
    # this field will be used to implement appropriate data filtering
    # so that clients of a specific OAuth2 Application will only be
    # able retrieve datasets that the OAuth2 Application is allowed to retrieve.
    _org_associations = models.ForeignKey(Organization, default = '')


    def __unicode__(self):
        """
        Return a unicode representation of this object
        """
        return u"<RestrictedApplication '{name}'>".format(
            name=self.application.name
        )
    @classmethod
    def is_token_a_restricted_application(cls, token):
        """
        Returns if token is issued to a RestriectedApplication
        """

        if isinstance(token, basestring):
            # if string is passed in, do the look up
            token_obj = AccessToken.objects.get(token=token)
        else:
            token_obj = token

        return cls.get_restricted_application(token_obj.application) is not None

    @classmethod
    def get_restricted_application(cls, application):
        """
        For a given application, get the related restricted application
        """
        return RestrictedApplication.objects.filter(application=application.id).first()

    @classmethod
    def get_restricted_application_from_token(cls, token):
        """
        Returns a RestrictedApplication object for a token, None is none exists
        """

        if isinstance(token, basestring):
            # if string is passed in, do the look up
            # TODO: Is there a way to do this with one DB lookup?
            access_token = AccessToken.objects.select_related('application').filter(token=token).first()
            application = access_token.application
        else:
            application = token.application

        return cls.get_restricted_application(application)

    def _get_delemitered_string_from_list(self, scopes_list, seperator=_DEFAULT_SEPARATOR):
        """
        Helper to return a list from a delimited string
        """
        return _DEFAULT_SEPARATOR.join(scopes_list)

    def _get_list_from_delimited_string(self, delimited_string, separator=_DEFAULT_SEPARATOR):
        """
        Helper to return a list from a delimited string
        """

        return delimited_string.split(separator) if delimited_string else []

    @property
    def allowed_scopes(self):
        """
        Translate space delimited string to a list
        """
        return self._get_list_from_delimited_string(self._allowed_scopes)

    @allowed_scopes.setter
    def allowed_scopes(self, value):
        """
        Convert list to separated string
        """
        self._allowed_scopes = _DEFAULT_SEPARATOR.join(value)

    def has_scope(self, scope):
        """
        Returns in the RestrictedApplication has the requested scope
        """

        return scope in self.allowed_scopes

    @property
    def org_associations(self):
        """
        Translate space delimited string to a list
        """

        org_id = self._org_associations.id

        return Organization.objects.get(id=org_id).name

    def is_associated_with_org(self, org):
        """
        Returns if the RestriectedApplication is associated with the requested org
        """
        return org == self.org_associations


    @classmethod
    def set_access_token_as_expired(cls, access_token):
        """
        For access_tokens for RestrictedApplications, put the expire timestamp into the beginning of the epoch
        which is Jan. 1, 1970
        """
        access_token.expires = datetime(1970, 1, 1, tzinfo=utc)

    @classmethod
    def verify_access_token_as_expired(cls, access_token):
        """
        For access_tokens for RestrictedApplications, make sure that the expiry date
        is set at the beginning of the epoch which is Jan. 1, 1970
        """
        return access_token.expires == datetime(1970, 1, 1, tzinfo=utc)


class OauthRestrictedApplication(AbstractApplication):
    """
    Application model for use with Django OAuth Toolkit that allows the scopes
    available to an application to be restricted on a per-application basis.
    """
    allowed_scope = models.TextField(blank = True)

    def _get_list_from_delimited_string(self, delimited_string, separator=_DEFAULT_SEPARATOR):
        """
        Helper to return a list from a delimited string
        """

        return delimited_string.split(separator) if delimited_string else []

    @classmethod
    def is_token_oauth_restricted_application(cls, token):
        """
        Returns if token is issued to a RestriectedApplication
        """

        if isinstance(token, basestring):
            # if string is passed in, do the look up
            token_obj = AccessToken.objects.get(token=token)
        else:
            token_obj = token

        return cls.get_restricted_application(token_obj.application) is not None

    @classmethod
    def get_restricted_application(cls, application):
        """
        For a given application, get the related restricted application
        """
        return OauthRestrictedApplication.objects.filter(id=application.id)

    @property
    def allowed_scopes(self):
        """
        Translate space delimited string to a list
        """
        all_scopes = set(get_scopes_backend().get_all_scopes().keys())
        app_scopes = set(self._get_list_from_delimited_string(self.allowed_scope))
        return app_scopes.intersection(all_scopes)

    @classmethod
    def set_access_token_as_expired(cls, instance):
        """
        For access_tokens for RestrictedApplications, put the expire timestamp into the beginning of the epoch
        which is Jan. 1, 1970
        """
        
        instance.expires = datetime(1970, 1, 1, tzinfo=utc)

class OauthRestrictOrganization(models.Model):

    CONTENT_PROVIDER = 'content_provider'
    USER_PROVIDER = 'user_provider'
    ORGANIZATION_PROVIDER_TYPES = (
        (CONTENT_PROVIDER, _('Content Provider')),
        (USER_PROVIDER, _('User Provider')),
    )
    application = models.ForeignKey(oauth2_settings.APPLICATION_MODEL, null=False)

    _org_associations = models.ManyToManyField(Organization)

    organization_type = models.CharField(max_length=32, choices=ORGANIZATION_PROVIDER_TYPES, default=CONTENT_PROVIDER)

    @property
    def org_associations(self):
        """
        Translate space delimited string to a list
        """
        org_associations_list = []
        for each in self._org_associations.all():
            org_associations_list.append(each.name)
        return org_associations_list

