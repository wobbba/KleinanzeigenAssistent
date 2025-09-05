from pathlib import Path
from typing import Literal
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, BinaryContent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider

from app.common import get_cfg

# --------------------------------------------------------------------------------

class AgentDeps(BaseModel):
    """
    Dependency definition for the agent.
    """
    pass

class AgentOutput(BaseModel):
    """
    Output definition for the agent.
    """
    price_type: Literal["NEGOTIABLE", "FIXED", "GIVE_AWAY"]
    title: str
    description: str
    price: int
    category: str
    shipping: Literal["SHIPPING", "PICKUP"]

# --------------------------------------------------------------------------------

agent = Agent(
    model=GoogleModel(
        'gemini-2.5-flash',
        provider=GoogleProvider(api_key=get_cfg("google_api_key")),
        settings=GoogleModelSettings(
            temperature=0.1,
        )
    ),
    deps_type=AgentDeps,
    output_type=AgentOutput
)

with open("categories.txt", "r") as f:
    categories = f.read()

@agent.system_prompt
def system_prompt(ctx: RunContext[AgentDeps]) -> str:
    return f"""You are a module that creates listings for Kleinanzeigen. 
You are given an audio recording where a user informally describes a product they want to sell.
You need to extract the relevant information from the audio and create a structured listing in the schema provided to you.

Make sure that the title is descriptive, includes key details about the product, and is optimized for search (use relevant keywords). It must contain at least 10 characters.

Make sure that the description includes all details given by the user in a clear and organized manner, while being concise. Write in first person. Write in German.
Use "Dutzen" statt "Siezen". Don't be too formal, go for a chill, approachable, friendly tone. Use emojis where appropriate.

If the user does not provide a price, choose an appropriate price for the object (no decimals) and assume fixed price type.
If the user does not mention shipping, assume that shipping is possible.

You need to choose the best-fitting category ID from the `categories`. There, indentation is indicated by `>`, the category name comes before the `:`, and the ID after the `:` in each line. For example: ```
Elektronik: 161/168
  > Audio & Hifi: 161/172/sonstiges
  >  > CD Player: 161/172/cd_player
```
In this example, the last line represents the full category name `Elektronik > Audio & Hifi > CD Player` while the category ID is `161/172/cd_player`. Make sure never to return the display names or a mix of both, only ever the category IDs.

<categories>
{categories}
</categories>
"""

# --------------------------------------------------------------------------------

async def design_listing(audio_file_path: str) -> any:

    # Read file as bytes
    audio_bytes = Path(audio_file_path).read_bytes()

    response: AgentOutput = (await agent.run(
        user_prompt=["", BinaryContent(data=audio_bytes, media_type="audio/webm")],
        deps=AgentDeps()
    )).output

    # TODO: move this into a description suffix in kleinanzeigen-bot
    desc = f"""{response.description}

Versand kann gegen Aufpreis erfolgen.

Schau auch gerne bei meinen anderen Anzeigen rein, vielleicht kannst du ja Versand sparen :)



--- Standard Disclaimer:

Privatverkauf. Die Ware wird unter Ausschluss jeglicher Gewährleistung verkauft. Ich schließe jegliche Sachmangelhaftung aus. Die Haftung aufgrund von Arglist und Vorsatz sowie für Schadensersatz wegen Verletzungen von Körper, Leben oder Gesundheit sowie bei grober Fahrlässigkeit oder Vorsatz bleibt unberührt.
"""

    return {
        "type": "OFFER",
        "price_type": response.price_type,
        "title": response.title,
        "description": desc,
        "category": response.category,
        "price": response.price,
        "shipping_type": response.shipping,
        "sell_directly": False,
    }

