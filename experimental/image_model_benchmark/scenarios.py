# CREATED_BY_AGENT
"""
测试场景定义
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ScenarioType(StrEnum):
    EDIT_APPEARANCE = "edit_appearance"
    TWO_PERSONS_DANCE = "two_persons_dance"


@dataclass
class ScenarioVariant:
    """场景变体配置"""

    name: str
    description: str
    prompt_params: dict[str, str]


@dataclass
class Scenario:
    """测试场景"""

    type: ScenarioType
    name: str
    description: str
    prompt_template: str
    required_images: list[str]
    variants: list[ScenarioVariant]

    def get_prompt(self, variant: ScenarioVariant) -> str:
        """根据变体生成完整提示词"""
        return self.prompt_template.format(**variant.prompt_params)

    def get_image_paths(self, base_dir: Path) -> list[Path]:
        """获取所需图片的完整路径"""
        return [base_dir / img for img in self.required_images]


# 场景1：修改发色/衣服
EDIT_APPEARANCE_SCENARIO = Scenario(
    type=ScenarioType.EDIT_APPEARANCE,
    name="修改外观",
    description="修改图片中人物的发色和衣服",
    prompt_template=(
        "Based on the reference image, modify the person's appearance:\n"
        "- Change hair color to: {hair_color}\n"
        "- Change outfit to: {outfit}\n\n"
        "Keep the person's face, pose and background similar to the original. "
        "Generate a high-quality, realistic image."
    ),
    required_images=["character.jpeg"],
    variants=[
        ScenarioVariant(
            name="红发白裙",
            description="红色头发 + 白色连衣裙",
            prompt_params={
                "hair_color": "vibrant red",
                "outfit": "elegant white summer dress",
            },
        ),
        ScenarioVariant(
            name="金发黑西装",
            description="金色头发 + 黑色西装",
            prompt_params={
                "hair_color": "golden blonde",
                "outfit": "professional black business suit",
            },
        ),
        ScenarioVariant(
            name="紫发运动装",
            description="紫色头发 + 运动休闲装",
            prompt_params={
                "hair_color": "deep purple",
                "outfit": "casual athletic wear with hoodie",
            },
        ),
    ],
)


# 场景2：两人跳舞
TWO_PERSONS_DANCE_SCENARIO = Scenario(
    type=ScenarioType.TWO_PERSONS_DANCE,
    name="双人跳舞",
    description="让两张图片中的人物一起跳舞",
    prompt_template=(
        "Create an image where the two people from the reference images are "
        "dancing together in {scene}.\n\n"
        "Requirements:\n"
        "- Maintain each person's original facial features and body type\n"
        "- Show them in an {dance_style} dance pose\n"
        "- The scene should be {atmosphere}\n"
        "- Generate a high-quality, realistic image with proper lighting"
    ),
    required_images=["character.jpeg", "user.jpg"],
    variants=[
        ScenarioVariant(
            name="舞厅华尔兹",
            description="在优雅舞厅中跳华尔兹",
            prompt_params={
                "scene": "an elegant ballroom with crystal chandeliers",
                "dance_style": "classic waltz",
                "atmosphere": "romantic and sophisticated with warm lighting",
            },
        ),
        ScenarioVariant(
            name="户外公园",
            description="在阳光明媚的公园中跳舞",
            prompt_params={
                "scene": "a beautiful sunny park with green trees",
                "dance_style": "casual and playful",
                "atmosphere": "joyful and natural with soft sunlight",
            },
        ),
        ScenarioVariant(
            name="夜店派对",
            description="在霓虹灯下跳现代舞",
            prompt_params={
                "scene": "a modern nightclub with neon lights",
                "dance_style": "energetic modern dance",
                "atmosphere": "vibrant and exciting with colorful lighting",
            },
        ),
    ],
)


# 所有场景
ALL_SCENARIOS: dict[ScenarioType, Scenario] = {
    ScenarioType.EDIT_APPEARANCE: EDIT_APPEARANCE_SCENARIO,
    ScenarioType.TWO_PERSONS_DANCE: TWO_PERSONS_DANCE_SCENARIO,
}


def get_scenario(scenario_type: ScenarioType) -> Scenario:
    """获取指定类型的场景"""
    return ALL_SCENARIOS[scenario_type]


def get_all_scenarios() -> list[Scenario]:
    """获取所有场景"""
    return list(ALL_SCENARIOS.values())


def load_test_images(
    scenario: Scenario,
    test_images_dir: Path,
) -> list[bytes]:
    """
    加载场景所需的测试图片

    Args:
        scenario: 测试场景
        test_images_dir: 测试图片目录

    Returns:
        图片字节数据列表

    Raises:
        FileNotFoundError: 如果图片文件不存在
    """
    images: list[bytes] = []
    for img_name in scenario.required_images:
        img_path = test_images_dir / img_name
        if not img_path.exists():
            raise FileNotFoundError(f"测试图片不存在: {img_path}")
        with open(img_path, "rb") as f:
            images.append(f.read())
    return images
