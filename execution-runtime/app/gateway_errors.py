class GatewayConfigurationError(RuntimeError):
    """The configured adapter cannot operate with the current environment or secrets."""


class GatewayQueryUnsupportedError(RuntimeError):
    """The selected external adapter does not support the requested capability."""


class GatewayRequestRejectedError(RuntimeError):
    """The venue deterministically rejected the request before any unknown outcome."""


class GatewayResultUnknownError(RuntimeError):
    """A live request may have reached the venue but its final result is unknown."""
