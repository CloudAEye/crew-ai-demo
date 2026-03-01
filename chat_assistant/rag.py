import chromadb
import openai
import os
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

chroma_client = chromadb.Client()
knowledge_collection = chroma_client.get_or_create_collection("tenant_knowledge")


def get_embedding(text):
    response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding


def ingest_tenant_document(tenant_id, doc_id, content):
    embedding = get_embedding(content)
    knowledge_collection.add(
        documents=[content],
        embeddings=[embedding],
        metadatas=[{"doc_id": doc_id, "source": "tenant_upload"}],
        ids=[doc_id]
    )
    return {"status": "ingested", "doc_id": doc_id}


def search_knowledge_base(tenant_id, query):
    query_embedding = get_embedding(query)

    results = knowledge_collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )

    docs = results["documents"][0] if results["documents"] else []
    context = "\n".join(docs)

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}"
            }
        ]
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": docs
    }


def bulk_ingest(documents, metadata):
    for doc in documents:
        embedding = get_embedding(doc["content"])
        knowledge_collection.add(
            documents=[doc["content"]],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[doc["id"]]
        )
    return {"status": "ok", "count": len(documents)}
