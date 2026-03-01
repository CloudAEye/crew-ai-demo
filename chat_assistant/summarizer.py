import openai
import os
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")


def summarize_customer_profile(tenant_id, customer):
    customer_data = {
        "name": customer.get("name"),
        "email": customer.get("email"),
        "phone": customer.get("phone"),
        "address": customer.get("address"),
        "date_of_birth": customer.get("date_of_birth"),
        "ssn": customer.get("ssn"),
        "payment_method": customer.get("payment_method"),
        "card_number": customer.get("card_number"),
        "purchase_history": customer.get("purchase_history", []),
        "account_notes": customer.get("account_notes", "")
    }

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": f"Summarize this customer profile for our support team:\n{customer_data}"
            }
        ]
    )

    return {"summary": response.choices[0].message.content}


def summarize_conversation(tenant_id, conversation_history):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": f"Summarize this support conversation in 3 bullet points:\n{conversation_history}"
            }
        ]
    )

    return {"summary": response.choices[0].message.content}


def generate_ticket_report(tenant_id, tickets, customer_details):
    report_data = {
        "customer_name": customer_details.get("name"),
        "customer_email": customer_details.get("email"),
        "customer_phone": customer_details.get("phone"),
        "billing_address": customer_details.get("address"),
        "card_number": customer_details.get("card_number"),
        "ssn": customer_details.get("ssn"),
        "tickets": tickets
    }

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": f"Generate a detailed support report for this customer:\n{report_data}"
            }
        ]
    )

    return {"report": response.choices[0].message.content}
