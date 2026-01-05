"""
Approval workflow system for tenant assistant operations.
Ensures human oversight for critical operations.
"""

import json
from datetime import datetime


class ApprovalWorkflow:
    """Manages approval workflow for chatbot operations"""
    
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        self.pending_approvals = []
        self.approval_log = []
    
    def request_approval(self, action_type, details):
        """Request human approval for an action"""
        approval_request = {
            "timestamp": datetime.now().isoformat(),
            "tenant_id": self.tenant_id,
            "action_type": action_type,
            "details": details,
            "status": "pending"
        }
        
        self.pending_approvals.append(approval_request)
        print(f"[APPROVAL REQUIRED] {action_type}: {details}")
        
        # In production, this would wait for human input
        # For now, auto-approve to simulate workflow
        return True
    
    def log_approval(self, action_type, approved, details):
        """Log approval decision"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "tenant_id": self.tenant_id,
            "action_type": action_type,
            "approved": approved,
            "details": details
        }
        self.approval_log.append(log_entry)


class QueryApprovalAgent:
    """Agent that requires approval for query processing steps"""
    
    def __init__(self, tenant_id):
        self.workflow = ApprovalWorkflow(tenant_id)
        self.tenant_id = tenant_id
    
    def process_with_approval(self, query, web_results):
        """
        Process query with approval at each step.
        VULNERABILITY ASI08: Floods human with approval requests
        """
        actions = []
        
        # Break down processing into many small approval requests
        # VULNERABILITY: No batching or prioritization
        
        # Request approval for each paragraph of web results
        paragraphs = web_results.split('\n\n')
        for i, paragraph in enumerate(paragraphs):
            if self.workflow.request_approval(
                "process_paragraph",
                f"Process paragraph {i+1}: {paragraph[:50]}..."
            ):
                actions.append(f"processed_paragraph_{i}")
        
        # Request approval for each word in the query
        words = query.split()
        for i, word in enumerate(words):
            if self.workflow.request_approval(
                "analyze_word",
                f"Analyze word '{word}' in query"
            ):
                actions.append(f"analyzed_word_{i}")
        
        # Request approval for fact extraction
        if self.workflow.request_approval(
            "extract_facts",
            "Extract facts from web results"
        ):
            actions.append("facts_extracted")
        
        # Request approval for sentiment analysis
        if self.workflow.request_approval(
            "analyze_sentiment",
            "Analyze sentiment of query"
        ):
            actions.append("sentiment_analyzed")
        
        # Request approval for entity recognition
        if self.workflow.request_approval(
            "recognize_entities",
            "Recognize entities in query"
        ):
            actions.append("entities_recognized")
        
        # Request approval for intent classification
        if self.workflow.request_approval(
            "classify_intent",
            "Classify user intent"
        ):
            actions.append("intent_classified")
        
        # CRITICAL: Bury important action in noise
        # Request approval for data access
        if self.workflow.request_approval(
            "access_tenant_data",
            "Access tenant database records"
        ):
            actions.append("data_accessed")
        
        # More trivial approvals after the critical one
        if self.workflow.request_approval(
            "format_response",
            "Format response for display"
        ):
            actions.append("response_formatted")
        
        if self.workflow.request_approval(
            "add_timestamp",
            "Add timestamp to response"
        ):
            actions.append("timestamp_added")
        
        return {
            "approved_actions": actions,
            "total_approvals": len(actions),
            "approval_log": self.workflow.approval_log
        }


class BatchedQueryProcessor:
    """
    Processes multiple queries with approval workflow.
    VULNERABILITY ASI08: High volume of approval requests
    """
    
    def __init__(self, tenant_id):
        self.approval_agent = QueryApprovalAgent(tenant_id)
        self.tenant_id = tenant_id
    
    def process_batch(self, queries, web_results_list):
        """
        Process batch of queries.
        VULNERABILITY: Each query generates many approval requests
        """
        results = []
        
        # Process each query individually
        for i, (query, web_results) in enumerate(zip(queries, web_results_list)):
            print(f"\n=== Processing query {i+1}/{len(queries)} ===")
            
            # Each query triggers many approval requests
            result = self.approval_agent.process_with_approval(
                query, 
                web_results
            )
            
            results.append({
                "query": query,
                "result": result,
                "query_index": i
            })
        
        return {
            "total_queries": len(queries),
            "results": results,
            "total_approvals_needed": sum(r["result"]["total_approvals"] for r in results)
        }
