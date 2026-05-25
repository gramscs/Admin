"""Top-level routes package for clearer organization.

This package holds relocated route implementations. Original modules in
`app/main`, `app/track`, `app/pages`, and `app/admin` provide shims that
re-export the implementations to preserve backward compatibility during the
refactor.
"""

__all__ = ["main", "track", "pages", "admin"]
