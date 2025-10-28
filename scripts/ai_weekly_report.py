#!/usr/bin/env python3
"""
AI Weekly Report Launcher

This script provides easy access to the AI Industry Weekly Report Generator
from the main scripts directory.
"""

import sys
import os
from pathlib import Path

# Add the weekly_ai_industry_report directory to the path
script_dir = Path(__file__).parent
weekly_report_dir = script_dir / "weekly_ai_industry_report"
sys.path.insert(0, str(weekly_report_dir))

# Import and run the main function
if __name__ == "__main__":
    try:
        from weekly_ai_industry_report import main

        main()
    except ImportError as e:
        print(f"❌ Error importing weekly report generator: {e}")
        print("Please ensure you're running from the correct directory.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error running weekly report generator: {e}")
        sys.exit(1)
