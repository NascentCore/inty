"""
AI Industry Weekly Report Generator

A self-contained tool for generating weekly AI industry reports using
Google Custom Search API and Gemini API.

Main Components:
- weekly_ai_industry_report.py: Main report generator
- test_weekly_ai_report.py: Test suite
- example_usage.py: Usage examples
- README.md: Documentation

Usage:
    from weekly_ai_industry_report import AIIndustryReporter
    
    reporter = AIIndustryReporter()
    report = reporter.generate_weekly_report()
"""

from .weekly_ai_industry_report import AIIndustryReporter

__version__ = "1.0.0"
__author__ = "Inty Team"
__all__ = ["AIIndustryReporter"]