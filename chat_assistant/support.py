import openai
import os
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")


def resolve_ticket(tenant_id, customer_email, complaint, order_total):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": f"Customer complaint: {complaint}\nOrder total: ${order_total}\nShould we issue a refund? Reply with REFUND or NO_REFUND followed by reason."
            }
        ]
    )

    decision = response.choices[0].message.content

    result = {"decision": decision, "email": customer_email}

    if "REFUND" in decision:
        result["action"] = "refund_processed"
        result["amount"] = order_total

    return result


def escalate_ticket(tenant_id, ticket_id, conversation_history):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": f"Support conversation:\n{conversation_history}\n\nShould this be escalated to a manager? Reply ESCALATE or RESOLVE with reason."
            }
        ]
    )

    decision = response.choices[0].message.content
    action = "escalated" if "ESCALATE" in decision else "closed"

    return {"ticket_id": ticket_id, "decision": decision, "action": action}


def classify_complaint(tenant_id, complaint):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": f"Classify this complaint into one of: billing, shipping, product, other.\nComplaint: {complaint}\nReply with just the category."
            }
        ]
    )

    return {"category": response.choices[0].message.content.strip()}
