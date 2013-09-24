"""
    Contains decorators for managers to use
"""

def expose(method='get', output='json', uses_strip=False):
    """
        Decorator factory for exposing a method
    """
    def wrapper(func):
        func.info = {
            'method':  method,
            'output': output
        }
        return func
    return wrapper
