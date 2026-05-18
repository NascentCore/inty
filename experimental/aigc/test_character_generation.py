#!/usr/bin/env python3
"""
Test script for the AI Character Generator
"""

import unittest
from models import CharacterImage
from unittest.mock import MagicMock
from gemini_client import GeminiClient
from models import CharacterProfile, CharacterBackground, CharacterEncounter


def make_dummy_character():
    return CharacterProfile(
        name="Test Character",
        age=30,
        gender="non-binary",
        physical_appearance={
            "height": "6'0\"",
            "build": "athletic",
            "hair_color": "black",
            "eye_color": "green",
            "distinguishing_features": ["tattoo on right arm"],
            "clothing_style": "adventurer",
            "accessories": ["amulet"],
        },
        personality_summary="A brave and curious explorer.",
        background=CharacterBackground(
            origin="Unknown lands",
            occupation="Explorer",
            personality_traits=["brave", "curious", "resourceful"],
            motivations=["discovery", "adventure"],
            fears=["failure"],
            dreams=["finding lost cities"],
            relationships={
                "family": "unknown",
                "friends": "many met on travels",
            },
            skills=["navigation", "climbing", "negotiation"],
            quirks=["talks to self"],
            backstory="Born in mystery, always seeking the next horizon.",
        ),
        encounter=CharacterEncounter(
            scene_description="You meet them at a bustling market.",
            location="Bazaar",
            mood="excited",
            initial_dialogue="Care to join me on an adventure?",
            user_role="potential companion",
            encounter_type="adventure",
        ),
        images=[
            CharacterImage(
                url="https://example.com/image.png",
                description="A portrait of the character",
                scene_context="In front of a large, ornate building, holding a large sword",
                image_style="realistic",
            ),
            CharacterImage(
                url="https://example.com/image.png",
                description="A portrait of the character",
                scene_context="In front of a dark and menacing forest, holding a large sword in combat stance",
                image_style="realistic",
            ),
            CharacterImage(
                url="https://example.com/image.png",
                description="A portrait of the character",
                scene_context="Laying on a warm bed, with bandages on their arm, smiling, surrounded by fellow adventure companions",
                image_style="realistic",
            ),
        ],
    )


def test_generate_char_images_happy_path():
    dummy_character = make_dummy_character()
    dummy_image_bytes = b"fakeimagedata"
    dummy_response = MagicMock()
    dummy_image_obj = MagicMock()
    dummy_image_obj.image.image_bytes = dummy_image_bytes
    dummy_image_obj.image.mime_type = "image/png"
    dummy_response.generated_images = [dummy_image_obj]

    client = GeminiClient()
    images = client.generate_character_images(
        dummy_character, num_images_per_scene=1
    )

    for image in images:
        image.show()
        image.save(f"generated_image_{images.index(image)}.png")


if __name__ == "__main__":
    unittest.main()
