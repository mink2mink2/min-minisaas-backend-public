"""Import all SQLAlchemy models so Base.metadata is fully populated."""

# Core models
from app.models.event_log import EventLog  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.ledger import LedgerRoot, UserChainHash  # noqa: F401

# Domain models
from app.domain.auth.models.user import User  # noqa: F401
from app.domain.auth.models.device import Device  # noqa: F401
from app.domain.auth.models.security_log import SecurityLog  # noqa: F401

# Board models
from app.domain.board.models.category import BoardCategory  # noqa: F401
from app.domain.board.models.post import BoardPost  # noqa: F401
from app.domain.board.models.comment import Comment  # noqa: F401
from app.domain.board.models.like_bookmark import PostLike, PostBookmark, CommentLike  # noqa: F401

# PDF Domain models
from app.domain.pdf.models.pdf_file import PDFFile  # noqa: F401


__all__ = [
    "EventLog",
    "Transaction",
    "LedgerRoot",
    "UserChainHash",
    "User",
    "Device",
    "SecurityLog",
    "BoardCategory",
    "BoardPost",
    "Comment",
    "PostLike",
    "PostBookmark",
    "CommentLike",
    "PDFFile",
]
