class GatewayConfigurationError(RuntimeError):
    """The configured adapter cannot operate with the current environment or secrets."""


class GatewayQueryUnsupportedError(RuntimeError):
    """The selected external adapter does not support the requested capability."""
