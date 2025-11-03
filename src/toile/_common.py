"""TODO"""

##
# Imports

import os, sys
from pathlib import Path


##
# Typing shortcuts

_Pathable = str | Path


##
# Contexts

class _SuppressStderrContext:
    """Suppress error printing within the context
    
    USE WITH CAUTION.
    """

    def __init__( self ):
        """Construct a new context manager"""
        pass

    def __enter__( self ):
        sys.stderr = open( os.devnull, 'w' )

    def __exit__( self, exc_type, exc_val, exc_tb ):
        sys.stderr = sys.__stderr__

def suppress_stderr() -> _SuppressStderrContext:
    return _SuppressStderrContext()


#