from services.ai.client import GtcAiClient
from services.ai.schema import ParsedTalentProfileSchema


def parse_cv(cv_url: str) -> ParsedTalentProfileSchema:
    client = GtcAiClient()
    response = client.post(
        "accounts/talents/profile/cv/parse",
        params={"url": cv_url},
    )
    data = ParsedTalentProfileSchema(**response.json())
    return data