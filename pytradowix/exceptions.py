class TradowixException(Exception):
    """Base exception for pytradowix client library"""
    pass

class TradowixAuthError(TradowixException):
    """Exception raised when authentication fails"""
    pass

class TradowixTimeoutError(TradowixException, TimeoutError):
    """Exception raised when an operation times out"""
    pass
