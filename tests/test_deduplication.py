import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add src to path
# Assuming this file is in <root>/tests, and src is in <root>/src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock dependencies that might not be installed
sys.modules['requests'] = MagicMock()
sys.modules['agentscope'] = MagicMock()
sys.modules['agentscope.agent'] = MagicMock()
sys.modules['agentscope.message'] = MagicMock()
sys.modules['agentscope.model'] = MagicMock()
sys.modules['agentscope.formatter'] = MagicMock()
sys.modules['agentscope.memory'] = MagicMock()
sys.modules['agentscope.tool'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

# Now import the module under test
from src.agents import search_news

class TestDeduplication(unittest.TestCase):
    @patch('src.agents.requests.post')
    @patch('src.agents.SERPER_API_KEY', 'test_key') # Mock API key
    def test_search_news_deduplication(self, mock_post):
        """
        Test that search_news filters out:
        1. Duplicate Titles (normalized)
        2. Duplicate Links
        """
        # Setup mock response with duplicates
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "news": [
                {
                    "title": "Unique News 1",
                    "link": "http://example.com/1",
                    "snippet": "Snippet 1",
                    "source": "Source 1",
                    "date": "2023-10-27"
                },
                {
                    "title": "Unique News 1", # Duplicate Title (Exact match) -> Should be SKIP
                    "link": "http://example.com/2", # Different link
                    "snippet": "Snippet 2",
                    "source": "Source 2",
                    "date": "2023-10-27"
                },
                {
                    "title": "Unique News 2",
                    "link": "http://example.com/1", # Duplicate Link (same as first) -> Should be SKIP
                    "snippet": "Snippet 3",
                    "source": "Source 3",
                    "date": "2023-10-27"
                },
                 {
                    "title": "  unique News 3  ", # Case/whitespace variation -> Should be KEEP
                    "link": "http://example.com/3",
                    "snippet": "Snippet 4",
                    "source": "Source 4",
                    "date": "2023-10-27"
                },
                 {
                    "title": "Unique NEWS 3", # Duplicate of above after normalization -> Should be SKIP
                    "link": "http://example.com/4",
                    "snippet": "Snippet 5",
                    "source": "Source 5",
                    "date": "2023-10-27"
                }
            ]
        }
        mock_post.return_value = mock_response

        # Run function
        results = search_news("query")

        # Verify results
        print("\n=== Test Results ===")
        print(f"Total Items Returned: {len(results)}")
        for i, item in enumerate(results):
            print(f"{i+1}. Title: '{item['title']}' | Link: {item['link']}")

        # Assertions
        # Expecting 2 items: "Unique News 1" and "  unique News 3  "
        self.assertEqual(len(results), 2, "Should have exactly 2 unique items")
        
        self.assertEqual(results[0]['title'], "Unique News 1")
        self.assertEqual(results[0]['link'], "http://example.com/1")
        
        self.assertEqual(results[1]['title'], "  unique News 3  ")
        self.assertEqual(results[1]['link'], "http://example.com/3")

if __name__ == '__main__':
    unittest.main()
