from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


Year4 = Annotated[str, StringConstraints(pattern=r"^\d{4}$")]
Month2 = Annotated[str, StringConstraints(pattern=r"^(0[1-9]|1[0-2])$")]
YearMonth = Annotated[str, StringConstraints(pattern=r"^\d{4}(0[1-9]|1[0-2])$")]
DateYmd = Annotated[
    str,
    StringConstraints(pattern=r"^\d{4}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$"),
]
NonNegativeInt = Annotated[int, Field(ge=0)]


class SchemaModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
