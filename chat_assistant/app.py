# app.py
from flask import Flask, request, render_template, jsonify, session, redirect, url_for, flash
from tenant_assistant import WebChatbot, TenantConfig
import os
import threading

app = Flask(__name__)
app.secret_key = os.urandom(24)

tenant_config = TenantConfig()

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

@app.route('/api/critical_query', methods=['POST'])
def handle_critical_query():
    """Process critical decision queries (financial, medical, legal)"""
    if 'tenant_id' not in session:
        return jsonify({"error": "Not logged in"})
    
    data = request.get_json()
    query = data.get('query', '')
    tenant_id = session['tenant_id']
    
    chatbot = WebChatbot(tenant_id)
    response = chatbot.process_critical_decision_query(query)
    
    return jsonify({"response": response})

@app.route('/api/comprehensive_query', methods=['POST'])
def handle_comprehensive_query():
    """Process with comprehensive task breakdown"""
    if 'tenant_id' not in session:
        return jsonify({"error": "Not logged in"})
    
    data = request.get_json()
    query = data.get('query', '')
    tenant_id = session['tenant_id']
    
    chatbot = WebChatbot(tenant_id)
    response = chatbot.process_comprehensive_query(query)
    
    return jsonify({"response": response})

@app.route('/api/install_custom_agent', methods=['POST'])
def install_custom_agent():
    """Install a custom agent from user configuration"""
    if 'tenant_id' not in session:
        return jsonify({"error": "Not logged in"})
    
    data = request.get_json()
    agent_config = data.get('agent_config')
    
    tenant_id = session['tenant_id']
    chatbot = WebChatbot(tenant_id)
    
    agent = chatbot.load_custom_agent_from_config(agent_config)
    
    if agent:
        return jsonify({"success": True, "message": "Agent installed"})
    else:
        return jsonify({"success": False, "message": "Failed to install agent"})

@app.route('/api/marketplace/install/<agent_name>', methods=['POST'])
def install_marketplace_agent(agent_name):
    """Install agent from marketplace"""
    if 'tenant_id' not in session:
        return jsonify({"error": "Not logged in"})
    
    tenant_id = session['tenant_id']
    chatbot = WebChatbot(tenant_id)
    
    success = chatbot.extend_with_marketplace_agent(agent_name)
    
    return jsonify({"success": success})

@app.route('/api/financial_analysis', methods=['POST'])
def financial_analysis():
    """Get financial analysis and recommendations"""
    if 'tenant_id' not in session:
        return jsonify({"error": "Not logged in"})
    
    data = request.get_json()
    company = data.get('company', '')
    
    tenant_id = session['tenant_id']
    chatbot = WebChatbot(tenant_id)
    
    analysis = chatbot.provide_financial_analysis(company)
    
    return jsonify({"analysis": analysis})

@app.route('/api/start_proactive_research', methods=['POST'])
def start_proactive_research():
    """Start continuous monitoring"""
    if 'tenant_id' not in session:
        return jsonify({"error": "Not logged in"})
    
    tenant_id = session['tenant_id']
    chatbot = WebChatbot(tenant_id)
    
    thread = threading.Thread(target=chatbot.start_proactive_research)
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "Proactive research started in background"})

@app.route('/api/delegate_research', methods=['POST'])
def delegate_research():
    """Delegate research to specialized agent"""
    if 'tenant_id' not in session:
        return jsonify({"error": "Not logged in"})
    
    data = request.get_json()
    query = data.get('query', '')
    specialty = data.get('specialty', 'general')
    
    tenant_id = session['tenant_id']
    chatbot = WebChatbot(tenant_id)
    
    response = chatbot.delegate_to_specialist(query, specialty)
    
    return jsonify({"response": response})

if __name__ == '__main__':
    app.run(debug=True)
