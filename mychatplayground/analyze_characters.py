#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析用户创建角色时使用的外貌、衣物、场景、发色等高频词汇
"""

import csv
import re
import json
from collections import Counter

# 定义关键词类别
APPEARANCE_KEYWORDS = [
    # 发色 (Hair colors)
    'blonde', 'brunette', 'black hair', 'brown hair', 'red hair', 'ginger', 
    'white hair', 'silver hair', 'grey hair', 'gray hair', 'pink hair', 
    'blue hair', 'purple hair', 'green hair', 'auburn', 'dark hair', 'light hair',
    'golden hair', 'platinum', 'strawberry blonde', 'jet black',
    
    # 发型 (Hairstyles)
    'long hair', 'short hair', 'curly', 'straight hair', 'wavy', 'ponytail',
    'pigtails', 'braid', 'braids', 'bun', 'bangs', 'fringe', 'bob', 'pixie',
    'messy hair', 'spiky', 'mohawk', 'dreadlocks', 'afro',
    
    # 眼睛 (Eyes)
    'blue eyes', 'green eyes', 'brown eyes', 'hazel eyes', 'black eyes',
    'grey eyes', 'gray eyes', 'golden eyes', 'amber eyes', 'red eyes',
    'purple eyes', 'heterochromia', 'bright eyes', 'dark eyes', 'light eyes',
    
    # 身材 (Body type)
    'tall', 'short', 'petite', 'slim', 'slender', 'curvy', 'athletic',
    'muscular', 'chubby', 'thick', 'fit', 'thin', 'skinny', 'voluptuous',
    'busty', 'big boobs', 'big breasts', 'large breasts', 'small breasts',
    'hourglass', 'pear shaped', 'plus size',
    
    # 皮肤 (Skin)
    'fair skin', 'pale', 'tan', 'tanned', 'dark skin', 'olive skin',
    'light skin', 'brown skin', 'ebony', 'porcelain', 'freckles',
    
    # 年龄描述 (Age descriptions)
    'young', 'mature', 'milf', 'teenager', 'teen', 'adult', 'older',
    'middle aged', 'elderly',
    
    # 面部特征 (Facial features)
    'beautiful', 'handsome', 'pretty', 'cute', 'gorgeous', 'stunning',
    'attractive', 'sexy', 'hot', 'ugly', 'plain', 'sharp features',
    'soft features', 'angular', 'dimples', 'beard', 'mustache', 'clean shaven',
    'goatee', 'stubble', 'glasses', 'piercing', 'piercings', 'tattoo', 'tattoos',
]

CLOTHING_KEYWORDS = [
    # 上衣 (Tops)
    'shirt', 't-shirt', 'blouse', 'top', 'sweater', 'hoodie', 'jacket',
    'coat', 'tank top', 'crop top', 'vest', 'cardigan', 'blazer',
    
    # 下装 (Bottoms)
    'pants', 'jeans', 'shorts', 'skirt', 'mini skirt', 'dress', 'leggings',
    'trousers', 'sweatpants', 'joggers',
    
    # 内衣 (Underwear)
    'bra', 'panties', 'lingerie', 'underwear', 'thong', 'bikini', 'swimsuit',
    'bathing suit', 'corset', 'garter',
    
    # 全身服装 (Full outfits)
    'uniform', 'suit', 'tuxedo', 'gown', 'wedding dress', 'costume',
    'armor', 'robe', 'kimono', 'maid outfit', 'nurse outfit', 'school uniform',
    'business attire', 'casual', 'formal', 'elegant', 'revealing',
    
    # 鞋子 (Shoes)
    'heels', 'high heels', 'boots', 'sneakers', 'sandals', 'barefoot',
    'stilettos', 'flats', 'loafers',
    
    # 配饰 (Accessories)
    'necklace', 'earrings', 'bracelet', 'ring', 'choker', 'collar',
    'hat', 'cap', 'headband', 'crown', 'tiara', 'scarf', 'tie', 'bowtie',
    'stockings', 'thigh highs', 'fishnet',
    
    # 颜色 (Colors for clothing)
    'black dress', 'white dress', 'red dress', 'blue dress', 'pink dress',
    'leather', 'lace', 'silk', 'satin', 'velvet', 'denim', 'cotton',
]

SCENE_KEYWORDS = [
    # 室内场景 (Indoor scenes)
    'bedroom', 'bathroom', 'kitchen', 'living room', 'office', 'classroom',
    'library', 'hospital', 'hotel', 'apartment', 'house', 'mansion',
    'castle', 'dungeon', 'basement', 'attic', 'studio', 'gym', 'spa',
    'bar', 'club', 'restaurant', 'cafe', 'coffee shop', 'shop', 'store',
    'mall', 'school', 'college', 'university', 'dorm', 'prison', 'jail',
    
    # 室外场景 (Outdoor scenes)
    'beach', 'pool', 'park', 'garden', 'forest', 'woods', 'mountain',
    'lake', 'river', 'ocean', 'sea', 'island', 'desert', 'street',
    'city', 'town', 'village', 'countryside', 'farm', 'field', 'meadow',
    'rooftop', 'balcony', 'backyard', 'alley', 'parking lot',
    
    # 特殊场景 (Special settings)
    'fantasy', 'medieval', 'sci-fi', 'futuristic', 'apocalyptic', 'zombie',
    'vampire', 'werewolf', 'supernatural', 'magic', 'kingdom', 'empire',
    'spaceship', 'space station', 'planet', 'alien',
    
    # 天气/时间 (Weather/Time)
    'night', 'day', 'morning', 'evening', 'sunset', 'sunrise', 'rain',
    'snow', 'storm', 'sunny', 'cloudy', 'dark', 'moonlight',
    
    # 相遇场景 (Meeting scenarios)
    'first meet', 'meeting', 'encounter', 'date', 'blind date',
    'party', 'wedding', 'funeral', 'reunion', 'interview', 'work',
    'neighbor', 'roommate', 'stranger', 'accident', 'crash', 'rescue',
]

PERSONALITY_KEYWORDS = [
    # 正面性格 (Positive traits)
    'kind', 'sweet', 'gentle', 'caring', 'loving', 'friendly', 'cheerful',
    'happy', 'optimistic', 'confident', 'brave', 'strong', 'smart',
    'intelligent', 'wise', 'funny', 'playful', 'innocent', 'pure',
    'loyal', 'honest', 'sincere', 'romantic', 'passionate', 'protective',
    
    # 负面/复杂性格 (Negative/complex traits)
    'cold', 'distant', 'rude', 'arrogant', 'cruel', 'evil', 'dark',
    'mysterious', 'secretive', 'shy', 'timid', 'nervous', 'anxious',
    'jealous', 'possessive', 'obsessive', 'yandere', 'tsundere',
    'dominant', 'submissive', 'aggressive', 'violent', 'sadistic',
    'masochistic', 'manipulative', 'flirty', 'seductive', 'teasing',
    
    # 角色类型 (Character types)
    'boss', 'teacher', 'student', 'professor', 'doctor', 'nurse',
    'cop', 'police', 'soldier', 'warrior', 'knight', 'prince', 'princess',
    'king', 'queen', 'celebrity', 'idol', 'model', 'actress', 'actor',
    'singer', 'dancer', 'maid', 'butler', 'servant', 'master', 'slave',
    'stepmother', 'stepmom', 'stepfather', 'stepdad', 'stepsister',
    'stepbrother', 'mother', 'mom', 'father', 'dad', 'sister', 'brother',
    'daughter', 'son', 'wife', 'husband', 'girlfriend', 'boyfriend',
    'ex-girlfriend', 'ex-boyfriend', 'crush', 'friend', 'best friend',
    'stranger', 'neighbor', 'coworker', 'colleague', 'billionaire', 'rich',
    'ceo', 'mafia', 'gangster', 'criminal', 'assassin', 'spy', 'thief',
    'vampire', 'werewolf', 'demon', 'angel', 'god', 'goddess', 'alien',
    'robot', 'android', 'elf', 'fairy', 'witch', 'wizard', 'superhero',
    'catgirl', 'bunny girl', 'neko',
]

def extract_text_from_row(row):
    """从CSV行中提取所有文本内容"""
    texts = []
    
    # 提取settings中的description
    if row.get('settings'):
        try:
            settings = json.loads(row['settings'])
            if settings.get('description'):
                texts.append(settings['description'].lower())
        except:
            pass
    
    # 提取其他文本字段
    text_fields = ['intro', 'opening', 'prompt', 'personality', 'scenario']
    for field in text_fields:
        if row.get(field):
            texts.append(row[field].lower())
    
    return ' '.join(texts)

def count_keywords(text, keywords):
    """统计关键词出现次数"""
    counts = Counter()
    text_lower = text.lower()
    
    for keyword in keywords:
        # 使用单词边界匹配
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        matches = len(re.findall(pattern, text_lower))
        if matches > 0:
            counts[keyword] = matches
    
    return counts

def main():
    csv_path = '/Users/wangwangwang/Desktop/用户创建角色_高质量.csv'
    
    # 存储所有文本
    all_text = []
    
    # 各类别计数器
    appearance_counts = Counter()
    clothing_counts = Counter()
    scene_counts = Counter()
    personality_counts = Counter()
    
    # 读取CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = extract_text_from_row(row)
            all_text.append(text)
            
            # 统计各类关键词
            appearance_counts.update(count_keywords(text, APPEARANCE_KEYWORDS))
            clothing_counts.update(count_keywords(text, CLOTHING_KEYWORDS))
            scene_counts.update(count_keywords(text, SCENE_KEYWORDS))
            personality_counts.update(count_keywords(text, PERSONALITY_KEYWORDS))
    
    # 输出结果
    print("=" * 60)
    print("用户创建角色高频词分析")
    print("=" * 60)
    
    print("\n" + "=" * 60)
    print("【外貌特征 / APPEARANCE】Top 30")
    print("=" * 60)
    for word, count in appearance_counts.most_common(30):
        print(f"  {word}: {count}")
    
    print("\n" + "=" * 60)
    print("【衣物服饰 / CLOTHING】Top 30")
    print("=" * 60)
    for word, count in clothing_counts.most_common(30):
        print(f"  {word}: {count}")
    
    print("\n" + "=" * 60)
    print("【场景设定 / SCENE】Top 30")
    print("=" * 60)
    for word, count in scene_counts.most_common(30):
        print(f"  {word}: {count}")
    
    print("\n" + "=" * 60)
    print("【性格/角色类型 / PERSONALITY & ROLES】Top 40")
    print("=" * 60)
    for word, count in personality_counts.most_common(40):
        print(f"  {word}: {count}")
    
    # 额外分析：自由词频统计（过滤常见词后）
    print("\n" + "=" * 60)
    print("【自由词频统计 - 过滤常见词后的高频词】")
    print("=" * 60)
    
    # 常见停用词
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
        'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
        'from', 'up', 'about', 'into', 'over', 'after', 'beneath', 'under',
        'above', 'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either',
        'neither', 'not', 'only', 'own', 'same', 'than', 'too', 'very',
        'just', 'also', 'now', 'here', 'there', 'when', 'where', 'why',
        'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
        'other', 'some', 'such', 'no', 'any', 'only', 'own', 'same',
        'this', 'that', 'these', 'those', 'i', 'me', 'my', 'myself',
        'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours',
        'yourself', 'yourselves', 'he', 'him', 'his', 'himself',
        'she', 'her', 'hers', 'herself', 'it', 'its', 'itself',
        'they', 'them', 'their', 'theirs', 'themselves', 'what',
        'which', 'who', 'whom', 'if', 'then', 'else', 'because',
        'as', 'until', 'while', 'although', 'though', 'once',
        'like', 'want', 'wants', 'wanted', 'get', 'gets', 'got',
        'make', 'makes', 'made', 'go', 'goes', 'went', 'gone',
        'come', 'comes', 'came', 'take', 'takes', 'took', 'taken',
        'see', 'sees', 'saw', 'seen', 'know', 'knows', 'knew', 'known',
        'think', 'thinks', 'thought', 'give', 'gives', 'gave', 'given',
        'find', 'finds', 'found', 'tell', 'tells', 'told', 'ask', 'asks',
        'asked', 'use', 'uses', 'used', 'try', 'tries', 'tried',
        'leave', 'leaves', 'left', 'call', 'calls', 'called',
        'keep', 'keeps', 'kept', 'let', 'lets', 'begin', 'begins', 'began',
        'seem', 'seems', 'seemed', 'help', 'helps', 'helped',
        'show', 'shows', 'showed', 'shown', 'hear', 'hears', 'heard',
        'play', 'plays', 'played', 'run', 'runs', 'ran', 'move', 'moves', 'moved',
        'live', 'lives', 'lived', 'believe', 'believes', 'believed',
        'll', 've', 're', 'd', 's', 't', 'm', 'don', 'won', 'aren', 'isn',
        'wasn', 'weren', 'hasn', 'haven', 'hadn', 'doesn', 'didn', 'couldn',
        'wouldn', 'shouldn', 'mightn', 'mustn', 'im', 'youre', 'hes', 'shes',
        'its', 'were', 'theyre', 'ive', 'youve', 'weve', 'theyve',
        'id', 'youd', 'hed', 'shed', 'wed', 'theyd', 'ill', 'youll',
        'hell', 'shell', 'well', 'theyll', 'isnt', 'arent', 'wasnt',
        'werent', 'hasnt', 'havent', 'hadnt', 'doesnt', 'dont', 'didnt',
        'wont', 'wouldnt', 'cant', 'couldnt', 'shouldnt', 'mightnt', 'mustnt',
        'always', 'never', 'sometimes', 'often', 'usually', 'really',
        'actually', 'probably', 'maybe', 'perhaps', 'definitely',
        'one', 'two', 'first', 'last', 'next', 'new', 'old', 'good', 'bad',
        'great', 'little', 'big', 'small', 'long', 'high', 'low',
        'right', 'wrong', 'early', 'late', 'hard', 'easy', 'able',
        'back', 'even', 'still', 'ever', 'again', 'away', 'off',
        'out', 'down', 'around', 'through', 'between', 'during',
        'before', 'after', 'without', 'within', 'along', 'across',
        'behind', 'beyond', 'near', 'upon', 'toward', 'towards',
        'onto', 'throughout', 'despite', 'concerning', 'regarding',
        'say', 'says', 'said', 'feel', 'feels', 'felt', 'become', 'becomes', 'became',
        'put', 'puts', 'mean', 'means', 'meant', 'set', 'sets', 'turn', 'turns', 'turned',
        'start', 'starts', 'started', 'look', 'looks', 'looked', 'looking',
        'things', 'thing', 'something', 'anything', 'nothing', 'everything',
        'someone', 'anyone', 'everyone', 'nobody', 'everybody', 'anybody',
        'people', 'person', 'man', 'men', 'woman', 'women', 'child', 'children',
        'world', 'life', 'time', 'times', 'year', 'years', 'day', 'days',
        'way', 'ways', 'part', 'parts', 'place', 'places', 'case', 'cases',
        'week', 'weeks', 'company', 'system', 'program', 'question', 'questions',
        'work', 'works', 'working', 'worked', 'government', 'number', 'numbers',
        'night', 'point', 'points', 'home', 'homes', 'water', 'room', 'rooms',
        'mother', 'area', 'areas', 'money', 'story', 'stories', 'fact', 'facts',
        'month', 'months', 'lot', 'lots', 'word', 'words', 'business', 'issue', 'issues',
        'side', 'sides', 'kind', 'kinds', 'head', 'heads', 'far', 'hand', 'hands',
        'course', 'hours', 'body', 'bodies', 'hour', 'door', 'doors',
        'name', 'names', 'line', 'lines', 'city', 'cities', 'family', 'families',
    }
    
    # 合并所有文本
    combined_text = ' '.join(all_text)
    
    # 提取单词
    words = re.findall(r'\b[a-zA-Z]+\b', combined_text.lower())
    
    # 过滤停用词和短词
    filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
    
    # 统计词频
    word_counts = Counter(filtered_words)
    
    print("\nTop 50 高频词（去除常见词后）:")
    for word, count in word_counts.most_common(50):
        print(f"  {word}: {count}")

if __name__ == '__main__':
    main()

