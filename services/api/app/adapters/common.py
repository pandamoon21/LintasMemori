from __future__ import annotations

from collections.abc import Callable
from typing import Any

ProgressFn = Callable[[float, str], None]
AdapterResult = dict[str, Any]
