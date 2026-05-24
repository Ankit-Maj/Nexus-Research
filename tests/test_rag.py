import sys
from pathlib import Path

# Add root folder to python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.rag.retriever import get_session_store

def run_test():
    print("Testing Hybrid RAG Retriever...")
    session_id = "test_run_123"
    store = get_session_store(session_id)
    
    # Mock documents
    doc_1_content = (
        "Project Orion is a secure multi-agent workflow platform designed for corporate intelligence. "
        "It supports query routing, automatic citations, and PDF report compilation. "
        "The system uses Tavily API for web scraping and FAISS vector databases."
    )
    doc_2_content = (
        "Tesla Q1 2026 financial report shows a record delivery of 500,000 electric vehicles. "
        "Operating profit increased by 14% year-over-year to $4.2 billion, driven by sales of Model Y. "
        "However, gross margins squeezed to 17.5% due to price cuts in China and Europe."
    )
    
    print("\n[Step 1] Ingesting documents...")
    store.add_document("orion_readme.md", doc_1_content, "document")
    store.add_document("tesla_q1_26.pdf", doc_2_content, "document", {"page": 2})
    
    print("\n[Step 2] Testing Hybrid search for keyword 'Tesla operating profit'...")
    results = store.search("Tesla operating profit", top_k=2)
    
    print(f"Retrieved {len(results)} results:")
    for i, r in enumerate(results):
        print(f"Result #{i+1}:")
        print(f"  Source: {r['source_name']} ({r['source_type']})")
        print(f"  Score:  {r['score']}")
        print(f"  Snippet: {r['content'][:100]}...")
        
    assert len(results) > 0, "No results returned."
    assert "tesla" in results[0]["content"].lower(), "Top result does not match query."
    print("\nHybrid RAG tests passed successfully!")

if __name__ == "__main__":
    run_test()
