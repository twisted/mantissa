# Copyright 2006 Divmod, Inc.  See LICENSE file for details

from twisted.trial import unittest
from nevow.testutil import FakeRequest

from xmantissa.websession import usernameFromRequest


class TestUsernameFromRequest(unittest.TestCase):

    def test_domainUnspecified(self):
        """
        Test that L{usernameFromRequest} adds the value of host header to the
        username in the request if the username doesn't already specify a
        domain.
        """
        request = FakeRequest()
        request.setHeader('host', 'divmod.com')
        request.args = {'username': ['joe']}
        username = usernameFromRequest(request)
        self.assertEqual(username, 'joe@divmod.com')


    def test_domainSpecified(self):
        """
        Test that L{usernameFromRequest} returns the username in the request
        if that username specifies a domain.
        """
        request = FakeRequest()
        request.setHeader('host', 'divmod.com')
        request.args = {'username': ['joe@notdivmod.com']}
        username = usernameFromRequest(request)
        self.assertEqual(username, 'joe@notdivmod.com')
