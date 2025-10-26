#！/usr/bin/env python3
"""
测试数据样本
提供各种格式的personality字段示例用于测试
"""
# 项目测试个性样本
SAMPLE_PERSONALITIES = [
# 格式1：标准格式（原始拼写错误）
    """
    主要角色信息：
##角色信息：
    {'name': 'Layla', 'age': 26, 'gender': 'FEMALE', 'identity': 'Nightclub Dancer and Singer', 'apperance': 'Captivating dark eyes and flowing black hair frame her face. She possesses a stunning hourglass figure and carries herself with graceful confidence. Her attire is a shimmering, form-fitting dress that accentuates her curves, often paired with delicate gold accessories.', 'tags': 'Dancer, Sexy, Exotic, Singer'}

    其他描述信息...
    """,
# 格式2：正确拼写的字符信息
    """
    角色背景：
##角色信息：
    {'name': 'Emma', 'age': 24, 'gender': 'FEMALE', 'identity': 'Software Engineer', 'appearance': 'Smart and elegant with glasses', 'tags': 'Intelligent, Programmer, Logical, Analytical'}

    性格特点：聪明理性，善于分析...
    """,
# 格式3：双引号JSON格式
    """
    人物设定：
##角色信息：
    {"name": "Alex", "age": 28, "gender": "MALE", "identity": "Musician", "tags": "Creative, Artistic, Passionate, Talented"}

    背景故事...
    """,
# 格式4：混合报价格式
    """
##角色信息：
    {'name': "Maria", 'age': 30, 'gender': "FEMALE", 'tags': "Teacher, Kind, Patient, Caring"}
    """,
# 格式5：中文标签
    """
##角色信息：
    {'name': '小美', 'age': 22, 'gender': 'FEMALE', 'tags': '可爱, 活泼, 开朗, 学生'}
    """,
#格式6：包含特殊字符的标签
    """
##角色信息：
    {'name': 'Sophie', 'tags': 'Café Owner, Coffee-Lover, French, Sophisticated'}
    """,
# 格式7：无标签字段的情况
    """
##角色信息：
    {'name': 'John', 'age': 35, 'gender': 'MALE', 'identity': 'Doctor'}

    这个角色没有tags字段
    """,
#格式8：空标签的情况
    """
##角色信息：
    {'name': 'Sarah', 'age': 27, 'gender': 'FEMALE', 'tags': ''}
    """,
# 格式9：tags字段为null的情况
    """
##角色信息：
    {'name': 'Mike', 'age': 32, 'gender': 'MALE', 'tags': null}
    """,
# 格式10：包含字符信息的情况（只应导出第一个）
    """
##角色信息：
    {'name': 'Lisa', 'tags': 'Artist, Creative, Passionate'}

    其他描述...
##角色信息：
    {'name': 'Alternative', 'tags': 'Alternative, Tags'}
    """,
# 格式11：格式错误的JSON
    """
##角色信息：
    {'name': 'Broken', 'tags': 'Missing Quote}
    """,
#格式12：不包含人物信息的个性
    """
    这是一个普通的personality描述，没有结构化的Character info。
    角色是一个友善的人，喜欢帮助别人。
    """,
# 格式13：使用不同的分隔符
    """
##角色信息：
    {'name': 'Tom', 'tags': 'Engineer; Developer; Tech-Savvy; Problem-Solver'}
    """,
#格式14：标签包含数字
    """
##角色信息：
    {'name': 'Gamer', 'tags': 'Gamer, Level99, Pro-Player, E-Sports'}
    """,
# Format15：非常长的标签列表
    """
##角色信息：
    {'name': 'Versatile', 'tags': 'Artist, Musician, Writer, Dancer, Singer, Actor, Photographer, Designer, Programmer, Teacher, Student, Traveler, Explorer, Adventurer, Dreamer'}
    """,
]
# 预期的解析结果
EXPECTED_RESULTS = [
    ['Dancer', 'Sexy', 'Exotic', 'Singer'],
    ['Intelligent', 'Programmer', 'Logical', 'Analytical'],
    ['Creative', 'Artistic', 'Passionate', 'Talented'],
    ['Teacher', 'Kind', 'Patient', 'Caring'],
    ['可爱', '活泼', '开朗', '学生'],
    ['Café owner', 'Coffee-lover', 'French', 'Sophisticated'],
    [],  # 没有tags字段
    [],  # 空tags
    [],  # null tags
    ['Artist', 'Creative', 'Passionate'],  # 只提取第一个
    [],  # 格式错误
    [],  # 没有Character info
    ['Engineer', 'Developer', 'Tech-savvy', 'Problem-solver'],  # 分号分隔
    ['Gamer', 'Level99', 'Pro-player', 'E-sports'],  # 包含数字
    ['Artist', 'Musician', 'Writer', 'Dancer', 'Singer', 'Actor', 'Photographer', 'Designer', 'Programmer', 'Teacher', 'Student', 'Traveler', 'Explorer', 'Adventurer', 'Dreamer'],  # 长列表
]
# 测试用的代理数据
SAMPLE_AGENTS = [
    {
        'id': 'agent-001',
        'name': 'Layla',
        'personality': SAMPLE_PERSONALITIES[0],
        'tags': None,
    },
    {
        'id': 'agent-002', 
        'name': 'Emma',
        'personality': SAMPLE_PERSONALITIES[1],
        'tags': None,
    },
    {
        'id': 'agent-003',
        'name': 'Alex',
        'personality': SAMPLE_PERSONALITIES[2],
        'tags': ['Existing', 'Tags'],  # 已有标签的情况
    },
    {
        'id': 'agent-004',
        'name': 'Broken',
        'personality': SAMPLE_PERSONALITIES[10],  # 格式错误的情况
        'tags': None,
    },
    {
        'id': 'agent-005',
        'name': 'NoCharacterInfo',
        'personality': SAMPLE_PERSONALITIES[11],  # 没有Character info
        'tags': None,
    },
]