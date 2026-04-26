from openai import OpenAI

import config


def embed(text: str) -> list[float]:
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return list(response.data[0].embedding)
