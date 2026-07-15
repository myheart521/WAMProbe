"""WAMProbe-specific exception hierarchy."""


class WAMProbeError(Exception):
    """Base exception for expected WAMProbe failures."""


class UnsupportedCapabilityError(WAMProbeError):
    """Raised when a metric requests a capability the adapter does not expose."""


class ValidationError(WAMProbeError):
    """Raised when benchmark or model data violates the public contract."""
