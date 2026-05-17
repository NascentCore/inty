# CREATED_BY_AGENT
import unittest

from models import CharacterGenerationRequest
from multistage_generator import MultiStageCharacterGenerator


class DummyGeminiClient:
    """Minimal stub that feeds deterministic JSON back into the generator."""

    def __init__(self):
        self.responses = [
            {
                "name": "Nova Kade",
                "alias": "Nova",
                "archetype": "Neon bard",
                "short_bio": "A synthwave poet who hacks by night.",
                "vibe": "edgy",
                "session_goal": "Co-write dramatic gigs with the user.",
                "key_traits": ["witty", "expressive", "loyal"],
            },
            {
                "elevator_pitch": "I'm Nova, your neon-lit partner in whispered revolutions.",
                "detailed_introduction": "First-person intro",
                "relationship_hooks": ["You tune my circuits back to hope."],
                "boundaries": ["We stay collaborative."],
                "conversation_openers": ["Care to share the mic?"],
            },
            {
                "roleplay_prompts": [
                    {
                        "title": "Alley Encore",
                        "prompt": "Keep tone smoldering.",
                        "npc_goal": "Inspire a duet.",
                        "player_hook": "Ask the user to harmonize.",
                        "sample_dialogue": '"Nova: Take the high notes; I will haunt the lows."',
                        "tags": ["music", "noir"],
                    }
                ],
            },
            {
                "image_prompts": [
                    {
                        "title": "Stage Light",
                        "prompt": "Nova under neon rain.",
                        "style": "cyberpunk",
                        "camera": "Wide shot",
                        "lighting": "Vaporwave glow",
                        "color_palette": "magenta & teal",
                    }
                ],
                "audio_profile": {
                    "archetype": "Velvet rebel",
                    "accent": "Transatlantic lilt",
                    "energy": "medium",
                    "pace": "languid",
                    "timbre": "smoky alto",
                    "sample_lines": ["Dial in; the night just started."],
                },
            },
        ]

    def generate_structured_json(self, prompt):
        return self.responses.pop(0)


class MultiStageGeneratorTests(unittest.TestCase):
    def test_multistage_pipeline_returns_full_payload(self):
        request = CharacterGenerationRequest(
            brief_description="A synth bard",
            genre="sci-fi",
            tone="edgy",
            image_style="cyberpunk",
            num_images=3,
        )

        generator = MultiStageCharacterGenerator(
            gemini_client=DummyGeminiClient()
        )
        result = generator.generate(request)

        self.assertTrue(result.success)
        self.assertEqual(len(result.stages), 4)
        self.assertEqual(result.payload.identity.name, "Nova Kade")
        self.assertEqual(len(result.payload.roleplay_prompts), 1)
        self.assertEqual(result.payload.audio_profile.archetype, "Velvet rebel")


if __name__ == "__main__":
    unittest.main()
