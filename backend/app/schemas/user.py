from pydantic import BaseModel


# Data required when registering a user
class UserCreate(BaseModel):
    name: str
    username: str
    email: str
    password: str
    bio: str | None = None


# Data returned by the API
class UserResponse(BaseModel):
    id: int
    name: str
    username: str
    email: str
    bio: str | None = None