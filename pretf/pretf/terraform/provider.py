from .base import TerraformBlock


def __getattr__(name: str) -> TerraformBlock:
    return TerraformBlock("provider", name)
