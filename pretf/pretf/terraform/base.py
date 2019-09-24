from typing import Any, Callable

from pretf.render import Block
from pretf.api import block


class TerraformBlock:
    """Terraform top-level block class."""

    def __init__(self, block_type: str, label: str):
        self.type = block_type
        self.label = label

    def __getattr__(self, name: str) -> Callable:

        def block_body(**kwargs: Any) -> Block:
            return block(self.type, self.label, name, kwargs)

        return block_body

    __getitem__ = __getattr__

    def __call__(self, **kwargs: Any) -> Block:
        """Support blocks without names.

        Support for `provider` and `variable` blocks.

        """
        return block(self.type, self.label, kwargs)
