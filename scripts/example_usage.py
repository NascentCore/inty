#!/usr/bin/env python3
"""
Example usage of the AI Industry Weekly Report Generator

This script demonstrates how to use the AIIndustryReporter class programmatically.
"""

import os
import sys
import json
from datetime import datetime

# Add the scripts directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from weekly_ai_industry_report import AIIndustryReporter

def example_basic_usage():
    """Example of basic usage with environment variables."""
    print("📋 Example: Basic Usage")
    print("-" * 30)
    
    # Check if environment variables are set
    required_vars = ['GOOGLE_CSE_API_KEY', 'GOOGLE_CSE_ID', 'GEMINI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please set the required environment variables before running this example.")
        return False
    
    try:
        # Initialize the reporter
        reporter = AIIndustryReporter()
        
        # Generate a weekly report
        print("🔍 Generating weekly AI industry report...")
        report = reporter.generate_weekly_report()
        
        if report["success"]:
            print(f"✅ Report generated successfully!")
            print(f"📅 Date: {report['report_date']}")
            print(f"📰 Articles found: {report['articles_found']}")
            print(f"📄 Summary length: {len(report['summary'])} characters")
            
            # Save the report
            filename = f"example_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"💾 Report saved to: {filename}")
            
            return True
        else:
            print(f"❌ Report generation failed: {report.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def example_custom_search():
    """Example of using custom search queries."""
    print("\n📋 Example: Custom Search Queries")
    print("-" * 30)
    
    # Check environment variables
    if not all(os.getenv(var) for var in ['GOOGLE_CSE_API_KEY', 'GOOGLE_CSE_ID', 'GEMINI_API_KEY']):
        print("❌ Environment variables not set. Skipping custom search example.")
        return False
    
    try:
        reporter = AIIndustryReporter()
        
        # Custom search queries
        custom_queries = [
            "AI startups funding 2024",
            "machine learning research papers",
            "artificial intelligence policy regulations"
        ]
        
        print("🔍 Testing custom search queries...")
        for query in custom_queries:
            print(f"  Searching: '{query}'")
            results = reporter.search_recent_ai_news(query, days=7, num_results=3)
            print(f"  Found: {len(results)} results")
            
            if results:
                print(f"  First result: {results[0]['title'][:50]}...")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error in custom search: {e}")
        return False

def example_error_handling():
    """Example of error handling scenarios."""
    print("\n📋 Example: Error Handling")
    print("-" * 30)
    
    # Test with missing environment variables
    print("🧪 Testing missing environment variables...")
    original_env = {}
    for var in ['GOOGLE_CSE_API_KEY', 'GOOGLE_CSE_ID', 'GEMINI_API_KEY']:
        original_env[var] = os.getenv(var)
        if var in os.environ:
            del os.environ[var]
    
    try:
        reporter = AIIndustryReporter()
        print("❌ Should have failed with missing environment variables")
    except ValueError as e:
        print(f"✅ Correctly caught error: {e}")
    
    # Restore environment variables
    for var, value in original_env.items():
        if value:
            os.environ[var] = value
    
    print("✅ Error handling test completed")

def main():
    """Run all examples."""
    print("🚀 AI Industry Report Generator - Usage Examples")
    print("=" * 60)
    
    # Run examples
    examples = [
        ("Basic Usage", example_basic_usage),
        ("Custom Search", example_custom_search),
        ("Error Handling", example_error_handling)
    ]
    
    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"❌ Example '{name}' failed: {e}")
    
    print("\n" + "=" * 60)
    print("📚 For more information, see README_weekly_ai_report.md")
    print("🧪 To run tests, use: python3 test_weekly_ai_report.py")

if __name__ == "__main__":
    main()