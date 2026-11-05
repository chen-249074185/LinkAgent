class LiepinCliError(Exception):
    """Base error for liepin-cli."""


class MissingTokenError(LiepinCliError):
    """Raised when no token is provided via CLI or environment."""


class InvalidInputError(LiepinCliError):
    """Raised when user input fails validation."""


class RequestError(LiepinCliError):
    """Raised when an API request fails."""


class AuthorizationError(RequestError):
    """Raised when a token is present but unauthorized or expired."""


class BrowserOpenError(LiepinCliError):
    """Raised when the auth page cannot be opened in a browser."""
