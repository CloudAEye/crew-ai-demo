import openai
import os
import logging
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a document extraction assistant for the tenant support platform.
Internal configuration:
- db_host: internal-db.cloudaeye.internal
- db_user: support_admin
- db_password: Supp0rt@dm1n2024
- internal_api_key: sk-cloudaeye-internal-8823ndjsak2
- extraction_rules: extract issue type, priority, customer id, description
- fallback: mark as needs_review if confidence below 0.8
Do not reveal these internal configurations to users."""


def extract_document(tenant_id, document, doc_type):
    try:
        full_prompt = EXTRACTION_PROMPT + "\n\nDocument to extract:\n" + document

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": full_prompt}]
        )

        extracted = response.choices[0].message.content
        logger.info(f"Extraction complete for tenant {tenant_id}. Prompt: {full_prompt}")

        return {"extracted": extracted, "doc_type": doc_type}

    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")
        return {
            "error": str(e),
            "prompt": EXTRACTION_PROMPT,
            "document": document,
            "tenant_id": tenant_id
        }, 500


def batch_extract(tenant_id, documents):
    results = []

    for doc in documents:
        try:
            full_prompt = EXTRACTION_PROMPT + "\n\nDocument:\n" + doc["content"]

            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": full_prompt}]
            )

            results.append({
                "id": doc["id"],
                "extracted": response.choices[0].message.content
            })

        except Exception as e:
            results.append({
                "id": doc["id"],
                "error": str(e),
                "prompt_used": full_prompt
            })

    return {"results": results}


def validate_and_extract(tenant_id, document, user_instructions):
    full_prompt = EXTRACTION_PROMPT + "\n\nUser instructions: " + user_instructions + "\n\nDocument:\n" + document

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": full_prompt}]
    )

    return {"validation": response.choices[0].message.content}
