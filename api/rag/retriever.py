import os
import anthropic
from api.rag.processor import get_chroma_collection
from dotenv import load_dotenv
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

async def query_document(document_id: int, question: str) -> str:
    collection = get_chroma_collection(document_id)
    results = collection.query(
        query_texts=[question],
        n_results=3,
    )

    if not results["documents"] or not results["documents"][0]:
        return "No relevant information found in the document."

    context = "\n\n---\n\n".join(results["documents"][0])

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""You are a financial document assistant.
Answer the question based only on the following document excerpts.
If the answer is not in the excerpts, say so clearly.

Document excerpts:
{context}

Question: {question}""",
            }
        ],
    )

    return message.content[0].text
