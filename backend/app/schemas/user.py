from pydantic import BaseModel, Field,EmailStr


# Data required when registering a user
class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    username: str = Field(pattern=r"^[A-Za-z0-9_]{3,30}$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    bio: str | None = Field(default=None, max_length=500)



# Data returned by the API
class UserResponse(BaseModel):
    id: int
    name: str
    username: str
    email: str
    bio: str | None = None