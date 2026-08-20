from pydantic import BaseModel, Field


class Publisher(BaseModel):
    name: str | None = Field(None, description="Top-level parent company or organization (e.g. the firm, not its research institute)")
    business_unit: str | None = Field(None, description="Named institute, research arm, or division inside that parent organization, if any")


class Range(BaseModel):
    low: float | None = Field(None, description="Lower bound of the range")
    high: float | None = Field(None, description="Upper bound of the range")


class Arena(BaseModel):
    name: str | None = Field(None, description="Name of the arena of competition")
    revenue_2022_billion_usd: float | None = Field(None, description="2022 revenue for this arena, in billions USD; null if not stated")
    revenue_2040_billion_usd: Range = Range()
    growth_rate_pct: Range = Range()


class ReportExtraction(BaseModel):
    title: str | None = Field(None, description="Full title of the report")
    publication_date: str | None = Field(None, description="Publication date of the report")
    publisher: Publisher = Publisher()
    num_arenas: int | None = Field(None, description="Number of future arenas of competition identified")
    arenas: list[Arena] = Field(default_factory=list, description="EVERY future arena of competition in the report, with all its numeric parameters, read from the exhibit tables/charts; do not stop after a few")
