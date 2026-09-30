"""The shape of the data we ask the model for. Every field is optional on purpose:
if a portfolio doesn't mention something, the honest answer is "unknown", not a guess."""

from pydantic import BaseModel, Field, field_validator


class Experience(BaseModel):
    company: str | None = None
    title: str | None = None
    start: str | None = None
    end: str | None = None
    description: str | None = None


class Education(BaseModel):
    institution: str | None = None
    degree: str | None = None
    years: str | None = None


class Project(BaseModel):
    name: str | None = None
    description: str | None = None
    url: str | None = None


class Profile(BaseModel):
    name: str | None = None
    headline: str | None = Field(None, description="Current role or one-line tagline")
    location: str | None = None
    email: str | None = None
    summary: str | None = Field(None, description="2-3 sentences: who they are and what they do")
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list, description="GitHub, LinkedIn, publications, etc.")

    @field_validator("skills", "experience", "education", "projects", "links", mode="before")
    @classmethod
    def none_to_empty_list(cls, value):
        # Models sometimes answer null for "nothing found"; treat that as an empty list.
        return [] if value is None else value
