from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.core.companion_harness.companion.bootstrap import (
    CompanionSetExperienceProfileToolInput,
    interactive_bootstrap_active,
    load_bootstrap_spec_text,
    load_bootstrap_telegram_profile_slice_text,
    tool_companion_bootstrap_user_interactive_complete,
    tool_companion_set_experience_profile,
)
from app.core.companion_harness.experience_profile.experience_directives import (
    ExperienceDirectiveTone,
    ExperienceSessionIntent,
)
from app.core.companion_harness.companion.models import (
    ContextMeta,
    load_prompt_bundle,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    BOOTSTRAP_MD_REL,
    BOOTSTRAP_TELEGRAM_PROFILE_MD_REL,
    CONTEXT_JSON_REL,
    IDENTITY_MD_REL,
    MEMORY_MD_REL,
    SOUL_MD_REL,
    STYLE_MD_REL,
    USER_MD_REL,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
    load_template_seed_text,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    BOOTSTRAP_WRITABLE_REL_PATHS,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
    REPL_DESCRIPTION_OVERRIDES_BOOTSTRAP,
    CompanionToolName,
)
from app.core.companion_harness.tools.companion_tool_runtime import (
    execute_tool_call,
    tool_memory_store_write_document,
)
from app.core.companion_harness.companion.scope import CompanionScope


def _store(root: Path):
    return MemoryStore(
        scope=CompanionScope("bootstrap", "agent", str(root.resolve())),
        repository=None,
    )


def test_bootstrap_spec_loaders_use_canonical_prompt_seed_paths() -> None:
    assert load_bootstrap_spec_text() == load_template_seed_text(
        BOOTSTRAP_MD_REL
    ).rstrip()
    assert load_bootstrap_telegram_profile_slice_text() == load_template_seed_text(
        BOOTSTRAP_TELEGRAM_PROFILE_MD_REL
    ).rstrip()


def test_bootstrap_writable_rel_paths_match_scope_path_accessors() -> None:
    p = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    accessor_rels = frozenset(
        {
            p.companionship_md,
            p.identity,
            p.style_md,
            p.user_md,
        }
    )
    assert accessor_rels == frozenset(BOOTSTRAP_WRITABLE_REL_PATHS)


def test_interactive_bootstrap_active_requires_incomplete_meta() -> None:
    assert not interactive_bootstrap_active(
        meta=ContextMeta(workspace_bootstrap_user_interactive_completed=True),
    )
    assert interactive_bootstrap_active(
        meta=ContextMeta(workspace_bootstrap_user_interactive_completed=False),
    )


def test_tool_companion_set_experience_profile_updates_context(
    tmp_path: Path,
) -> None:
    root = tmp_path
    st = _store(root)
    st.write_document(
        CONTEXT_JSON_REL,
        json.dumps(
            {"context_mode": "intimate", "user_id": "u"}, ensure_ascii=False
        )
        + "\n",
    )
    ok = tool_companion_set_experience_profile(
        st,
        CompanionSetExperienceProfileToolInput(
            experience_intent=ExperienceSessionIntent.ROLEPLAY,
            note="user asked",
        ),
    )
    assert ok.startswith("OK ")
    context_rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.context_json
    assert st.read_document_if_exists(context_rel) is not None
    data = json.loads(st.read_document(context_rel))
    assert data["context_mode"] == "roleplay"
    assert data["experience_directives"]["intent"] == "roleplay"
    assert data["experience_change_note"] == "user asked"


def test_tool_companion_set_experience_profile_repairs_drifted_context(
    tmp_path: Path,
) -> None:
    st = _store(tmp_path)
    st.write_document(
        CONTEXT_JSON_REL,
        json.dumps(
            {
                "context_mode": "roleplay",
                "experience_directives": {
                    "intent": "casual_chat",
                    "tone": "warm",
                },
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    ok = tool_companion_set_experience_profile(
        st,
        CompanionSetExperienceProfileToolInput(
            experience_intent=ExperienceSessionIntent.EMOTIONAL_SUPPORT,
            note="repair drift",
        ),
    )
    assert ok.startswith("OK ")
    data = json.loads(st.read_document(CONTEXT_JSON_REL))
    assert data["context_mode"] == "emotional_companion"
    assert data["experience_directives"]["intent"] == "emotional_support"
    assert data["experience_directives"]["tone"] == "warm"


def test_execute_tool_call_dispatch_set_experience_profile_missing_note(
    tmp_path: Path,
) -> None:
    root = tmp_path
    st = _store(root)
    st.write_document(
        CONTEXT_JSON_REL,
        json.dumps({"context_mode": "public"}, ensure_ascii=False) + "\n",
    )
    r = asyncio.run(
        execute_tool_call(
            st,
            "companion_set_experience_profile",
            json.dumps({"experience_intent": "emotional_support"}),
        )
    )
    assert r.startswith("ERROR:")
    assert "note" in r
    assert (
        json.loads(st.read_document(CONTEXT_JSON_REL))["context_mode"]
        == "public"
    )


def test_execute_tool_call_dispatch_set_experience_profile(
    tmp_path: Path,
) -> None:
    root = tmp_path
    st = _store(root)
    st.write_document(
        CONTEXT_JSON_REL,
        json.dumps({"context_mode": "public"}, ensure_ascii=False) + "\n",
    )
    r = asyncio.run(
        execute_tool_call(
            st,
            "companion_set_experience_profile",
            json.dumps(
                {
                    "experience_intent": "emotional_support",
                    "note": "user asked for emotional companion",
                }
            ),
        )
    )
    assert r.startswith("OK ")
    assert (
        json.loads(st.read_document(CONTEXT_JSON_REL))["context_mode"]
        == "emotional_companion"
    )
    data = json.loads(st.read_document(CONTEXT_JSON_REL))
    assert data["experience_directives"]["intent"] == "emotional_support"


def test_tool_companion_set_experience_profile_sets_tone(
    tmp_path: Path,
) -> None:
    st = _store(tmp_path)
    st.write_document(
        CONTEXT_JSON_REL,
        json.dumps({"context_mode": "intimate"}, ensure_ascii=False) + "\n",
    )
    ok = tool_companion_set_experience_profile(
        st,
        CompanionSetExperienceProfileToolInput(
            experience_intent=ExperienceSessionIntent.CASUAL_CHAT,
            note="user wants playful",
            tone=ExperienceDirectiveTone.PLAYFUL,
        ),
    )
    assert "tone='playful'" in ok
    data = json.loads(st.read_document(CONTEXT_JSON_REL))
    assert data["experience_directives"]["tone"] == "playful"
    assert data["experience_directives"]["intent"] == "casual_chat"
    assert data["context_mode"] == "emotional_companion"


def test_execute_tool_call_dispatch_set_experience_profile_tone(
    tmp_path: Path,
) -> None:
    st = _store(tmp_path)
    st.write_document(
        CONTEXT_JSON_REL,
        json.dumps({"context_mode": "intimate"}, ensure_ascii=False) + "\n",
    )
    r = asyncio.run(
        execute_tool_call(
            st,
            "companion_set_experience_profile",
            json.dumps(
                {
                    "experience_intent": "remote_romance",
                    "note": "playful remote",
                    "tone": "playful",
                }
            ),
        )
    )
    assert r.startswith("OK ")
    data = json.loads(st.read_document(CONTEXT_JSON_REL))
    assert data["context_mode"] == "remote_lover"
    assert data["experience_directives"]["intent"] == "remote_romance"
    assert data["experience_directives"]["tone"] == "playful"


def test_bootstrap_write_identity_ok(tmp_path: Path) -> None:
    root = tmp_path
    st = _store(root)
    r = asyncio.run(
        execute_tool_call(
            st,
            "memory_store_write_document",
            json.dumps(
                {"relative_path": IDENTITY_MD_REL, "content": "# id\n"},
                ensure_ascii=False,
            ),
            write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
        )
    )
    assert r.startswith("OK ")
    assert st.read_document(IDENTITY_MD_REL) == "# id\n"


def test_bootstrap_write_soul_rejected(tmp_path: Path) -> None:
    root = tmp_path
    st = _store(root)
    r = asyncio.run(
        execute_tool_call(
            st,
            "memory_store_write_document",
            json.dumps(
                {"relative_path": SOUL_MD_REL, "content": "new soul"},
                ensure_ascii=False,
            ),
            write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
        )
    )
    assert r.startswith("ERROR: memory_store_write_document only allows:")
    assert SOUL_MD_REL in r
    assert st.read_document_if_exists(SOUL_MD_REL) is None


def test_bootstrap_end_state_seeds(tmp_path: Path) -> None:
    root = tmp_path
    st = _store(root)
    soul_seed = load_template_seed_text(SOUL_MD_REL)
    memory_seed = load_template_seed_text(MEMORY_MD_REL)
    load_prompt_bundle(st)
    assert st.read_document(SOUL_MD_REL) == soul_seed
    assert st.read_document(MEMORY_MD_REL) == memory_seed
    asyncio.run(
        execute_tool_call(
            st,
            "memory_store_write_document",
            json.dumps(
                {
                    "relative_path": IDENTITY_MD_REL,
                    "content": "# custom identity\n",
                },
                ensure_ascii=False,
            ),
            write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
        )
    )
    asyncio.run(
        execute_tool_call(
            st,
            "memory_store_write_document",
            json.dumps(
                {"relative_path": STYLE_MD_REL, "content": "# style\n"},
                ensure_ascii=False,
            ),
            write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
        )
    )
    asyncio.run(
        execute_tool_call(
            st,
            "memory_store_write_document",
            json.dumps(
                {"relative_path": USER_MD_REL, "content": "# user\n"},
                ensure_ascii=False,
            ),
            write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
        )
    )
    assert st.read_document(SOUL_MD_REL) == soul_seed
    assert st.read_document(MEMORY_MD_REL) == memory_seed
    assert st.read_document(IDENTITY_MD_REL) == "# custom identity\n"


def test_tool_companion_bootstrap_user_interactive_complete_updates_context(
    tmp_path: Path,
) -> None:
    root = tmp_path
    st = _store(root)
    ctx = {
        "context_mode": "unspecific",
        "user_id": "u1",
        "companion_id": "a1",
        "chat_id": "c1",
        "workspace_bootstrap_user_interactive_completed": False,
    }
    st.write_document(
        CONTEXT_JSON_REL, json.dumps(ctx, ensure_ascii=False) + "\n"
    )
    out = tool_companion_bootstrap_user_interactive_complete(st, "done")
    assert out.startswith("OK ")
    data = json.loads(st.read_document(CONTEXT_JSON_REL))
    assert data["workspace_bootstrap_user_interactive_completed"] is True
    assert data["workspace_bootstrap_user_interactive_complete_note"] == "done"
    assert data["context_mode"] == "unspecific"


def test_tool_companion_bootstrap_user_interactive_complete_preserves_non_bootstrap_mode(
    tmp_path: Path,
) -> None:
    root = tmp_path
    st = _store(root)
    st.write_document(
        CONTEXT_JSON_REL,
        json.dumps(
            {
                "context_mode": "roleplay",
                "user_id": "u",
                "workspace_bootstrap_user_interactive_completed": False,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    tool_companion_bootstrap_user_interactive_complete(st, None)
    data = json.loads(st.read_document(CONTEXT_JSON_REL))
    assert data["context_mode"] == "roleplay"


def test_execute_tool_call_dispatch_set_experience_profile_rejects_invalid_intent(
    tmp_path: Path,
) -> None:
    st = _store(tmp_path)
    st.write_document(
        CONTEXT_JSON_REL,
        json.dumps({"context_mode": "intimate"}, ensure_ascii=False) + "\n",
    )
    r = asyncio.run(
        execute_tool_call(
            st,
            "companion_set_experience_profile",
            json.dumps(
                {
                    "experience_intent": "custom_profile",
                    "note": "experiment",
                }
            ),
        )
    )
    assert r.startswith("ERROR:")
    assert (
        json.loads(st.read_document(CONTEXT_JSON_REL))["context_mode"]
        == "intimate"
    )


def test_execute_tool_call_dispatch_write_and_complete(tmp_path: Path) -> None:
    root = tmp_path
    st = _store(root)
    st.write_document(
        CONTEXT_JSON_REL,
        json.dumps(
            {
                "context_mode": "intimate",
                "user_id": "u",
                "companion_id": "a",
                "chat_id": "c",
                "workspace_bootstrap_user_interactive_completed": False,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    st.write_document(USER_MD_REL, "old")
    r1 = asyncio.run(
        execute_tool_call(
            st,
            "memory_store_write_document",
            json.dumps(
                {"relative_path": USER_MD_REL, "content": "new user"},
                ensure_ascii=False,
            ),
            write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
        )
    )
    assert r1.startswith("OK ")
    assert st.read_document(USER_MD_REL) == "new user"
    r2 = asyncio.run(
        execute_tool_call(
            st,
            "companion_bootstrap_user_interactive_complete",
            json.dumps({}),
        )
    )
    assert r2.startswith("OK ")
    assert (
        json.loads(st.read_document(CONTEXT_JSON_REL))[
            "workspace_bootstrap_user_interactive_completed"
        ]
        is True
    )


def test_memory_store_write_soul_allowed_after_interactive_bootstrap_complete(
    tmp_path: Path,
) -> None:
    root = tmp_path
    st = _store(root)
    st.write_document(SOUL_MD_REL, "seed")
    st.write_document(
        CONTEXT_JSON_REL,
        json.dumps(
            {
                "workspace_bootstrap_user_interactive_completed": True,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    ok = tool_memory_store_write_document(st, SOUL_MD_REL, "updated via store")
    assert ok.startswith("OK ")
    assert st.read_document(SOUL_MD_REL) == "updated via store"


def test_bootstrap_tool_schema_write_description_names_bootstrap_paths_only() -> (
    None
):
    bootstrap_csv = ", ".join(BOOTSTRAP_WRITABLE_REL_PATHS)
    write_desc = REPL_DESCRIPTION_OVERRIDES_BOOTSTRAP[
        CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT
    ]
    assert f"Only writable paths via this tool: {bootstrap_csv}" in write_desc
    assert SOUL_MD_REL in write_desc
    from app.core.companion_harness.tools.companion_tool_runtime import (
        build_openai_bootstrap_track_tools,
    )

    write_tool = next(
        t
        for t in build_openai_bootstrap_track_tools()
        if t["function"]["name"] == "memory_store_write_document"
    )
    assert (
        f"Only writable paths via this tool: {bootstrap_csv}"
        in write_tool["function"]["description"]
    )


def test_bootstrap_track_openai_tools_match_manifest() -> None:
    from app.core.companion_harness.tools.companion_tool_definitions import (
        BOOTSTRAP_TRACK_TOOL_NAMES,
    )
    from app.core.companion_harness.tools.companion_tool_runtime import (
        build_openai_bootstrap_track_tools,
    )

    names = {
        t["function"]["name"] for t in build_openai_bootstrap_track_tools()
    }
    expected = {n.value for n in BOOTSTRAP_TRACK_TOOL_NAMES}
    assert names == expected
