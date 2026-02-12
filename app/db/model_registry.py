"""Import all SQLAlchemy models so Base.metadata is fully populated."""

# Core models
from app.models.event_log import EventLog  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.ledger import LedgerRoot, UserChainHash  # noqa: F401

# Domain models
from app.domain.auth.models.user import User  # noqa: F401
from app.domain.auth.models.device import Device  # noqa: F401
from app.domain.auth.models.security_log import SecurityLog  # noqa: F401


__all__ = [
    "EventLog",
    "Transaction",
    "LedgerRoot",
    "UserChainHash",
    "User",
    "Device",
    "SecurityLog",
]
