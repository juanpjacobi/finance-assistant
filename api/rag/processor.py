from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb

CHROMA_PATH = "./chroma_db"

def get_chroma_collection(document_id: int):
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=f"document_{document_id}",
    )
    return collection

async def process_pdf(file_path: str, document_id: int) -> int:
    reader = PdfReader(file_path)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() or ""

    if not full_text.strip():
        raise ValueError("Could not extract text from PDF")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks = splitter.split_text(full_text)

    collection = get_chroma_collection(document_id)
    collection.add(
        documents=chunks,
        ids=[f"chunk_{document_id}_{i}" for i in range(len(chunks))],
    )

    return len(chunks)
