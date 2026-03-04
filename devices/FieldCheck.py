from dataclasses import dataclass
from typing import Any, Callable, Optional

@dataclass(frozen=True)
class FieldCheck:
    label: str
    left: Callable[[], Any]                 # value from IntuneDevice (or computed)
    right: Callable[[], Any]                # value from TOPdesk dict (or computed)
    normalize: Optional[Callable[[Any], Any]] = None  # optional normalization for both sides