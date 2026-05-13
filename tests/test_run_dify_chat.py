from tools.scripts.run_dify_chat import build_dify_payload, prepare_characters_for_dify


def test_prepare_characters_for_dify_filters_existing_and_duplicates():
    generated_characters = [
        {"name": " Aisha ", "description": "first description"},
        {"name": "aisha", "description": "duplicate in current batch"},
        {"name": "Daniella", "description": "exists in db"},
        {"name": "Kira", "description": "valid candidate"},
        {"name": "Kira", "description": "duplicate in current batch"},
        {"name": "", "description": "missing name"},
        {"name": "Fiona", "description": "   "},
        {"name": "Nia", "description": "another valid candidate"},
    ]
    existing_names = ["daniella", "Elena"]

    prepared = prepare_characters_for_dify(generated_characters, existing_names)

    prepared_name_set = {item["name"] for item in prepared}
    assert prepared_name_set == {"Aisha", "Kira", "Nia"}

    prepared_by_name = {item["name"]: item for item in prepared}
    assert prepared_by_name["Aisha"]["description"] == "first description"
    assert prepared_by_name["Kira"]["description"] == "valid candidate"


def test_build_dify_payload_passes_name_and_description_in_inputs():
    character = {
        "name": "Mei Lin",
        "description": "Hanfu muse for Lunar New Year theme.",
    }

    payload = build_dify_payload(character)

    assert payload["inputs"]["visibility"] == "PRIVATE"
    assert payload["inputs"]["source"] == "AUTO_GENERATED"
    assert payload["inputs"]["name"] == "Mei Lin"
    assert payload["inputs"]["character_name"] == "Mei Lin"
    assert payload["inputs"]["description"] == character["description"]
    assert payload["inputs"]["character_description"] == character["description"]
    assert payload["query"].endswith("name is Mei Lin")
