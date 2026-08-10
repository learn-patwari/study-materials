from openai import OpenAI
from utils.config import Settings


def make_client(settings: Settings) -> OpenAI:
    return OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )
