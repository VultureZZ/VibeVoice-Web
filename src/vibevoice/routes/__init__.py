"""API routes for VibeVoice."""

def __getattr__(name):
    """Lazy load route modules to avoid circular imports."""
    if name == "podcast":
        from . import podcast
        return podcast
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
