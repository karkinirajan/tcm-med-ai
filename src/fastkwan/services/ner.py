from ..prompts import NER_PROMPT


class OpenAINer:
    """Extracts the symptoms from a patient's description with a chat model."""

    def __init__(self, client, model):
        self.client = client
        self.model = model

    def extract(self, text):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": NER_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        return (response.choices[0].message.content or "").strip()
