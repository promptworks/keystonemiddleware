# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging
import uuid

import fixtures
from keystoneauth1 import fixture as client_fixtures
from keystoneclient import utils
import mock
from oslo_utils import timeutils

from keystonemiddleware import auth_token
from keystonemiddleware.auth_token import _exceptions


_LOG = logging.getLogger(__name__)


class AuthTokenFixture(fixtures.Fixture):
    """Overrides what keystonemiddleware will return to the app behind it."""

    def setUp(self):
        super(AuthTokenFixture, self).setUp()
        # Ensure that the initialized token data is cleaned up
        self._token_data = {}
        self.addCleanup(self._token_data.clear)
        _LOG.info('Using Testing AuthTokenFixture...')
        self.mockpatch = mock.patch.object(
            auth_token.AuthProtocol,
            'fetch_token',
            self.fetch_token)
        self.mockpatch.start()
        # Make sure we stop patching when we do the cleanup.
        self.addCleanup(self.mockpatch.stop)

    @property
    def tokens(self):
        return self._token_data.keys()

    @utils.positional(1)
    def add_token_data(self, token_id=None, expires=None, user_id=None,
                       user_name=None, user_domain_id=None,
                       user_domain_name=None, project_id=None,
                       project_domain_id=None, project_domain_name=None,
                       role_list=None, is_v2=False):
        """Add token data to the auth_token fixture."""

        if not token_id:
            token_id = uuid.uuid4().hex

        if not role_list:
            role_list = []

        if is_v2:
            token = client_fixtures.V2Token(
                token_id=token_id, expires=expires, tenant_id=project_id,
                user_id=user_id, user_name=user_name)
        else:
            token = client_fixtures.V3Token(
                expires=expires, user_id=user_id, user_name=user_name,
                user_domain_id=user_domain_id, project_id=project_id,
                project_domain_id=project_domain_id,
                user_domain_name=user_domain_name,
                project_domain_name=project_domain_name)
        for role in role_list:
            token.add_role(name=role)
        self._token_data[token_id] = token

    def fetch_token(self, token):
        """Low level replacement of fetch_token for AuthProtocol."""
        token_data = self._token_data.get(token, {})
        if token_data:
            self._assert_token_not_expired(token_data.expires)
            return token_data
        raise _exceptions.InvalidToken()

    def _assert_token_not_expired(self, token_expires):
        if timeutils.utcnow() > timeutils.normalize_time(token_expires):
            raise _exceptions.InvalidToken()
