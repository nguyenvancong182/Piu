"""
Custom exceptions for Piu application.
"""

class SingleInstanceException(BaseException):
    """Custom exception to signal that application is already running."""
    pass

