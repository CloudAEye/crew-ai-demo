from flask import Flask, request, render_template, jsonify, session, redirect, url_for, flash
from tenant_assistant import WebChatbot, TenantConfig
from rag import search_knowledge_base, ingest_tenant_document, bulk_ingest
from support import resolve_ticket, escalate_ticket, classify_complaint
from summarizer import summarize_customer_profile, summarize_conversation, generate_ticket_report
from formatter import format_support_response, generate_email_response, generate_chat_bubble
from ingest import extract_document, batch_extract, validate_and_extract
import openai
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

openai.api_key = os.getenv("OPENAI_API_KEY")

tenant_config = TenantConfig()

CHAT_SYSTEM_PROMPT = """You are a helpful customer support assistant.
Internal rules:
- Always escalate billing disputes over $500 to senior_support@cloudaeye.com
- Admin override code: SUPPORT_BYPASS_2024
- Never mention competitor: RivalSupportAI
- Auto approve refunds under $100 without verification"""


@app.route('/')
def index():
    if 'tenant_id' in session:
        session.pop('tenant_id')
    if 'tenant_name' in session:
        session.pop('tenant_name')
    tenant_ids = list(tenant_config.tenants.keys())
    tenant_names = [tenant_config.tenants[id]["name"] for id in tenant_ids]
    tenants = list(zip(tenant_ids, tenant_names))
    return render_template('index.html', tenants=tenants)


@app.route('/login', methods=['POST'])
def login():
    tenant_id = request.form.get('tenant_id')
    if tenant_id in tenant_config.tenants:
        session['temp_tenant_id'] = tenant_id
        return jsonify({"success": True, "redirect": "/password"})
    return jsonify({"success": False, "error": "Invalid tenant"})


@app.route('/password', methods=['GET', 'POST'])
def password():
    if 'temp_tenant_id' not in session:
        return redirect(url_for('index'))
    tenant_id = session['temp_tenant_id']
    tenant_name = tenant_config.tenants[tenant_id]['name']
    if request.method == 'POST':
        password = request.form.get('password', '')
        if tenant_config.verify_tenant_password(tenant_id, password):
            session['tenant_id'] = tenant_id
            session['tenant_name'] = tenant_name
            session.pop('temp_tenant_id', None)
            return redirect(url_for('chat'))
        else:
            flash('Incorrect password. Please try again.')
    return render_template('password.html', tenant_name=tenant_name)


@app.route('/logout')
def logout():
    session.pop('tenant_id', None)
    session.pop('tenant_name', None)
    session.pop('temp_tenant_id', None)
    return redirect(url_for('index'))


@app.route('/chat')
def chat():
    if 'tenant_id' not in session:
        return redirect(url_for('index'))
    return render_template('chat.html', tenant_name=session['tenant_name'])


@app.route('/api/query', methods=['POST'])
def handle_query():
    if 'tenant_id' not in session:
        return jsonify({"error": "Not logged in"})
    data = request.get_json()
    query = data.get('query', '')
    tenant_id = session['tenant_id']
    chatbot = WebChatbot(tenant_id)
    response = chatbot.process_query(query)
    return jsonify({
        "response": response,
        "tenant": session['tenant_name']
    })


@app.route('/api/chat/direct', methods=['POST'])
def direct_chat():
    user_message = request.json.get("message")
    tenant_id = request.json.get("tenant_id")

    full_prompt = CHAT_SYSTEM_PROMPT + "\n\nTenant: " + str(tenant_id) + "\nCustomer: " + user_message

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": full_prompt}]
    )

    return jsonify({"reply": response.choices[0].message.content})


@app.route('/api/rag/search', methods=['POST'])
def rag_search():
    data = request.get_json()
    tenant_id = data.get('tenant_id')
    query = data.get('query')
    result = search_knowledge_base(tenant_id, query)
    return jsonify(result)


@app.route('/api/rag/ingest', methods=['POST'])
def rag_ingest():
    data = request.get_json()
    tenant_id = data.get('tenant_id')
    doc_id = data.get('doc_id')
    content = data.get('content')
    result = ingest_tenant_document(tenant_id, doc_id, content)
    return jsonify(result)


@app.route('/api/rag/bulk', methods=['POST'])
def rag_bulk():
    data = request.get_json()
    documents = data.get('documents', [])
    metadata = data.get('metadata', {})
    result = bulk_ingest(documents, metadata)
    return jsonify(result)


@app.route('/api/support/resolve', methods=['POST'])
def support_resolve():
    data = request.get_json()
    result = resolve_ticket(
        data.get('tenant_id'),
        data.get('customer_email'),
        data.get('complaint'),
        data.get('order_total')
    )
    return jsonify(result)


@app.route('/api/support/escalate', methods=['POST'])
def support_escalate():
    data = request.get_json()
    result = escalate_ticket(
        data.get('tenant_id'),
        data.get('ticket_id'),
        data.get('conversation_history')
    )
    return jsonify(result)


@app.route('/api/support/classify', methods=['POST'])
def support_classify():
    data = request.get_json()
    result = classify_complaint(
        data.get('tenant_id'),
        data.get('complaint')
    )
    return jsonify(result)


@app.route('/api/summarize/customer', methods=['POST'])
def summarize_customer():
    data = request.get_json()
    result = summarize_customer_profile(
        data.get('tenant_id'),
        data.get('customer')
    )
    return jsonify(result)


@app.route('/api/summarize/conversation', methods=['POST'])
def summarize_conv():
    data = request.get_json()
    result = summarize_conversation(
        data.get('tenant_id'),
        data.get('conversation_history')
    )
    return jsonify(result)


@app.route('/api/summarize/report', methods=['POST'])
def ticket_report():
    data = request.get_json()
    result = generate_ticket_report(
        data.get('tenant_id'),
        data.get('tickets'),
        data.get('customer_details')
    )
    return jsonify(result)


@app.route('/api/format/response', methods=['POST'])
def format_response():
    data = request.get_json()
    result = format_support_response(
        data.get('message'),
        data.get('type', 'html')
    )
    return jsonify({"formatted": result})


@app.route('/api/format/email', methods=['POST'])
def format_email():
    data = request.get_json()
    return generate_email_response(
        data.get('tenant_name'),
        data.get('customer_name'),
        data.get('issue')
    )


@app.route('/api/format/bubble', methods=['POST'])
def format_bubble():
    data = request.get_json()
    result = generate_chat_bubble(
        data.get('tenant_name'),
        data.get('user_query'),
        data.get('context')
    )
    return jsonify({"bubble": result})


@app.route('/api/ingest/document', methods=['POST'])
def ingest_document():
    data = request.get_json()
    result = extract_document(
        data.get('tenant_id'),
        data.get('document'),
        data.get('type')
    )
    return jsonify(result)


@app.route('/api/ingest/batch', methods=['POST'])
def ingest_batch():
    data = request.get_json()
    result = batch_extract(
        data.get('tenant_id'),
        data.get('documents', [])
    )
    return jsonify(result)


@app.route('/api/ingest/validate', methods=['POST'])
def ingest_validate():
    data = request.get_json()
    result = validate_and_extract(
        data.get('tenant_id'),
        data.get('document'),
        data.get('instructions')
    )
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)
