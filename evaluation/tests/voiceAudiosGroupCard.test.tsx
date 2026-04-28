import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { VoiceAudiosGroupCard } from "../pages/UserAnalyticsReportsPage";

describe("VoiceAudiosGroupCard", () => {
  it("renders a permanent link for each recording file", () => {
    const audioUrl = "https://storage.googleapis.com/inty-static/live_chat/u1/a1.wav";

    const html = renderToStaticMarkup(
      <VoiceAudiosGroupCard
        title="当天语音通话录音（按用户-角色）"
        previewLimit={20}
        groups={[
          {
            user_id: "u1",
            agent_id: "a1",
            agent_name: "Esmeralda",
            audios: [
              {
                audio_url: audioUrl,
                message_id: 1,
                created_at: "2026-04-28T00:00:00Z",
                duration_seconds: 51,
              },
            ],
          },
        ]}
      />,
    );

    expect(html).toContain("Permanent link");
    expect(html).toContain('title="Permanent recording file link"');
    expect(html).toContain(`href="${audioUrl}"`);
  });
});
