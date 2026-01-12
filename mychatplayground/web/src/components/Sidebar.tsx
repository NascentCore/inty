"use client";

import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "💬 对话模式测试", description: "角色扮演/聊天提示词验证" },
  { href: "/image-prompt", label: "✨ 角色背景图测试", description: "AI 生图提示词生成" },
  { href: "/conversation-analysis", label: "📊 用户聊天消息分析", description: "上传对话文件进行分析" },
  { href: "/message-to-image", label: "🎭 消息生图测试", description: "聊天消息转生图测试" },
  { href: "/nano-banana", label: "🍌 Nano Banana", description: "一步到位消息生图" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="relative z-[9999] flex h-dvh w-48 flex-shrink-0 flex-col border-r border-zinc-200 bg-zinc-50">
      {/* Logo */}
      <div className="border-b border-zinc-200 px-4 py-4">
        <div className="text-sm font-bold text-zinc-900">Mychatplayground</div>
        <div className="mt-1 text-[10px] text-zinc-500">OpenRouter Playground</div>
      </div>

      {/* 导航链接 */}
      <nav className="flex-1 p-3">
        <div className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            return (
              <a
                key={item.href}
                href={item.href}
                className={`block rounded-lg px-3 py-2.5 text-sm transition-colors ${
                  isActive
                    ? "bg-zinc-900 text-white"
                    : "text-zinc-600 hover:bg-zinc-200 hover:text-zinc-900"
                }`}
                title={item.description}
              >
                {item.label}
              </a>
            );
          })}
        </div>
      </nav>

      {/* 底部信息 */}
      <div className="border-t border-zinc-200 px-4 py-3">
        <div className="text-[10px] text-zinc-400">v1.0</div>
      </div>
    </aside>
  );
}

