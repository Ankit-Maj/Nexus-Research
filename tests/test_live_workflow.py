import sys
import json
from pathlib import Path
import httpx

def test_live_research():
    print("Testing live research SSE endpoint against local running backend...")
    url = "http://127.0.0.1:8000/research"
    
    payload = {
        "query": "EV battery trends 2026",
        "retrieval_mode": "WEB",
        "length": "Short",
        "session_id": "test_live_session_999"
    }
    
    print(f"Sending POST request to {url} with query: '{payload['query']}'...")
    
    # We will use httpx client to read streaming SSE events
    try:
        with httpx.stream("POST", url, json=payload, timeout=60.0) as response:
            if response.status_code != 200:
                print(f"FAILED: Backend returned status code {response.status_code}")
                # Try to read detail
                print(response.read().decode())
                sys.exit(1)
                
            print("Response established. Reading stream...\n")
            event_type = None
            report_received = False
            
            for line in response.iter_lines():
                if not line.strip():
                    continue
                
                # Check for event header
                if line.startswith("event:"):
                    event_type = line.replace("event:", "").strip()
                elif line.startswith("data:"):
                    data_str = line.replace("data:", "").strip()
                    try:
                        data = json.loads(data_str)
                        if event_type == "report":
                            print(f"\n[SUCCESS] Final Report received! Title: '{data.get('title')}'")
                            print(f"Report ID: {data.get('id')}")
                            print(f"Integrity Score: {data.get('validation', {}).get('overall_integrity_score')}/10.0")
                            print(f"Number of sections: {len(data.get('sections', []))}")
                            print(f"Number of citations: {len(data.get('citations', []))}")
                            report_received = True
                        else:
                            # Standard trace message
                            agent = data.get("agent_name", "Unknown Agent")
                            msg = data.get("message", "")
                            status = data.get("status", "")
                            print(f"[{agent}] Status: {status} | Message: {msg}")
                    except Exception as e:
                        print(f"Error parsing data line: {line}. Error: {e}")
                    # Reset event type for next message
                    event_type = None
            
            if not report_received:
                print("\nFAILED: Finished stream but did not receive event: report.")
                sys.exit(1)
                
            print("\nLive research SSE integration test passed successfully!")
            
    except Exception as e:
        print(f"\nFAILED: Exception occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_live_research()
