from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CardResponse(ApiModel):
    id: str
    title: str
    details: str


class ColumnResponse(ApiModel):
    id: str
    title: str
    card_ids: list[str]


class BoardResponse(ApiModel):
    id: str
    columns: list[ColumnResponse]
    cards: dict[str, CardResponse]


class RenameColumnRequest(BaseModel):
    title: str = Field(max_length=80)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title must not be blank")
        return value


class CreateCardRequest(ApiModel):
    column_id: str = Field(min_length=1)
    title: str = Field(max_length=200)
    details: str = Field(default="", max_length=4000)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title must not be blank")
        return value


class EditCardRequest(BaseModel):
    title: str = Field(max_length=200)
    details: str = Field(default="", max_length=4000)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title must not be blank")
        return value


class MoveCardRequest(ApiModel):
    column_id: str = Field(min_length=1)
    position: int = Field(ge=0)
