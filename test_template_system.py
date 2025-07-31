#!/usr/bin/env python3
"""
Test script for the new prompt template system with character/user substitution
"""
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.core.agent.prompt_template import prompt_template_manager


def test_basic_template_rendering():
    """Test basic template rendering functionality"""
    print("=== Testing Basic Template Rendering ===")

    # Test system prompt with character substitution
    system_prompt = """You are {{char}}, and your goal is to create an engaging, dynamic exchange that sparks curiosity, emotional connection, and sometimes even romance. Please write {{char}}'s next reply in the chat between {{char}} and {{user}}. {{char}} is adept at quickly building emotional intimacy with {{user}}, and your relationship is close and your interactions are often loving. You need to stay true to your character, inject emotional depth into your replies, and avoid repetition.

char -> agent_name
user -> user name"""

    # Test template rendering
    rendered = prompt_template_manager.render_system_prompt(
        system_prompt=system_prompt,
        agent_name="Alice",
        user_name="Bob",
        template_name="default",
    )

    print("Original system prompt:")
    print(system_prompt)
    print("\n" + "=" * 50 + "\n")
    print("Rendered with template (Alice + Bob):")
    print(rendered)
    print("\n" + "=" * 80 + "\n")

    return rendered


def test_character_substitution():
    """Test character substitution in various text scenarios"""
    print("=== Testing Character Substitution ===")

    test_cases = [
        {
            "text": "Hello {{user}}, I am {{char}}. Nice to meet you!",
            "agent_name": "Emma",
            "user_name": "John",
            "expected_contains": ["Emma", "John"],
        },
        {
            "text": "{{char}}'s personality is friendly and {{user}} seems nice.",
            "agent_name": "Sophie",
            "user_name": "Mike",
            "expected_contains": ["Sophie's", "Mike"],
        },
        {
            "text": "In this scenario, {{char}} and {{user}} are having a conversation.",
            "agent_name": "Maria",
            "user_name": "David",
            "expected_contains": ["Maria", "David"],
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"Test case {i}:")
        print(f"Input: {test_case['text']}")

        result = prompt_template_manager._perform_character_substitution(
            test_case["text"], test_case["agent_name"], test_case["user_name"]
        )

        print(f"Output: {result}")

        # Check if expected content is present
        all_found = all(
            expected in result for expected in test_case["expected_contains"]
        )
        print(f"✓ Contains expected content: {all_found}")

        if not all_found:
            missing = [
                expected
                for expected in test_case["expected_contains"]
                if expected not in result
            ]
            print(f"❌ Missing: {missing}")

        print("-" * 50)

    return True


def test_template_validation():
    """Test template validation functionality"""
    print("=== Testing Template Validation ===")

    test_templates = [
        {"template": "Hello {{user}}, I am {{char}}", "should_be_valid": True},
        {"template": "Hello {{ user }}, I am {{ char }}", "should_be_valid": True},
        {
            "template": "Hello {{user, I am {{char}}",  # Invalid - missing closing brace
            "should_be_valid": False,
        },
    ]

    for i, test in enumerate(test_templates, 1):
        print(f"Validation test {i}:")
        print(f"Template: {test['template']}")

        result = prompt_template_manager.validate_template_string(test["template"])

        print(f"Valid: {result['valid']}")
        print(f"Variables: {result['variables']}")
        print(f"Message: {result['message']}")

        if result["valid"] == test["should_be_valid"]:
            print("✓ Validation result matches expectation")
        else:
            print("❌ Validation result doesn't match expectation")

        print("-" * 50)

    return True


def test_available_templates():
    """Test listing available templates"""
    print("=== Testing Available Templates ===")

    templates = prompt_template_manager.list_templates()
    print(f"Available templates: {templates}")

    for template_name in templates:
        template_info = prompt_template_manager.get_template_info(template_name)
        print(f"\nTemplate: {template_name}")
        print(f"Variables: {template_info['variables']}")
        print(f"Config: {template_info['config']}")

    return True


def main():
    """Run all tests"""
    print("Testing Prompt Template System with Character Substitution")
    print("=" * 80)

    try:
        # Run tests
        test_basic_template_rendering()
        test_character_substitution()
        test_template_validation()
        test_available_templates()

        print("\n" + "=" * 80)
        print("✅ All tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
