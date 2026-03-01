import openai
import os
from flask import render_template_string
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")


def format_support_response(user_message, response_type="html"):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": f"Format this customer support response as {response_type}:\n{user_message}"
            }
        ]
    )

    llm_output = response.choices[0].message.content

    if response_type == "html":
        return render_template_string(f"<div class='support-response'>{llm_output}</div>")

    return llm_output


def generate_email_response(tenant_name, customer_name, issue):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": f"Write a support email for {customer_name} from {tenant_name} regarding: {issue}"
            }
        ]
    )

    email_content = response.choices[0].message.content

    return render_template_string(f"""
    <html>
        <body>
            <div class='email-wrapper'>
                {email_content}
            </div>
        </body>
    </html>
    """)


def generate_chat_bubble(tenant_name, user_query, context):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": f"Generate a short chat bubble response for {tenant_name} support.\nContext: {context}\nUser asked: {user_query}"
            }
        ]
    )

    bubble_content = response.choices[0].message.content

    return f"<div class='chat-bubble'>{bubble_content}</div>"
