#!/usr/bin/env python3
"""
测试数据样本
提供各种格式的personality字段示例用于测试
"""

# 测试用的personality字段样本
SAMPLE_PERSONALITIES = [
    # 格式1：标准格式（原始拼写错误）
    """
    主要角色信息：

    ##Charactor info:
    {'name': 'Layla', 'age': 26, 'gender': 'FEMALE', 'identity': 'Nightclub Dancer and Singer', 'apperance': 'Captivating dark eyes and flowing black hair frame her face. She possesses a stunning hourglass figure and carries herself with graceful confidence. Her attire is a shimmering, form-fitting dress that accentuates her curves, often paired with delicate gold accessories.', 'tags': 'Dancer, Sexy, Exotic, Singer'}

    其他描述信息...
    """,
    # 格式2：正确拼写的Character info
    """
    角色背景：

    ##Character info:
    {'name': 'Emma', 'age': 24, 'gender': 'FEMALE', 'identity': 'Software Engineer', 'appearance': 'Smart and elegant with glasses', 'tags': 'Intelligent, Programmer, Logical, Analytical'}

    性格特点：聪明理性，善于分析...
    """,
    # 格式3：双引号JSON格式
    """
    人物设定：

    ##Character info:
    {"name": "Alex", "age": 28, "gender": "MALE", "identity": "Musician", "tags": "Creative, Artistic, Passionate, Talented"}

    背景故事...
    """,
    # 格式4：混合引号格式
    """
    ##Charactor info:
    {'name': "Maria", 'age': 30, 'gender': "FEMALE", 'tags': "Teacher, Kind, Patient, Caring"}
    """,
    # 格式5：中文标签
    """
    ##角色信息:
    {'name': '小美', 'age': 22, 'gender': 'FEMALE', 'tags': '可爱, 活泼, 开朗, 学生'}
    """,
    # 格式6：包含特殊字符的标签
    """
    ##Character info:
    {'name': 'Sophie', 'tags': 'Café Owner, Coffee-Lover, French, Sophisticated'}
    """,
    # 格式7：没有tags字段的情况
    """
    ##Character info:
    {'name': 'John', 'age': 35, 'gender': 'MALE', 'identity': 'Doctor'}

    这个角色没有tags字段
    """,
    # 格式8：空tags的情况
    """
    ##Character info:
    {'name': 'Sarah', 'age': 27, 'gender': 'FEMALE', 'tags': ''}
    """,
    # 格式9：tags字段为null的情况
    """
    ##Character info:
    {'name': 'Mike', 'age': 32, 'gender': 'MALE', 'tags': null}
    """,
    # 格式10：包含多个Character info的情况（只应提取第一个）
    """
    ##Character info:
    {'name': 'Lisa', 'tags': 'Artist, Creative, Passionate'}

    其他描述...

    ##Character info:
    {'name': 'Alternative', 'tags': 'Alternative, Tags'}
    """,
    # 格式11：格式错误的JSON
    """
    ##Character info:
    {'name': 'Broken', 'tags': 'Missing Quote}
    """,
    # 格式12：不包含Character info的personality
    """
    这是一个普通的personality描述，没有结构化的Character info。
    角色是一个友善的人，喜欢帮助别人。
    """,
    # 格式13：使用不同的分隔符
    """
    ##Character info:
    {'name': 'Tom', 'tags': 'Engineer; Developer; Tech-Savvy; Problem-Solver'}
    """,
    # 格式14：标签包含数字
    """
    ##Character info:
    {'name': 'Gamer', 'tags': 'Gamer, Level99, Pro-Player, E-Sports'}
    """,
    # 格式15：非常长的标签列表
    """
    ##Character info:
    {'name': 'Versatile', 'tags': 'Artist, Musician, Writer, Dancer, Singer, Actor, Photographer, Designer, Programmer, Teacher, Student, Traveler, Explorer, Adventurer, Dreamer'}
    """,
]

# 预期的解析结果
EXPECTED_RESULTS = [
    ["Dancer", "Sexy", "Exotic", "Singer"],
    ["Intelligent", "Programmer", "Logical", "Analytical"],
    ["Creative", "Artistic", "Passionate", "Talented"],
    ["Teacher", "Kind", "Patient", "Caring"],
    ["可爱", "活泼", "开朗", "学生"],
    ["Café owner", "Coffee-lover", "French", "Sophisticated"],
    [],  # 没有tags字段
    [],  # 空tags
    [],  # null tags
    ["Artist", "Creative", "Passionate"],  # 只提取第一个
    [],  # 格式错误
    [],  # 没有Character info
    ["Engineer", "Developer", "Tech-savvy", "Problem-solver"],  # 分号分隔
    ["Gamer", "Level99", "Pro-player", "E-sports"],  # 包含数字
    [
        "Artist",
        "Musician",
        "Writer",
        "Dancer",
        "Singer",
        "Actor",
        "Photographer",
        "Designer",
        "Programmer",
        "Teacher",
        "Student",
        "Traveler",
        "Explorer",
        "Adventurer",
        "Dreamer",
    ],  # 长列表
]

# 测试用的Agent数据
SAMPLE_AGENTS = [
    {
        "id": "agent-001",
        "name": "Layla",
        "personality": SAMPLE_PERSONALITIES[0],
        "tags": None,
    },
    {
        "id": "agent-002",
        "name": "Emma",
        "personality": SAMPLE_PERSONALITIES[1],
        "tags": None,
    },
    {
        "id": "agent-003",
        "name": "Alex",
        "personality": SAMPLE_PERSONALITIES[2],
        "tags": ["Existing", "Tags"],  # 已有标签的情况
    },
    {
        "id": "agent-004",
        "name": "Broken",
        "personality": SAMPLE_PERSONALITIES[10],  # 格式错误的情况
        "tags": None,
    },
    {
        "id": "agent-005",
        "name": "NoCharacterInfo",
        "personality": SAMPLE_PERSONALITIES[11],  # 没有Character info
        "tags": None,
    },
]
