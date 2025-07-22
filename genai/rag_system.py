"""
GenAI/RAG System for Intelligent Disaster Response Reporting
Uses LangChain for document retrieval and intelligent summarization
"""

from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Qdrant
from langchain.document_loaders import TextLoader, JSONLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain.callbacks import StreamlitCallbackHandler

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Import our vector store
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from vector_search.vector_store import DisasterVectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DisasterRAGSystem:
    """RAG system for intelligent disaster response reporting and Q&A"""
    
    def __init__(self, qdrant_host: str = "localhost", qdrant_port: int = 6333,
                 openai_api_key: Optional[str] = None):
        
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Initialize vector store
        self.vector_store = DisasterVectorStore(host=qdrant_host, port=qdrant_port)
        
        # Initialize LLM
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
            self.llm = ChatOpenAI(
                model_name="gpt-3.5-turbo",
                temperature=0.1,
                max_tokens=1000
            )
        else:
            # Fallback to a local model or mock
            logger.warning("No OpenAI API key provided, using mock LLM")
            self.llm = self._create_mock_llm()
        
        # Initialize document storage
        self.document_collection = "disaster_documents"
        self._setup_document_collection()
        
        # Create chains
        self.qa_chain = None
        self.summary_chain = None
        self._setup_chains()
        
        # Conversation memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        logger.info("RAG system initialized")
    
    def _create_mock_llm(self):
        """Create a mock LLM for testing purposes"""
        class MockLLM:
            def __call__(self, prompt: str) -> str:
                return self._generate_mock_response(prompt)
            
            def _generate_mock_response(self, prompt: str) -> str:
                if "summary" in prompt.lower():
                    return "Based on the available data, there have been multiple disaster events including floods, fires, and severe weather conditions. Emergency response teams are monitoring the situation."
                elif "question" in prompt.lower() or "?" in prompt:
                    return "Based on the retrieved documents, the situation appears to be developing with emergency services responding appropriately."
                else:
                    return "I can help analyze disaster events and provide insights based on available data."
        
        return MockLLM()
    
    def _setup_document_collection(self):
        """Setup Qdrant collection for documents"""
        try:
            self.vector_store.client.create_collection(
                collection_name=self.document_collection,
                vectors_config=VectorParams(
                    size=384,  # MiniLM embedding dimension
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created document collection: {self.document_collection}")
        except Exception as e:
            logger.info(f"Document collection already exists or error: {e}")
    
    def _setup_chains(self):
        """Setup LangChain QA and summarization chains"""
        
        # Custom prompts
        qa_prompt = PromptTemplate(
            template="""
            You are an expert disaster response analyst. Use the following pieces of context 
            to answer the question about disaster events and emergency response.
            
            Context:
            {context}
            
            Question: {question}
            
            Provide a comprehensive answer based on the context. If you cannot answer 
            based on the context, say so clearly.
            
            Answer:
            """,
            input_variables=["context", "question"]
        )
        
        summary_prompt = PromptTemplate(
            template="""
            You are a disaster response coordinator. Create a comprehensive summary 
            of the following disaster events and provide actionable insights.
            
            Disaster Events Data:
            {events}
            
            Create a summary that includes:
            1. Overall situation assessment
            2. Key affected areas and disaster types
            3. Severity levels and trends
            4. Recommended actions for emergency response teams
            5. Areas requiring immediate attention
            
            Summary:
            """,
            input_variables=["events"]
        )
        
        # Store prompts for later use
        self.qa_prompt = qa_prompt
        self.summary_prompt = summary_prompt
        
        logger.info("Chains setup completed")
    
    def index_disaster_documents(self, documents: List[Dict[str, Any]]) -> int:
        """Index disaster-related documents for RAG"""
        
        indexed_count = 0
        
        for doc_data in documents:
            try:
                # Create document text
                doc_text = self._create_document_text(doc_data)
                
                # Split document if it's long
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200,
                    separators=["\n\n", "\n", " ", ""]
                )
                
                chunks = text_splitter.split_text(doc_text)
                
                # Index each chunk
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{doc_data.get('doc_id', 'unknown')}_{i}"
                    
                    # Generate embedding
                    embedding = self.vector_store.embed_text(chunk)
                    
                    # Prepare metadata
                    metadata = {
                        'doc_id': doc_data.get('doc_id', 'unknown'),
                        'doc_type': doc_data.get('doc_type', 'report'),
                        'title': doc_data.get('title', 'Unknown'),
                        'chunk_index': i,
                        'timestamp': doc_data.get('timestamp', datetime.now().isoformat()),
                        'source': doc_data.get('source', 'unknown'),
                        'content': chunk
                    }
                    
                    # Index in vector store
                    from qdrant_client.models import PointStruct
                    point = PointStruct(
                        id=chunk_id,
                        vector=embedding.tolist(),
                        payload=metadata
                    )
                    
                    self.vector_store.client.upsert(
                        collection_name=self.document_collection,
                        points=[point]
                    )
                    
                indexed_count += 1
                
            except Exception as e:
                logger.error(f"Error indexing document {doc_data.get('doc_id')}: {e}")
        
        logger.info(f"Indexed {indexed_count} documents")
        return indexed_count
    
    def _create_document_text(self, doc_data: Dict[str, Any]) -> str:
        """Create searchable text from document data"""
        
        text_parts = []
        
        # Add title
        if 'title' in doc_data:
            text_parts.append(f"Title: {doc_data['title']}")
        
        # Add content
        if 'content' in doc_data:
            text_parts.append(f"Content: {doc_data['content']}")
        
        # Add metadata
        if 'event_type' in doc_data:
            text_parts.append(f"Event Type: {doc_data['event_type']}")
        
        if 'location' in doc_data:
            location = doc_data['location']
            if isinstance(location, dict):
                text_parts.append(f"Location: {location.get('city', 'Unknown')} "
                                f"({location.get('lat', 0)}, {location.get('lon', 0)})")
        
        if 'severity' in doc_data:
            text_parts.append(f"Severity: {doc_data['severity']}")
        
        return "\n".join(text_parts)
    
    def retrieve_relevant_documents(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for a query"""
        
        # Generate query embedding
        query_embedding = self.vector_store.embed_text(query)
        
        # Search in document collection
        search_result = self.vector_store.client.search(
            collection_name=self.document_collection,
            query_vector=query_embedding.tolist(),
            limit=limit
        )
        
        # Process results
        documents = []
        for hit in search_result:
            documents.append({
                'content': hit.payload['content'],
                'metadata': hit.payload,
                'score': hit.score
            })
        
        return documents
    
    def answer_question(self, question: str, context_limit: int = 5) -> Dict[str, Any]:
        """Answer a question using RAG"""
        
        # Retrieve relevant documents
        relevant_docs = self.retrieve_relevant_documents(question, limit=context_limit)
        
        if not relevant_docs:
            return {
                'answer': "I don't have enough information to answer this question.",
                'sources': [],
                'confidence': 0.0
            }
        
        # Prepare context
        context_parts = []
        sources = []
        
        for doc in relevant_docs:
            context_parts.append(doc['content'])
            sources.append({
                'doc_id': doc['metadata']['doc_id'],
                'title': doc['metadata']['title'],
                'score': doc['score']
            })
        
        context = "\n\n".join(context_parts)
        
        # Generate answer using LLM
        try:
            prompt = self.qa_prompt.format(context=context, question=question)
            answer = self.llm(prompt)
            
            # Calculate confidence based on document relevance scores
            avg_score = sum(doc['score'] for doc in relevant_docs) / len(relevant_docs)
            
            return {
                'answer': answer,
                'sources': sources,
                'confidence': float(avg_score),
                'context_used': len(relevant_docs)
            }
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return {
                'answer': "Error generating answer. Please try again.",
                'sources': sources,
                'confidence': 0.0
            }
    
    def generate_situation_report(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive situation report"""
        
        # Get recent events from vector store
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=time_range_hours)
        
        recent_events = self.vector_store.search_by_time_range(
            start_time=start_time,
            end_time=end_time
        )
        
        if not recent_events:
            return {
                'summary': "No recent disaster events to report.",
                'event_count': 0,
                'time_range': f"Last {time_range_hours} hours",
                'generated_at': datetime.now().isoformat()
            }
        
        # Analyze events
        analysis = self._analyze_events(recent_events)
        
        # Generate summary using LLM
        events_text = self._format_events_for_summary(recent_events)
        
        try:
            prompt = self.summary_prompt.format(events=events_text)
            summary = self.llm(prompt)
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            summary = "Error generating summary. Please check system logs."
        
        return {
            'summary': summary,
            'analysis': analysis,
            'event_count': len(recent_events),
            'time_range': f"Last {time_range_hours} hours",
            'generated_at': datetime.now().isoformat(),
            'events': recent_events[:10]  # Include top 10 events
        }
    
    def _analyze_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze disaster events for patterns and insights"""
        
        if not events:
            return {}
        
        # Extract event data
        event_types = [e.get('event', {}).get('event_type', 'unknown') for e in events]
        severities = [e.get('event', {}).get('severity', 'unknown') for e in events]
        locations = [e.get('event', {}).get('location', {}) for e in events]
        
        # Count by type
        type_counts = {}
        for event_type in event_types:
            type_counts[event_type] = type_counts.get(event_type, 0) + 1
        
        # Count by severity
        severity_counts = {}
        for severity in severities:
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Find most affected areas
        city_counts = {}
        for location in locations:
            if isinstance(location, dict) and 'city' in location:
                city = location['city']
                city_counts[city] = city_counts.get(city, 0) + 1
        
        # Identify trends
        high_priority_count = sum(1 for s in severities if s in ['high', 'critical'])
        
        return {
            'total_events': len(events),
            'event_type_distribution': type_counts,
            'severity_distribution': severity_counts,
            'most_affected_areas': dict(sorted(city_counts.items(), 
                                             key=lambda x: x[1], reverse=True)[:5]),
            'high_priority_events': high_priority_count,
            'alert_level': self._determine_alert_level(severity_counts, high_priority_count)
        }
    
    def _format_events_for_summary(self, events: List[Dict[str, Any]]) -> str:
        """Format events for LLM summary generation"""
        
        formatted_events = []
        
        for i, event_data in enumerate(events[:20]):  # Limit to prevent token overflow
            event = event_data.get('event', {})
            
            event_text = f"""
            Event {i+1}:
            - Type: {event.get('event_type', 'Unknown')}
            - Severity: {event.get('severity', 'Unknown')}
            - Location: {event.get('location', {}).get('city', 'Unknown')}
            - Confidence: {event.get('confidence', 0):.2f}
            - Timestamp: {event.get('timestamp', 'Unknown')}
            """
            
            if 'text' in event:
                event_text += f"- Description: {event['text'][:200]}..."
            
            formatted_events.append(event_text)
        
        return "\n".join(formatted_events)
    
    def _determine_alert_level(self, severity_counts: Dict[str, int], 
                              high_priority_count: int) -> str:
        """Determine overall alert level"""
        
        total_events = sum(severity_counts.values())
        
        if total_events == 0:
            return "green"
        
        critical_ratio = severity_counts.get('critical', 0) / total_events
        high_ratio = severity_counts.get('high', 0) / total_events
        
        if critical_ratio > 0.3 or high_priority_count > 10:
            return "red"
        elif critical_ratio > 0.1 or high_ratio > 0.3 or high_priority_count > 5:
            return "orange"
        elif high_ratio > 0.1 or high_priority_count > 2:
            return "yellow"
        else:
            return "green"
    
    def chat_with_system(self, message: str, conversation_id: str = "default") -> Dict[str, Any]:
        """Interactive chat with the disaster response system"""
        
        # Check if this is a specific question that needs RAG
        if any(keyword in message.lower() for keyword in 
               ['what', 'where', 'when', 'how', 'why', 'status', 'report', 'summary']):
            
            return self.answer_question(message)
        
        # Otherwise, provide general assistance
        try:
            response = self.llm(f"""
            You are a disaster response assistant. The user said: "{message}"
            
            Provide a helpful response about disaster response, emergency management, 
            or ask clarifying questions to better assist them.
            """)
            
            return {
                'response': response,
                'type': 'general_assistance',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in chat response: {e}")
            return {
                'response': "I'm having trouble processing your request. Please try again.",
                'type': 'error',
                'timestamp': datetime.now().isoformat()
            }
    
    def create_evacuation_recommendations(self, location: Dict[str, float], 
                                        radius_km: float = 10.0) -> Dict[str, Any]:
        """Create evacuation recommendations based on local disaster events"""
        
        # Get events near the location
        nearby_events = self.vector_store.search_by_location(
            lat=location['lat'],
            lon=location['lon'],
            radius_km=radius_km,
            limit=20
        )
        
        if not nearby_events:
            return {
                'recommendation': 'no_evacuation_needed',
                'reason': 'No disaster events detected in the area',
                'confidence': 0.9
            }
        
        # Analyze threat level
        high_threat_events = [
            e for e in nearby_events 
            if e.get('event', {}).get('severity') in ['high', 'critical']
        ]
        
        if high_threat_events:
            # Find closest high-threat event
            closest_event = min(high_threat_events, key=lambda x: x['distance_km'])
            
            return {
                'recommendation': 'immediate_evacuation',
                'reason': f"High-severity {closest_event['event']['event_type']} "
                         f"detected {closest_event['distance_km']:.1f}km away",
                'confidence': 0.8,
                'closest_threat': closest_event,
                'evacuation_routes': self._suggest_evacuation_routes(location, nearby_events)
            }
        
        # Check for moderate threats
        medium_threat_events = [
            e for e in nearby_events 
            if e.get('event', {}).get('severity') == 'medium'
        ]
        
        if len(medium_threat_events) > 3:
            return {
                'recommendation': 'prepare_for_evacuation',
                'reason': f"Multiple moderate-threat events in area ({len(medium_threat_events)} events)",
                'confidence': 0.7,
                'preparation_steps': [
                    "Prepare emergency supplies",
                    "Identify evacuation routes",
                    "Stay informed about developing situations",
                    "Be ready to evacuate if conditions worsen"
                ]
            }
        
        return {
            'recommendation': 'monitor_situation',
            'reason': 'Low-level threats detected, continue monitoring',
            'confidence': 0.6,
            'monitoring_advice': [
                "Stay updated on local emergency broadcasts",
                "Keep emergency supplies ready",
                "Monitor weather and emergency alerts"
            ]
        }
    
    def _suggest_evacuation_routes(self, location: Dict[str, float], 
                                 threat_events: List[Dict[str, Any]]) -> List[str]:
        """Suggest evacuation routes away from threat areas"""
        
        # This is a simplified version - in reality, would integrate with mapping services
        threat_locations = [
            e.get('location', {}) for e in threat_events 
            if e.get('event', {}).get('severity') in ['high', 'critical']
        ]
        
        suggestions = [
            "Move to higher ground if flooding is a concern",
            "Head away from fire/smoke sources if wildfire detected",
            "Avoid damaged infrastructure if earthquake damage reported",
            "Follow official evacuation routes when available"
        ]
        
        return suggestions

def main():
    """Test the RAG system"""
    
    # Initialize RAG system (without OpenAI key for testing)
    rag = DisasterRAGSystem()
    
    # Test document indexing
    test_documents = [
        {
            'doc_id': 'report_001',
            'title': 'Hurricane Season 2024 Analysis',
            'content': 'Analysis of hurricane patterns and impacts during the 2024 season, including recommendations for improved response protocols.',
            'doc_type': 'analysis_report',
            'event_type': 'hurricane',
            'timestamp': datetime.now().isoformat()
        },
        {
            'doc_id': 'guide_001', 
            'title': 'Flood Response Procedures',
            'content': 'Step-by-step guide for emergency responders dealing with flood situations, including evacuation protocols and resource allocation.',
            'doc_type': 'procedure_guide',
            'event_type': 'flood',
            'timestamp': datetime.now().isoformat()
        }
    ]
    
    # Index documents
    indexed_count = rag.index_disaster_documents(test_documents)
    print(f"Indexed {indexed_count} documents")
    
    # Test Q&A
    test_questions = [
        "What are the hurricane response procedures?",
        "How should we handle flood evacuation?",
        "What resources are needed for disaster response?"
    ]
    
    for question in test_questions:
        print(f"\nQuestion: {question}")
        answer = rag.answer_question(question)
        print(f"Answer: {answer['answer']}")
        print(f"Confidence: {answer['confidence']:.2f}")
    
    # Test situation report
    print("\n--- Situation Report ---")
    report = rag.generate_situation_report(time_range_hours=24)
    print(f"Summary: {report['summary']}")
    print(f"Event Count: {report['event_count']}")
    
    # Test evacuation recommendations
    print("\n--- Evacuation Recommendations ---")
    test_location = {'lat': 25.7617, 'lon': -80.1918}  # Miami
    recommendations = rag.create_evacuation_recommendations(test_location)
    print(f"Recommendation: {recommendations['recommendation']}")
    print(f"Reason: {recommendations['reason']}")

if __name__ == "__main__":
    main()