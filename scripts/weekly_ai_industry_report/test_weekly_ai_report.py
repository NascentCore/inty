#!/usr/bin/env python3
"""
Test script for weekly_ai_industry_report.py

This script tests the basic functionality without requiring actual API keys.
"""

import sys
import os
import json
from unittest.mock import patch, MagicMock

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported."""
    try:
        from weekly_ai_industry_report import AIIndustryReporter
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_class_initialization():
    """Test AIIndustryReporter class initialization with mock environment."""
    try:
        # Mock environment variables
        with patch.dict(os.environ, {
            'GOOGLE_CSE_API_KEY': 'test_key',
            'GOOGLE_CSE_ID': 'test_cse_id',
            'GEMINI_API_KEY': 'test_gemini_key'
        }):
            from weekly_ai_industry_report import AIIndustryReporter
            reporter = AIIndustryReporter()
            print("✅ Class initialization successful")
            return True
    except Exception as e:
        print(f"❌ Class initialization error: {e}")
        return False

def test_missing_environment_variables():
    """Test error handling for missing environment variables."""
    try:
        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            from weekly_ai_industry_report import AIIndustryReporter
            reporter = AIIndustryReporter()
            print("❌ Should have raised ValueError for missing env vars")
            return False
    except ValueError as e:
        if "Missing required environment variables" in str(e):
            print("✅ Correctly handles missing environment variables")
            return True
        else:
            print(f"❌ Unexpected error: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error type: {e}")
        return False

def test_search_function_mock():
    """Test search function with mocked Google API."""
    try:
        with patch.dict(os.environ, {
            'GOOGLE_CSE_API_KEY': 'test_key',
            'GOOGLE_CSE_ID': 'test_cse_id',
            'GEMINI_API_KEY': 'test_gemini_key'
        }):
            # Mock the Google API response
            mock_response = {
                'items': [
                    {
                        'title': 'Test AI News 1',
                        'snippet': 'This is a test snippet about AI developments.',
                        'link': 'https://example.com/news1'
                    },
                    {
                        'title': 'Test AI News 2', 
                        'snippet': 'Another test snippet about machine learning.',
                        'link': 'https://example.com/news2'
                    }
                ]
            }
            
            # Mock the build function from googleapiclient.discovery
            with patch('weekly_ai_industry_report.build') as mock_build:
                mock_service = MagicMock()
                mock_cse = MagicMock()
                mock_cse.list.return_value.execute.return_value = mock_response
                mock_service.cse.return_value = mock_cse
                mock_build.return_value = mock_service
                
                from weekly_ai_industry_report import AIIndustryReporter
                reporter = AIIndustryReporter()
                
                results = reporter.search_recent_ai_news("test query", days=7, num_results=5)
                
                if len(results) == 2 and results[0]['title'] == 'Test AI News 1':
                    print("✅ Search function works correctly with mocked data")
                    return True
                else:
                    print(f"❌ Unexpected search results: {results}")
                    return False
                    
    except Exception as e:
        print(f"❌ Search function test error: {e}")
        return False

def test_summarize_function_mock():
    """Test summarize function with mocked Gemini API."""
    try:
        with patch.dict(os.environ, {
            'GOOGLE_CSE_API_KEY': 'test_key',
            'GOOGLE_CSE_ID': 'test_cse_id',
            'GEMINI_API_KEY': 'test_gemini_key'
        }):
            from weekly_ai_industry_report import AIIndustryReporter
            
            # Mock search results
            search_results = [
                {
                    'title': 'Test AI News 1',
                    'snippet': 'This is a test snippet about AI developments.',
                    'url': 'https://example.com/news1'
                }
            ]
            
            reporter = AIIndustryReporter()
            
            # Mock Gemini response
            mock_gemini_response = MagicMock()
            mock_gemini_response.text = "这是一个测试摘要，总结了AI行业的最新发展动态。"
            
            with patch.object(reporter.gemini_model, 'generate_content', return_value=mock_gemini_response):
                summary = reporter.summarize_with_gemini(search_results)
                
                if "测试摘要" in summary:
                    print("✅ Summarize function works correctly with mocked data")
                    return True
                else:
                    print(f"❌ Unexpected summary: {summary}")
                    return False
                    
    except Exception as e:
        print(f"❌ Summarize function test error: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing AI Industry Report Generator")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Class Initialization", test_class_initialization),
        ("Missing Environment Variables", test_missing_environment_variables),
        ("Search Function Mock", test_search_function_mock),
        ("Summarize Function Mock", test_summarize_function_mock)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The script is ready to use.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())