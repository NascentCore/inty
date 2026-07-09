from __future__ import annotations

from app.core.companion_harness.companion.bootstrap_memdoc_policy import (
    BootstrapMemDocPolicy,
    bootstrap_track_tool_names,
    bootstrap_writable_rel_paths,
    compose_bootstrap_procedure_overlay,
    compose_bootstrap_tool_call_section,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    BOOTSTRAP_TRACK_TOOL_NAMES,
    CompanionToolName,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
)
from app.core.companion_harness.tools.companion_tool_runtime import (
    build_openai_bootstrap_track_tools,
)


def test_bootstrap_writable_rel_paths_awake_write() -> None:
    assert (
        bootstrap_writable_rel_paths(BootstrapMemDocPolicy.AWAKE_WRITE)
        == MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP
    )


def test_bootstrap_writable_rel_paths_dreaming_policies_empty() -> None:
    assert (
        bootstrap_writable_rel_paths(BootstrapMemDocPolicy.DREAMING_ONLY)
        == frozenset()
    )
    assert (
        bootstrap_writable_rel_paths(BootstrapMemDocPolicy.DREAMING_INCEPTION)
        == frozenset()
    )


def test_bootstrap_track_tool_names_omit_write_for_dreaming() -> None:
    names = bootstrap_track_tool_names(BootstrapMemDocPolicy.DREAMING_ONLY)
    assert CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT not in names
    assert (
        CompanionToolName.COMPANION_BOOTSTRAP_USER_INTERACTIVE_COMPLETE in names
    )


def test_compose_bootstrap_tool_call_section_dreaming_has_no_write_instruction() -> (
    None
):
    section = compose_bootstrap_tool_call_section(
        BootstrapMemDocPolicy.DREAMING_ONLY
    )
    assert "to update **" not in section
    assert "写 IDENTITY" not in section
    assert "DreamingBatch" in section


def test_compose_bootstrap_procedure_overlay_only_for_dreaming() -> None:
    assert (
        compose_bootstrap_procedure_overlay(BootstrapMemDocPolicy.AWAKE_WRITE)
        == ""
    )
    overlay = compose_bootstrap_procedure_overlay(
        BootstrapMemDocPolicy.DREAMING_INCEPTION
    )
    assert "**not** written during bootstrap" in overlay


def test_build_openai_bootstrap_track_tools_default_includes_write() -> None:
    names = {
        t["function"]["name"] for t in build_openai_bootstrap_track_tools()
    }
    expected = {n.value for n in BOOTSTRAP_TRACK_TOOL_NAMES}
    assert names == expected
