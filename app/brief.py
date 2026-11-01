"""The product brief and its rules (spec.md, "Product brief rules"). The page checks the same limits."""
from typing import Annotated

from pydantic import BaseModel, StringConstraints

Required = lambda n: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=n)]  # noqa: E731
Optional_ = lambda n: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=n)]  # noqa: E731


class ProductBrief(BaseModel):
    product_name: Required(80)
    color: Required(40)
    material: Required(40)
    background: Required(80)
    style: Optional_(80) = None
    extra_details: Optional_(300) = None

    def fields(self) -> list[str]:
        """Every filled-in field, for the screener."""
        return [v for v in self.model_dump().values() if v]


class GenerateRequest(BaseModel):
    brief: ProductBrief
    variation: int


class CritiqueRequest(BaseModel):
    id: str            # checked as a UUID4 by store.load before any file is read
