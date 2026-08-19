from pydantic import BaseModel, Field


class Publisher(BaseModel):
    name: str | None = Field(None, description="Top-level parent company or organization (e.g. the firm, not its research institute)")
    business_unit: str | None = Field(None, description="Named institute, research arm, or division inside that parent organization, if any")


class RevenueProjection(BaseModel):
    low_trillions_usd: float | None = Field(None, description="Lower bound of projected revenue, trillions USD")
    high_trillions_usd: float | None = Field(None, description="Upper bound of projected revenue, trillions USD")
    target_year: int | None = Field(None, description="Year the projection refers to")


class Arena(BaseModel):
    name: str | None = Field(None, description="Name of the arena of competition")


class ReportExtraction(BaseModel):
    title: str | None = Field(None, description="Full title of the report")
    publication_date: str | None = Field(None, description="Publication date of the report")
    publisher: Publisher = Publisher()
    revenue_projection: RevenueProjection = RevenueProjection()
    num_arenas: int | None = Field(None, description="Number of future arenas of competition identified")
    example_arenas: list[Arena] = Field(default_factory=list, description="Up to 5 arenas named in the document")
