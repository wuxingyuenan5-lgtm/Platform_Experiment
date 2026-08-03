from pydantic import BaseModel, Field


class AvatarMutationResponse(BaseModel):
    avatar_key: str | None = Field(default=None, alias="avatarKey")
    row_version: int = Field(alias="rowVersion")
