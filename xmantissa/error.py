# -*- test-case-name: xmantissa.test -*-

"""
Exception definitions for Mantissa.
"""


class ArgumentError(Exception):
    """
    Base class for all exceptions raised by the address parser due to malformed
    input.
    """



class AddressTooLong(ArgumentError):
    """
    Exception raised when an address which exceeds the maximum allowed length
    is given to the parser.
    """



class InvalidAddress(ArgumentError):
    """
    Exception raised when an address is syntactically invalid.
    """



class InvalidTrailingBytes(ArgumentError):
    """
    Exception raised when there are extra bytes at the end of an address.
    """

