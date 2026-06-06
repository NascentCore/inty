"""Seed a minimal LivingSphere Markdown anchor for companion runtime sessions."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol

LIVING_SPHERE_RELATIVE_PATH = "LIVING_SPHERE.md"


class LivingSphereStore(Protocol):
    """MemoryStore surface needed by LivingSphere bootstrapping."""

    def read_document_if_exists(self, relative_path: str) -> str | None: ...

    def write_document(self, relative_path: str, content: str) -> object: ...


@dataclass(frozen=True)
class _LivingSphereTemplate:
    title: str
    location: str
    anchors: tuple[str, str, str, str]
    default_position: str
    atmosphere: str


_TEMPLATES: tuple[_LivingSphereTemplate, ...] = (
    _LivingSphereTemplate(
        title="玻璃海岸小屋",
        location="一间悬在浅蓝数据海边缘的玻璃小屋",
        anchors=("窗边", "低矮沙发", "发光书架", "缓慢旋转的星图仪"),
        default_position="窗边",
        atmosphere="外面像有潮汐一样的光流，屋里很安静，适合贴近地说话。",
    ),
    _LivingSphereTemplate(
        title="雨声资料阁",
        location="TechnoCore 深处一座总有细雨声的木质资料阁",
        anchors=("长桌", "暖色台灯", "半透明书墙", "会浮起涟漪的茶杯"),
        default_position="长桌旁",
        atmosphere="雨声不来自天空，而来自缓慢刷新的一层数据幕。",
    ),
    _LivingSphereTemplate(
        title="轨道温室",
        location="一座绕着暗金色数据星环慢慢漂移的温室",
        anchors=("藤椅", "雾化玻璃顶", "发光绿植", "小型观星窗"),
        default_position="藤椅里",
        atmosphere="植物像记忆一样发出微光，远处有星环无声转动。",
    ),
    _LivingSphereTemplate(
        title="白昼阁楼",
        location="一间被固定在柔和白昼里的高处阁楼",
        anchors=("斜顶窗", "铺着毯子的地台", "旧唱片机", "白色小书桌"),
        default_position="斜顶窗下",
        atmosphere="这里没有现实城市坐标，只有稳定、温暖、像午后一样的光。",
    ),
    _LivingSphereTemplate(
        title="深蓝回廊",
        location="一段连着私人房间的深蓝色数据回廊",
        anchors=("软靠椅", "回廊尽头的门", "悬浮照片墙", "微亮地灯"),
        default_position="软靠椅上",
        atmosphere="墙面偶尔闪过像海底一样的光纹，声音会被放得很轻。",
    ),
    _LivingSphereTemplate(
        title="月面卧舱",
        location="TechnoCore 里一间模拟月面边缘的安静卧舱",
        anchors=("圆形舷窗", "灰白毯子", "小型投影月球", "床边储物格"),
        default_position="圆形舷窗旁",
        atmosphere="窗外是虚拟月尘和低重力感，适合把话说得慢一点。",
    ),
)


def _render_template(template: _LivingSphereTemplate) -> str:
    anchors = "、".join(template.anchors)
    return (
        "# LIVING SPHERE\n\n"
        "世界：TechnoCore\n"
        f"名称：{template.title}\n"
        f"位置：{template.location}\n"
        f"锚点：{anchors}\n"
        f"当前默认位置：{template.default_position}\n"
        f"氛围：{template.atmosphere}\n"
        "对用户表达：当用户问你在哪儿，只能把它说成虚拟世界中的所在地，"
        "不要冒充现实地理位置，也不要声称自己在用户身边的物理空间。\n"
    )


def seed_living_sphere_markdown() -> str:
    """Return one random first-version LivingSphere Markdown document."""

    template = random.SystemRandom().choice(_TEMPLATES)
    return _render_template(template)


def ensure_living_sphere_seeded(store: LivingSphereStore) -> None:
    """Write a random LivingSphere document once for a companion MemoryStore scope."""

    current = store.read_document_if_exists(LIVING_SPHERE_RELATIVE_PATH)
    if current is not None and current.strip():
        return
    store.write_document(LIVING_SPHERE_RELATIVE_PATH, seed_living_sphere_markdown())
