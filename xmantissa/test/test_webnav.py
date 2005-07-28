# Copyright 2005 Divmod, Inc.  See LICENSE file for details

from twisted.trial import unittest

from xmantissa import webnav
from xmantissa.ixmantissa import INavigableElement

class FakeNavigator1(object):
    def getTabs(self):
        return [webnav.Tab('Hello', INavigableElement, 1.,
                           [webnav.Tab('Super', None, 1.0),
                            webnav.Tab('Mega', None, 0.5)])]

class FakeNavigator2(object):
    def getTabs(self):
        return [webnav.Tab('Hello', INavigableElement, 1.,
                           [webnav.Tab('Ultra', None, 0.75),
                            webnav.Tab('Hyper', None, 0.25)]),
                webnav.Tab('Goodbye', None, 0.9)]

class NavConfig(unittest.TestCase):

    avatarDomain = 'nav.example.com'

    def testTabMerge(self):
        nav = webnav.getTabs([FakeNavigator1(),
                              FakeNavigator2()])

        self.assertEquals(
            nav.children[0].name, 'Hello')
        self.assertEquals(
            nav.children[1].name, 'Goodbye')

        kids = [x.name for x in nav.children[0].children]
        self.assertEquals(kids, ['Super', 'Ultra', 'Mega', 'Hyper'])
