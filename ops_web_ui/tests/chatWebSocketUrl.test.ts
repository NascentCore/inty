import {
  afterAll,
  afterEach,
  beforeAll,
  describe,
  expect,
  it,
  vi,
} from "vitest";

let getChatWebSocketUrl: typeof import("../services/api").getChatWebSocketUrl;
let setAssumeUserId: typeof import("../services/api").setAssumeUserId;
let setGlobalApiKey: typeof import("../services/api").setGlobalApiKey;

beforeAll(async () => {
  vi.stubGlobal("window", { location: { origin: "http://stub.invalid" } });
  const mod = await import("../services/api");
  getChatWebSocketUrl = mod.getChatWebSocketUrl;
  setAssumeUserId = mod.setAssumeUserId;
  setGlobalApiKey = mod.setGlobalApiKey;
});

afterAll(() => {
  vi.unstubAllGlobals();
});

describe("getChatWebSocketUrl", () => {
  afterEach(() => {
    setGlobalApiKey(null);
    setAssumeUserId(null);
  });

  it("builds production chat ws URL with token only", () => {
    setGlobalApiKey("tok%20en");
    expect(getChatWebSocketUrl("http://localhost:3000")).toBe(
      "ws://localhost:3000/api/v1/chat/ws?token=tok%2520en",
    );
  });

  it("appends assume_user_id when set (superuser eval flow)", () => {
    setGlobalApiKey("abc");
    setAssumeUserId(" user-xyz ");
    expect(getChatWebSocketUrl("https://example.com")).toBe(
      "wss://example.com/api/v1/chat/ws?token=abc&assume_user_id=user-xyz",
    );
  });
});
