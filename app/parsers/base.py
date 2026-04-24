from abc import ABC, abstractmethod

from app.schemas.parsed import ParsedMockDraft


class BaseSourceParser(ABC):
    source_slug: str
    parser_version: str = "1.0.0"

    @abstractmethod
    async def discover(self) -> list[str]:
        """Discover potential article URLs."""

    @abstractmethod
    async def fetch(self, url: str) -> str:
        """Fetch article payload."""

    @abstractmethod
    def parse_metadata(self, payload: str, url: str) -> dict[str, object]:
        """Parse draft-level metadata."""

    @abstractmethod
    def parse_picks(self, payload: str) -> list[dict[str, object]]:
        """Parse pick rows from payload."""

    @abstractmethod
    def validate(self, parsed: ParsedMockDraft) -> None:
        """Validate parsed object before persistence."""

    async def parse_article(self, url: str) -> ParsedMockDraft:
        payload = await self.fetch(url)
        metadata = self.parse_metadata(payload, url)
        picks = self.parse_picks(payload)
        parsed = ParsedMockDraft(**metadata, picks=picks)
        self.validate(parsed)
        return parsed
