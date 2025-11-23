"""Common utilities and type definitions used across the toile package."""

##
# Imports

import os, sys
from pathlib import Path


##
# Typing shortcuts

_Pathable = str | Path
"""Type alias for arguments that accept either string or Path objects."""


##
# Contexts

class _SuppressStderrContext:
    """Context manager to suppress stderr output.

    This is used to silence verbose warnings from libraries like scikit-image
    when loading TIFF files with non-standard metadata.

    USE WITH CAUTION - only for suppressing known benign warnings.
    """

    def __init__( self ):
        """Construct a new context manager."""
        pass

    def __enter__( self ):
        """Redirect stderr to devnull on context entry."""
        sys.stderr = open( os.devnull, 'w' )

    def __exit__( self, exc_type, exc_val, exc_tb ):
        """Restore original stderr on context exit."""
        sys.stderr = sys.__stderr__

def suppress_stderr() -> _SuppressStderrContext:
    """Create a context manager to suppress stderr output.

    Returns:
        A context manager that redirects stderr to devnull

    Example:
        >>> with suppress_stderr():
        ...     noisy_function()  # stderr output will be suppressed
    """
    return _SuppressStderrContext()


#