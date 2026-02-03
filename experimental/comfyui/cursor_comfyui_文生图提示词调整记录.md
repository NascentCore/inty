# ComfyUI 首次启动模型加载
_Exported on 2/2/2026 at 17:39:18 PST from Cursor (2.4.23)_

---

**User**

第一次启动 comfyui workflow 会很慢，因为要加载模型，把这个记录在 @projects/RUNPOD_Z_IMAGE.md 开头

---

**Cursor**


在文档开头添加关于首次启动 ComfyUI workflow 较慢的说明：



已在 `projects/RUNPOD_Z_IMAGE.md` 开头（标题下方）加入说明：

- **第一次启动 ComfyUI workflow 会很慢**，因为需要加载模型；
- **后续请求会快很多**。

用的是 blockquote（`> **注意**：...`），在文档顶部一眼就能看到。

---

**User**

What's the purpose of control after generate in the text-to-image model?


---

**Cursor**


**Control after generate** 决定**每次生图结束后**，像 **seed** 这类“随机相关”参数要怎么变，用来在「多试几种」和「可复现」之间做取舍。

- **randomize**（你截图里的）：生完一张后，自动把 seed 换成新的随机数，下一张图会不一样。适合同一 prompt 下多试几种效果。
- **fixed**：生完图后 seed 不变，下次再跑还是同一套随机状态，便于复现或只改别的参数对比。
- **increment**：每次生图后把 seed 按固定步长加一（或类似规则），适合做有规律的、可追溯的变体。

所以它的作用就是：**在每次生图完成后，自动按你选的策略更新 seed（或其它可随机参数）**，不用每次自己改。

---

**User**

如何描述生图中人物的样貌，从而展示出不同的中国人面貌？

---

**Cursor**


在生图 prompt 里想体现「不同的中国人面貌」，可以从这些维度写清楚人物的**具体样貌**，而不是只写「一个中国人」：

## 1. 脸型与轮廓
- **脸型**：圆脸、方脸、鹅蛋脸、长脸、菱形脸、国字脸
- **轮廓**：颧骨明显/柔和、下颌线清晰/圆润、额头宽/窄

例：*oval face with soft jawline* / *round face, high cheekbones*

## 2. 五官
- **眼睛**：单眼皮、双眼皮、丹凤眼、杏眼、眼距宽/窄、眼睛大小
- **鼻子**：鼻梁高/塌、鼻翼宽/窄、鼻头圆/尖
- **嘴唇**：厚唇/薄唇、唇形
- **眉毛**：浓/淡、平眉、挑眉、柳叶眉

例：*single eyelids, almond-shaped eyes* / *double eyelids, defined nose bridge*

## 3. 肤色与肤质
- **肤色**：小麦色、偏白、健康肤色、暖调/冷调
- **肤质**：光滑、有雀斑、有痣、轻微皱纹（可顺带体现年龄）

例：*warm-toned skin, light tan* / *fair skin with natural glow*

## 4. 年龄与气质
- **年龄**：十几岁、二十出头、三十多岁、中年、银发
- **气质**：温和、英气、书卷气、阳光、沉稳

例：*woman in her late twenties, gentle expression* / *man in his thirties, sharp features*

## 5. 发型与细节
- **发型**：短发、长发、齐刘海、中分、卷发、直发、马尾、寸头
- **发色**：黑发、深棕、少量灰白
- **其他**：戴眼镜、有痣、酒窝、小虎牙等

例：*short black hair, side-swept bangs* / *long straight hair, middle part*

## 6. 写 prompt 时的用法建议

- **写具体、不写笼统**：  
  不好：*a Chinese person*  
  较好：*a Chinese woman, oval face, single eyelids, warm skin tone, long black hair, in her mid-twenties*

- **一次别堆太多冲突特征**：选 3～5 个最想突出的（如脸型 + 眼睛 + 年龄 + 发型），更容易稳定出图。

- **用「多样性」类词辅助**（视模型支持情况）：  
  *diverse East Asian features* / *various Chinese facial features* 有时能减少「同一张脸」感。

- **多组 prompt 轮换**：同一场景下换不同脸型、年龄、五官描述，批量生成，更容易得到多张不同中国人面貌。

如果你有固定用的模板（例如 ComfyUI 里某几个节点），可以把「人物样貌」单独做成一小段固定句式，只改脸型、年龄、发型等关键词，方便复现和做多样性测试。

---

**User**

给出一个描述类似辛芷蕾样貌（截图中所示）的样貌描述

---

**Cursor**


下面是一段可直接或稍作改写用于生图的「样貌描述」，以及一组关键词，便于在文生图里复现类似辛芷蕾的样貌。

---

## 样貌描述（可直接用于 prompt）

**中文：**  
女性，鹅蛋脸、略偏心形，下颌线清晰、下巴略尖，颧骨适中，脸颊饱满。杏仁眼、眼角微微上挑、内眼角较尖，双眼皮，眼窝有适度立体感，眼神清澈有神，深棕色瞳孔；眉毛自然、毛流清晰、中等粗细、弧度柔和。鼻梁高挺笔直，鼻头圆润，鼻翼宽度自然。嘴唇饱满、唇峰清晰，唇色豆沙粉或珊瑚色、带一点光泽，嘴角微扬。深棕色中短发，长度约到锁骨，发尾有层次、微微内卷，侧分、蓬松有空气感。肤色白皙、肤质细腻，妆容清透，眼线与睫毛突出眼形，唇妆自然。表情平静、自信，略带成熟与故事感。

**英文（便于模型理解）：**  
East Asian woman, oval to slightly heart-shaped face, defined jawline, soft pointed chin, moderate cheekbones, full but not round cheeks. Almond-shaped eyes, slight upward tilt at outer corners, sharp inner corners, double eyelids, clear and expressive gaze, dark brown eyes; natural eyebrows with visible hair strokes, medium thickness, soft arch. Straight, high nose bridge, rounded nose tip, natural nose width. Full lips, clear cupid’s bow, dusty rose or coral lip color with subtle shine, slight smile. Medium-length dark brown hair to collarbone, layered ends with soft inward curl, side part, voluminous and airy. Fair, smooth skin, natural makeup with defined eyes and soft lip color. Calm, confident expression, elegant and mature.

---

## 关键词（简短版，便于拼接进 prompt）

**中文关键词：**  
鹅蛋脸、杏仁眼、双眼皮、高鼻梁、饱满唇、深棕中短发、蓬松发尾、侧分、白皙皮肤、清透妆、自信、优雅。

**英文关键词：**  
oval face, almond eyes, double eyelids, high nose bridge, full lips, medium dark brown hair, layered wavy ends, side part, fair skin, natural makeup, confident, elegant.

---

**User**

第 1 张为生成的图片，与第 2 张所说的目标，差距有些大；根据差别，继续优化提示词

---

**Cursor**


根据两张图的差异，总结需要**加强或修正**的点，并给出一版优化后的提示词。

---

## 主要差距

| 维度 | 第 1 张（生成） | 第 2 张（目标） | 优化方向 |
|------|------------------|------------------|----------|
| **嘴唇** | 饱满但不够突出 | 最突出特征：唇峰非常明显、略厚、带光泽 | 强调「唇峰明显、饱满、豆沙/裸粉、微光泽」 |
| **发型** | 齐肩内扣短发、偏贴 | 肩下 bob/lob、**蓬松、有波浪、脸周体积感强** | 改为「肩下长度、蓬松、柔和波浪、脸周蓬松」 |
| ** pose** | 正面、无手部 | **头微侧、双手轻握托在下巴下、托腮** | 明确写「头微侧、双手托下巴」 |
| **气质/年龄** | 偏年轻、偏学生气 | 偏成熟、**沉稳、知性** | 写「二十七八至三十出头、沉稳、知性」 |
| **眼妆** | 有眼线/睫毛 | **睫毛更长、上眼线清晰但不浓** | 写「睫毛纤长、上眼线细致」 |
| **眉毛** | 自然、有弧度 | **偏浓、毛流清晰、弧度柔和** | 写「眉毛略浓、毛流清晰、柔和弧度」 |
| **上衣** | 深色/黑 | 浅色/白或米色 | 写「浅色或米色上衣」 |

---

## 优化后的样貌 + 构图提示词

**中文（可直接用或微调）：**  
东亚女性，二十八九至三十出头，鹅蛋脸，下颌线清晰、颧骨柔和。杏仁眼、双眼皮、外眼角略上扬，深棕色瞳孔，眼神直视、自信；睫毛纤长，上眼线细致不浓。眉毛偏浓、毛流清晰、柔和弧度、深棕。鼻梁直、鼻头略圆。**嘴唇饱满、唇峰非常明显、略厚，豆沙粉或裸粉唇色、带柔和光泽**，嘴角放松、微带沉稳感。**深棕色头发，肩下长度 bob/lob，柔和波浪、脸周蓬松有体积感，侧分**。肤色白皙、肤质细腻，妆容干净、偏知性。**头微微向一侧倾斜，双手轻握、托在下巴下方、托腮姿势**，穿浅色或米色上衣。表情平静、自信、略带成熟。纯色浅灰背景，柔光。

**英文（便于模型解析）：**  
East Asian woman, late twenties to early thirties, oval face, defined jawline, soft cheekbones. Almond-shaped eyes, double eyelids, outer corners slightly upturned, dark brown eyes, direct confident gaze; long eyelashes, subtle defined upper eyeliner. Thick natural eyebrows, visible hair strokes, soft arch, dark brown. Straight nose bridge, slightly rounded tip. **Full lips, very prominent cupid's bow, slightly plump, dusty rose or nude-peach lip color with soft sheen**, relaxed mouth, mature composure. **Dark brown hair, shoulder-length bob or lob, soft waves, strong volume around face, side part.** Fair smooth skin, refined natural makeup. **Head slightly tilted to one side, hands clasped gently below chin, framing lower face**, light cream or white top. Calm, confident, refined expression. Plain light grey background, soft even lighting.

---

## 可单独加强的短句（按需插入）

若生成结果仍偏离目标，可在原 prompt 里**额外加**下面几句，强化「目标图」特征：

- **嘴唇：**  
  `prominent cupid's bow, full lips with soft glossy sheen, rosy nude lipstick`  
  或：`唇峰非常明显，饱满唇，豆沙粉微光泽`

- **发型与体积感：**  
  `voluminous hair around face, shoulder-length wavy bob, soft side part`  
  或：`脸周头发蓬松有体积感，肩下波浪 bob，侧分`

- **姿势：**  
  `hands clasped under chin, head slightly tilted, elegant pose`  
  或：`双手托下巴，头微侧，优雅坐姿`

- **气质：**  
  `sophisticated, refined elegance, quiet confidence, mature beauty`  
  或：`知性、沉稳、低调自信、成熟美`

先按「优化后的样貌 + 构图」整段用一版；若某一方面仍不对（例如嘴唇还是不够突出），再单独加上面对应短句加强即可。

