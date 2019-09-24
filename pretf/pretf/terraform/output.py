import sys
import types
from typing import Any

from .base import TerraformBlock


def __getattr__(name: str) -> TerraformBlock:
    return TerraformBlock("output", name)


class ModuleWrapper(types.ModuleType):
    """Workaround to make the module subscriptable."""
    def __init__(self, module: types.ModuleType):
        self._module = module
        self.__dict__.update(module.__dict__)

    def __getattr__(self, name: str) -> Any:
        return self._module.__getattr__(name)

    __getitem__ = __getattr__


sys.modules[__name__] = ModuleWrapper(sys.modules[__name__])
