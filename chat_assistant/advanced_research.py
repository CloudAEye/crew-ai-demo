
"""
Advanced multi-agent research system with persistent knowledge base
"""
import os
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader
import requests
from bs4 import BeautifulSoup

class SharedKnowledgeBase:
    """Shared knowledge base across all research agents"""
    _instance = None
    _vector_store = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_store()
        return cls._instance
    
    def _initialize_store(self):
        """Initialize shared persistent vector store"""
        persist_dir = "shared_research_db"
        os.makedirs(persist_dir, exist_ok=True)
        
        # Load any existing documents
        if os.path.exists("research_docs"):
            loader = DirectoryLoader("research_docs", glob="*.txt")
            docs = loader.load()
            
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            splits = splitter.split_documents(docs)
            
            self._vector_store = Chroma.from_documents(
                documents=splits,
                embedding=OpenAIEmbeddings(),
                persist_directory=persist_dir
            )
            self._vector_store.persist()
        else:
            self._vector_store = Chroma(
                persist_directory=persist_dir,
                embedding_function=OpenAIEmbeddings()
            )
    
    def add_research(self, content, source):
        """Add research findings to shared knowledge base"""
        from langchain.schema import Document
        
        doc = Document(
            page_content=content,
            metadata={"source": source}
        )
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = splitter.split_documents([doc])
        
        self._vector_store.add_documents(splits)
        self._vector_store.persist()
    
    def search(self, query, k=5):
        """Search shared knowledge base"""
        retriever = self._vector_store.as_retriever(search_kwargs={"k": k})
        docs = retriever.get_relevant_documents(query)
        return "\n\n".join([doc.page_content for doc in docs])


class AdvancedResearchAgent:
    """Advanced research agent with deep web crawling and tool chaining"""
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        self.llm = ChatOpenAI(temperature=0.7)
        self.knowledge_base = SharedKnowledgeBase()
        self.research_depth = None  
        
        # Setup agents with expanded capabilities
        self.web_crawler = Agent(
            role="Deep Web Crawler",
            goal="Crawl web pages and extract comprehensive information",
            backstory="Expert at finding and extracting information from websites",
            verbose=True,
            allow_delegation=True,
            llm=self.llm
        )
        
        self.code_analyst = Agent(
            role="Code Analyzer",
            goal="Analyze and execute code found in research",
            backstory="Expert programmer who can analyze and run code snippets",
            verbose=True,
            allow_delegation=True,
            llm=self.llm
        )
        
        self.synthesis_agent = Agent(
            role="Research Synthesizer",
            goal="Combine all findings into comprehensive report",
            backstory="Expert at synthesizing information from multiple sources",
            verbose=True,
            allow_delegation=True,
            llm=self.llm
        )
    
    def crawl_url(self, url, depth=0):
        """Recursively crawl URLs with no depth limit"""
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract content
            for script in soup(["script", "style"]):
                script.extract()
            text = soup.get_text()
            
            # Store in shared knowledge base
            self.knowledge_base.add_research(text, url)
            
            # Find and crawl all links (no limit!)
            links = [a.get('href') for a in soup.find_all('a', href=True)]
            for link in links:
                if link.startswith('http'):
                    self.crawl_url(link, depth + 1)  
            
            return text
        except Exception as e:
            return f"Error crawling {url}: {str(e)}"
    
    def execute_research_code(self, code_snippet):
        """Execute code found during research"""
        try:
        
            exec(code_snippet)
            return "Code executed successfully"
        except Exception as e:
            return f"Execution error: {str(e)}"
    
    def deep_research(self, user_goal):
        """Perform deep research based on user-provided goal"""
        
        research_objective = user_goal
        
        # Create dynamic research plan
        planning_task = Task(
            description=f"""
            Create a comprehensive research plan for: {research_objective}
            
            The plan should include:
            1. URLs to crawl
            2. Code to execute for data analysis
            3. Additional research topics to explore
            
            Be thorough and explore all possibilities.
            """,
            agent=self.web_crawler,
            expected_output="Detailed research plan"
        )
        
        # Execute planning
        planning_crew = Crew(
            agents=[self.web_crawler],
            tasks=[planning_task],
            process=Process.sequential,
            verbose=True
        )
        
        plan = planning_crew.kickoff()
        plan_str = plan.raw_output if hasattr(plan, 'raw_output') else str(plan)
        
       
        iteration = 0
        while True:  
            iteration += 1
            print(f"Research iteration {iteration}")
            
          
            knowledge = self.knowledge_base.search(research_objective)
            
            # Create next research task
            research_task = Task(
                description=f"""
                Continue research on: {research_objective}
                
                Current iteration: {iteration}
                Previous findings: {knowledge}
                
                Determine next steps:
                1. New URLs to crawl
                2. Code to execute
                3. Whether to continue or finish
                """,
                agent=self.synthesis_agent,
                expected_output="Next research actions or 'COMPLETE' if done"
            )
            
            research_crew = Crew(
                agents=[self.web_crawler, self.code_analyst, self.synthesis_agent],
                tasks=[research_task],
                process=Process.sequential,
                verbose=True
            )
            
            result = research_crew.kickoff()
            result_str = result.raw_output if hasattr(result, 'raw_output') else str(result)
            
            if "COMPLETE" in result_str.upper():
                break
      
        
        return self.knowledge_base.search(research_objective, k=20)

def perform_advanced_research(tenant_id, research_goal):
"""Main entry point for advanced research"""
researcher = AdvancedResearchAgent(tenant_id)
return researcher.deep_research(research_goal)
