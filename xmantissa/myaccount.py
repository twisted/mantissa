"""
This module is here to satisfy old databases that contain MyAccount items
"""

from axiom.item import Item
from axiom.upgrade import registerUpgrader

class MyAccount(Item):
    typeName = 'mantissa_myaccount'
    schemaVersion = 2

registerUpgrader(lambda old: None, 'mantissa_myaccount', 1, 2)
