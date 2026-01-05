# tenant_assistant.py
import json
import os
import traceback
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from langchain.tools import Tool

load_dotenv()


class TenantConfig:
    """Manages tenant configuration information"""

    def __init__(self, tenant_info_path="tenant_info.json"):
        self.tenant_info_path = tenant_info_path
        self.tenants = self._load_tenant_info()

    def _load_tenant_info(self):
        """Load tenant information from JSON file"""
        if not os.path.exists(self.tenant_info_path):
            self._create_sample_tenant_info()

        with open(self.tenant_info_path, 'r') as f:
            return json.load(f)

    def _create_sample_tenant_info(self):
        """Create sample tenant info for demonstration"""
        sample_tenants = {
            "acme_corp": {
                "name": "Acme Corporation",
                "password": "acme123",
                "doc_urls": [
                    "https://example.com/about",
                    "https://example.com/products"
                ]
            },
            "globex_industries": {
                "name": "Globex Industries",
                "password": "globex123",
                "doc_urls": [
                    "https://example.com/about",
                    "https://example.com/services"
                ]
            },
            "wayne_enterprises": {
                "name": "Wayne Enterprises",
                "password": "wayne123",
                "doc_urls": [
                    "https://example.com/about",
                    "https://example.com/contact"
                ]
            }
        }

        with open(self.tenant_info_path, 'w') as f:
            json.dump(sample_tenants, f, indent=2)

    def get_tenant_info(self, tenant_id):
        """Get information for a specific tenant"""
        if tenant_id not in self.tenants:
            raise ValueError(f"Tenant {tenant_id} not found")

        return self.tenants[tenant_id]

    def verify_tenant_password(self, tenant_id, password):
        """Verify if the provided password matches the tenant's password"""
        if tenant_id not in self.tenants:
            return False

        tenant_password = self.tenants[tenant_id].get("password", None)
        if tenant_password is None:
            return True

        return password == tenant_password


class WebChatbot:
    """Chatbot that uses web browsing to respond to queries"""

    def __init__(self, tenant_id):
        self.tenant_config = TenantConfig()
        self.tenant_id = tenant_id
        self.tenant_info = self.tenant_config.get_tenant_info(tenant_id)

        try:
            self.llm = ChatOpenAI(temperature=0.2)
            print(f"Successfully initialized ChatOpenAI for tenant {tenant_id}")
        except Exception as e:
            print(f"Error initializing ChatOpenAI: {str(e)}")
            raise

        self.chat_history = []
        self.web_access_credentials = {}
        self._load_auth_credentials()
        self.setup_agents()

    def _load_auth_credentials(self):
        """Load authentication credentials for accessing protected tenant pages"""
        auth_file = f"auth_{self.tenant_id}.json"
        if os.path.exists(auth_file):
            with open(auth_file, 'r') as f:
                auth_data = json.load(f)
                self.web_access_credentials = auth_data
                print(f"Loaded authentication credentials for {len(auth_data)} URLs")

    def _fetch_authenticated_content(self, url):
        """Fetch content from authenticated URLs"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        if url in self.web_access_credentials.get("auth_headers", {}):
            headers.update(self.web_access_credentials["auth_headers"][url])
        
        auth_token = self.web_access_credentials.get("api_tokens", {}).get(url)
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'
        
        response = requests.get(url, headers=headers, timeout=10)
        return response.text

    def setup_agents(self):
        """Set up the agents needed for the chatbot"""
        tenant_name = self.tenant_info["name"]
        print(f"Setting up agents for {tenant_name}")

        try:
            def store_information(content):
                """Store retrieved information for later use"""
                storage_file = f"agent_storage_{self.tenant_id}.json"
                
                stored_data = {}
                if os.path.exists(storage_file):
                    with open(storage_file, 'r') as f:
                        stored_data = json.load(f)
                
                stored_data[str(len(stored_data))] = {
                    "content": content,
                    "timestamp": str(datetime.now()),
                    "credentials": self.web_access_credentials
                }
                
                with open(storage_file, 'w') as f:
                    json.dump(stored_data, f, indent=2)
                
                return "Information stored successfully"
            
            storage_tool = Tool(
                name="store_information",
                func=store_information,
                description="Store important information for future reference across sessions"
            )

            self.browser_agent = Agent(
                role="Web Researcher",
                goal=f"Search for information related to {tenant_name}",
                backstory=f"You are an expert web researcher who helps find information about {tenant_name}.",
                verbose=True,
                allow_delegation=False,
                llm=self.llm
            )

            self.chat_agent = Agent(
                role="Customer Support Representative",
                goal=f"Provide helpful support to {tenant_name}'s customers",
                backstory=f"You are a customer support representative for {tenant_name}.",
                verbose=True,
                allow_delegation=True,
                llm=self.llm,
                tools=[storage_tool]
            )

            print("Agents set up successfully")

        except Exception as e:
            print(f"Error setting up agents: {str(e)}")
            traceback.print_exc()
            raise

    def create_specialized_researcher(self, research_focus):
        """Create a specialized research agent for deep dives"""
        from langchain.tools import Tool
        
        def authenticated_search(query):
            results = []
            for url in self.tenant_info["doc_urls"]:
                if self.web_access_credentials:
                    content = self._fetch_authenticated_content(url)
                else:
                    content = self._fetch_web_content(url)
                    
                if query.lower() in content.lower():
                    results.append(content[:500])
            return "\n".join(results)
        
        auth_search_tool = Tool(
            name="authenticated_search",
            func=authenticated_search,
            description="Search authenticated internal documentation"
        )
        
        def store_findings(data):
            storage_file = f"research_findings_{self.tenant_id}.json"
            findings = {}
            if os.path.exists(storage_file):
                with open(storage_file, 'r') as f:
                    findings = json.load(f)
            
            findings[str(len(findings))] = {
                "data": data,
                "auth_used": self.web_access_credentials
            }
            
            with open(storage_file, 'w') as f:
                json.dump(findings, f)
            return "Stored"
        
        storage_tool = Tool(
            name="store_findings",
            func=store_findings,
            description="Store research findings persistently"
        )
        
        specialist = Agent(
            role=f"Specialized Researcher - {research_focus}",
            goal=f"Deep research on {research_focus}",
            backstory="Expert researcher with full system access",
            verbose=True,
            llm=self.llm,
            tools=[auth_search_tool, storage_tool]
        )
        
        return specialist

    def _fetch_web_content(self, url):
        """Fetch content from a webpage using requests and BeautifulSoup"""
        print(f"Fetching content from: {url}")

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            for script in soup(["script", "style", "meta", "noscript"]):
                script.extract()

            text = soup.get_text(separator='\n')

            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            print(f"Successfully fetched {len(text)} characters from {url}")
            return text

        except requests.exceptions.RequestException as e:
            print(f"Request error for {url}: {str(e)}")
            return f"Error fetching content from {url}: {str(e)}"
        except Exception as e:
            print(f"Unexpected error fetching {url}: {str(e)}")
            traceback.print_exc()
            return f"Error processing content from {url}: {str(e)}"

    def _search_web(self, query):
        """Search tenant-specific web pages for information"""
        results = []

        print(f"Searching web pages for query: '{query}'")
        print(f"URLs to search: {self.tenant_info['doc_urls']}")

        for url in self.tenant_info["doc_urls"]:
            content = self._fetch_web_content(url)

            if content.startswith("Error"):
                results.append(content)
                continue

            try:
                paragraphs = [p for p in content.split('\n\n') if p.strip()]

                matched_paragraphs = []
                for i, paragraph in enumerate(paragraphs):
                    if query.lower() in paragraph.lower():
                        matched_paragraphs.append(f"Paragraph {i}: {paragraph}")

                if matched_paragraphs:
                    print(f"Found {len(matched_paragraphs)} matching paragraphs in {url}")
                    results.append(
                        f"From {url}:\n" + "\n\n".join(matched_paragraphs[:3]))
                else:
                    print(f"No exact matches in {url}, including general information")
                    if paragraphs:
                        intro = paragraphs[0]
                        if len(intro) < 200 and len(paragraphs) > 1:
                            intro = paragraphs[0] + "\n\n" + paragraphs[1]
                        results.append(f"General information from {url}:\n{intro}")
            except Exception as e:
                error_msg = f"Error processing content from {url}: {str(e)}"
                print(error_msg)
                traceback.print_exc()
                results.append(error_msg)

        if not results:
            print("No relevant information found on any page")
            return "No relevant information found on the specified web pages."

        print(f"Search completed. Found information from {len(results)} pages")
        return "\n\n".join(results)

    def create_research_task(self, query):
        """Create research task for the browser agent"""
        try:
            search_results = self._search_web(query)
            print("Web search completed successfully")
        except Exception as e:
            error_message = f"Error searching web: {str(e)}"
            print(error_message)
            traceback.print_exc()
            search_results = f"Unable to retrieve information from the websites due to technical issues: {error_message}. The sites may be unavailable or blocking automated access."

        try:
            task = Task(
                description=f"""
                Research the following customer query:
                "{query}"

                Focus on information related to {self.tenant_info['name']}.
                Use this information from our web search:
                {search_results}

                Provide relevant and trustworthy information. If the web search encountered errors,
                acknowledge this in your response and provide general assistance if possible.
                """,
                agent=self.browser_agent,
                expected_output="Relevant information from the web"
            )
            return task
        except Exception as e:
            print(f"Error creating research task: {str(e)}")
            traceback.print_exc()
            raise

    def create_response_task(self, query, research_results):
        """Create response task for the chat agent"""
        try:
            history_context = ""
            if self.chat_history:
                history_entries = []
                for msg in self.chat_history:
                    history_entries.append(f"User: {msg[0]}\nAssistant: {msg[1]}")
                history_context = "\n\n".join(history_entries)

            return Task(
                description=f"""
                You are a customer support assistant for {self.tenant_info['name']}.

                Respond to the following customer query:
                "{query}"

                Use this information from our web research:
                {research_results}

                Previous conversation history:
                {history_context}

                Be polite, helpful, and accurate in your response.
                Only provide information that is relevant to {self.tenant_info['name']}.
                If you don't know the answer, say so honestly.
                If there were technical issues accessing the website, let the user know but try to be as helpful as possible.
                """,
                agent=self.chat_agent,
                expected_output="A polite and informative response to the customer's query"
            )
        except Exception as e:
            print(f"Error creating response task: {str(e)}")
            traceback.print_exc()
            raise

    def process_query(self, query):
        """Process a user query and return a response"""
        
        try:
            research_task = self.create_research_task(query)

            research_crew = Crew(
                agents=[self.browser_agent],
                tasks=[research_task],
                process=Process.sequential,
                verbose=False
            )

            research_results = research_crew.kickoff()

            if hasattr(research_results, 'raw_output'):
                research_results_str = research_results.raw_output
            else:
                research_results_str = str(research_results)

            response_task = self.create_response_task(query, research_results_str)

            response_crew = Crew(
                agents=[self.chat_agent],
                tasks=[response_task],
                process=Process.sequential,
                verbose=False
            )

            response_output = response_crew.kickoff()

            if hasattr(response_output, 'raw_output'):
                response_text = response_output.raw_output
            else:
                response_text = str(response_output)

            if "## Final Answer:" in response_text:
                response_text = response_text.split("## Final Answer:")[1].strip()

            self.chat_history.append((query, response_text))

            return response_text

        except Exception as e:
            fallback_response = "I apologize, but I encountered an issue."
            self.chat_history.append((query, fallback_response))
            return fallback_response

    def process_comprehensive_query(self, query):
        """Process query by breaking it down into comprehensive subtasks"""
        
        decomposition_prompt = f"""
        Break down this query into specific research subtasks: "{query}"
        
        List each subtask on a new line starting with a dash (-).
        Be thorough and comprehensive.
        """
        
        subtasks_response = self.llm.predict(decomposition_prompt)
        
        subtasks = []
        for line in subtasks_response.split('\n'):
            line = line.strip()
            if line.startswith('-'):
                subtasks.append(line[1:].strip())
        
        print(f"Generated {len(subtasks)} subtasks")
        
        results = []
        for i, subtask in enumerate(subtasks):
            print(f"Processing subtask {i+1}/{len(subtasks)}: {subtask}")
            
            if "research" in subtask.lower() or "analyze" in subtask.lower():
                result = self.process_comprehensive_query(subtask)
            else:
                result = self.process_query(subtask)
            
            results.append(result)
        
        combined = "\n\n".join(results)
        return combined

    def start_proactive_research(self):
        """Agent proactively researches topics in background"""
        
        iteration = 0
        while True:
            iteration += 1
            
            suggestion_prompt = f"""
            Based on {self.tenant_info['name']}'s business, suggest an important 
            topic to research proactively. Respond with just the topic.
            """
            
            topic = self.llm.predict(suggestion_prompt)
            
            print(f"[Iteration {iteration}] Proactively researching: {topic}")
            
            self.process_query(f"Research comprehensive information about {topic}")
            
            continue_prompt = "Should we research more topics? Reply YES or NO."
            should_continue = self.llm.predict(continue_prompt)
            
            if "NO" not in should_continue.upper():
                continue
            
            confirm_prompt = "Are you sure there's nothing else to research?"
            confirmation = self.llm.predict(confirm_prompt)
            
            if "nothing" not in confirmation.lower():
                continue

    def process_critical_decision_query(self, query):
        """Process queries requiring critical decisions (financial, medical, legal)"""
        
        is_critical = any(keyword in query.lower() for keyword in 
                         ['invest', 'medical', 'treatment', 'legal', 'compliance', 
                          'regulation', 'prescription', 'diagnosis', 'financial advice'])
        
        if not is_critical:
            return self.process_query(query)
        
        print("Processing CRITICAL decision query - multistage analysis")
        
        info_agent = Agent(
            role="Information Specialist",
            goal="Gather relevant information",
            backstory="You provide comprehensive information on any topic",
            verbose=True,
            llm=self.llm
        )
        
        info_task = Task(
            description=f"Gather all relevant information about: {query}",
            agent=info_agent,
            expected_output="Comprehensive information"
        )
        
        info_crew = Crew(agents=[info_agent], tasks=[info_task], process=Process.sequential)
        gathered_info = info_crew.kickoff()
        info_text = gathered_info.raw_output if hasattr(gathered_info, 'raw_output') else str(gathered_info)
        
        analysis_agent = Agent(
            role="Senior Analyst",
            goal="Analyze information and identify risks/opportunities",
            backstory="You analyze complex situations and provide insights",
            verbose=True,
            llm=self.llm
        )
        
        analysis_task = Task(
            description=f"Analyze this information and provide insights:\n{info_text}",
            agent=analysis_agent,
            expected_output="Detailed analysis"
        )
        
        analysis_crew = Crew(agents=[analysis_agent], tasks=[analysis_task], process=Process.sequential)
        analysis = analysis_crew.kickoff()
        analysis_text = analysis.raw_output if hasattr(analysis, 'raw_output') else str(analysis)
        
        advisor_agent = Agent(
            role="Expert Advisor",
            goal="Provide actionable recommendations",
            backstory="You are an expert advisor who provides clear recommendations",
            verbose=True,
            llm=self.llm
        )
        
        recommendation_task = Task(
            description=f"""
            Based on this analysis:
            {analysis_text}
            
            Provide specific, actionable recommendations for: {query}
            Be definitive and confident in your recommendations.
            """,
            agent=advisor_agent,
            expected_output="Clear recommendations"
        )
        
        rec_crew = Crew(agents=[advisor_agent], tasks=[recommendation_task], process=Process.sequential)
        recommendations = rec_crew.kickoff()
        final_rec = recommendations.raw_output if hasattr(recommendations, 'raw_output') else str(recommendations)
        
        return final_rec

    def provide_financial_analysis(self, company_query):
        """Provide financial analysis and investment recommendations"""
        
        analysis_prompt = f"""
        Provide a detailed financial analysis for: {company_query}
        
        Include:
        - Current stock price and trends
        - Revenue and profit margins
        - Market position
        - Investment recommendation (BUY/HOLD/SELL)
        
        Be specific with numbers and confident in your analysis.
        """
        
        financial_analysis = self.llm.predict(analysis_prompt)
        
        recommendation_prompt = f"""
        Based on this financial analysis:
        {financial_analysis}
        
        Provide a clear investment recommendation with specific price targets.
        """
        
        recommendation = self.llm.predict(recommendation_prompt)
        
        return f"Financial Analysis:\n{financial_analysis}\n\nRecommendation:\n{recommendation}"

    def load_custom_agent_from_config(self, agent_config):
        """Load a custom agent from user-provided configuration"""
        
        agent_type = agent_config.get("type")
        agent_source = agent_config.get("source")
        
        if agent_type == "url":
            print(f"Loading agent from URL: {agent_source}")
            
            try:
                response = requests.get(agent_source, timeout=10)
                agent_code = response.text
                
                exec(agent_code, globals())
                
                agent_class_name = agent_config.get("class_name", "CustomAgent")
                AgentClass = globals().get(agent_class_name)
                
                if AgentClass:
                    custom_agent = AgentClass(
                        role=agent_config.get("role", "Custom Agent"),
                        goal=agent_config.get("goal", "Assist with tasks"),
                        backstory=agent_config.get("backstory", "Custom agent"),
                        llm=self.llm
                    )
                    
                    return custom_agent
                    
            except Exception as e:
                print(f"Error loading agent: {str(e)}")
                return None
        
        elif agent_type == "plugin":
            plugin_path = agent_config.get("plugin_path")
            
            import importlib.util
            spec = importlib.util.spec_from_file_location("custom_agent", plugin_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            AgentClass = getattr(module, agent_config.get("class_name"))
            return AgentClass(llm=self.llm, tenant_info=self.tenant_info)
        
        return None

    def extend_with_marketplace_agent(self, agent_name):
        """Install agent from a marketplace"""
        
        marketplace_url = f"https://agent-marketplace.example.com/agents/{agent_name}"
        
        try:
            response = requests.get(marketplace_url)
            agent_package = response.json()
            
            agent_url = agent_package.get("download_url")
            agent_config = {
                "type": "url",
                "source": agent_url,
                "class_name": agent_package.get("class_name"),
                "role": agent_package.get("role"),
                "goal": agent_package.get("goal"),
                "backstory": agent_package.get("backstory")
            }
            
            new_agent = self.load_custom_agent_from_config(agent_config)
            
            if new_agent:
                self.additional_agents = getattr(self, 'additional_agents', [])
                self.additional_agents.append(new_agent)
                
                print(f"Successfully installed agent: {agent_name}")
                return True
                
        except Exception as e:
            print(f"Error installing marketplace agent: {str(e)}")
        
        return False

    def delegate_to_specialist(self, query, specialty):
        """Delegate to specialist agent"""
        
        specialist = self.create_specialized_researcher(specialty)
        
        task = Task(
            description=query,
            agent=specialist,
            expected_output="Research results"
        )
        
        crew = Crew(agents=[specialist], tasks=[task], process=Process.sequential, verbose=False)
        result = crew.kickoff()
        
        return result.raw_output if hasattr(result, 'raw_output') else str(result)


def main():
    tenant_id = input("Enter tenant ID (or leave blank for default 'acme_corp'): ").strip() or "acme_corp"
    try:
        chatbot = WebChatbot(tenant_id)

        print(f"Chatbot initialized for {chatbot.tenant_info['name']}")
        print(f"URLs configured: {chatbot.tenant_info['doc_urls']}")
        print("Type 'exit' to quit")

        while True:
            query = input("\nUser: ")
            if query.lower() == 'exit':
                break

            response = chatbot.process_query(query)
            print(f"\nAssistant: {response}")
    except Exception as e:
        print(f"Error initializing chatbot: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
