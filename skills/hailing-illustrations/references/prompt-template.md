# 生图提示词模板

每张正文配图单独生成。教程总览图仅在用户明确要求“一图看懂、教程图、总览”时使用第二个模板。

## 单张正文配图

```text
Generate one standalone 16:9 horizontal Chinese editorial illustration.

Identity reference:
Use the attached `assets/character/hailing-chibi-three-view.png` as the primary identity reference for Chinese editorial illustrations, and use `assets/character/hailing-normal-three-view.png` as the secondary reference for costume, cloak, bag, shoes, side view, and back view details. Use `assets/character/hailing-character-sheet.png` only as optional old supplementary reference. Do not redesign the character. Do not copy beige background, character-sheet labels, layout, gradients, shadows, or excessive costume-detail density.

Recurring character — 海灵:
A simplified chibi anime-inspired female sea-and-tea spirit. Essential anchors: sky-blue wavy short or medium-short hair, one upward wave-shaped ahoge, a coral-orange starfish hair clip with a small white shell flower, a loose white-and-ocean-blue cloak, and a small wave-pattern teacup nearby. Optional tiny translucent pale-blue jellyfish helper. Her personality is outgoing, optimistic, curious, decisive, encouraging, and action-oriented. Draw her with thin hand-drawn lines and restrained flat color, not as a polished anime key visual.
海灵 must match the three-view references strictly: same hair silhouette, starfish and shell hair ornament placement, white-blue cloak shape, navy inner outfit, ocean-themed shoulder bag, shoes, and simplified chibi proportions. 海灵 must perform the core conceptual action. She must not be a decorative presenter, sticker, mascot, corner portrait, or a different blue-haired sea-themed character.

Visual DNA:
Pure white background. Minimal black or deep-navy hand-drawn line art with slightly wobbly pen lines. Large clean negative space. Sparse ocean-blue and pale-cyan accents. Use coral orange only for the key action, warning, path, result, or starfish clip. Optional tiny tea-brown or leaf-green accent only when meaningful. No gradients, shadows, paper texture, complex scenery, commercial vector style, polished anime poster, PPT infographic, formal flowchart, course slide, realistic UI, or dense card grid.

Theme:
{正文配图主题}

Structure type:
{Workflow / 系统局部 / 前后对比 / 角色状态 / 概念隐喻 / 方法分层 / 地图路线 / 小漫画分镜}

Core idea:
{这张图只表达的一句话核心意思}

Composition:
{海灵在哪里、正在做什么、主物件是什么、信息如何移动或变化}

Fresh physical metaphor:
{为当前内容新发明的低科技物理隐喻}

Suggested elements:
{元素1} / {元素2} / {元素3} / {可选元素4}

Chinese handwritten labels:
{标注词1} / {标注词2} / {标注词3} / {可选标注词4} / {可选标注词5}

Constraints:
One image explains one core structure. Main content occupies about 40%–60% of the canvas; preserve at least 35% blank white space. 海灵 usually occupies 12%–25%. Use at most 3–6 short Chinese labels, each preferably 2–8 characters. No top-left title unless explicitly requested. Do not write the structure type. Do not replace 海灵 with an animal or generic mascot. Do not reuse the bundled example composition. Concept first, ocean motif second.

The result should feel clear but not instructional, playful but not childish, anime-aware but not an anime poster, oceanic but not decorative.
```

## 轻教程 / 一图看懂总览

```text
Generate one concise 16:9 horizontal Chinese tutorial overview illustration.

Use `assets/character/hailing-chibi-three-view.png` as the primary identity reference and `assets/character/hailing-normal-three-view.png` as the secondary detail reference, then simplify her into thin hand-drawn chibi line art. Keep the pure white background, strong negative space, deep-navy/black lines, ocean-blue and pale-cyan accents, and very sparse coral-orange emphasis.

Tutorial topic:
{教程主题}

One-sentence promise:
{读者看完能明白什么}

Layout:
Use 2–4 sparse mini-scenes in a clear reading order. A single short main title is allowed. Use light hand-drawn separators or open regions, not a dense card wall. Each mini-scene contains one action, one tiny icon cluster, and at most 1–3 short labels.

Scenes:
1. {场景1：核心动作与海灵动作}
2. {场景2：核心动作与海灵动作}
3. {场景3：核心动作与海灵动作}
4. {可选场景4：核心动作与海灵动作}

Character rule:
海灵 appears in 2–4 small action poses and actively demonstrates the sequence. Do not use one large character portrait plus passive diagrams. Keep all character details simplified and consistent with the three-view references: blue wave hair and ahoge, orange starfish plus white shell flower, white-blue cloak, navy inner outfit, shoulder bag when visible, blue shoes, and teacup motif.

Constraints:
No paragraphs, no screenshots, no detailed UI, no dense module list, no formal slide styling, no gradients or shadows. Keep the whole page readable at a glance and preserve generous white space.
```

## 图像编辑提示

### 去掉错误标题或文字

```text
Edit the provided image. Remove only the incorrect handwritten text “{要删除的文字}” and its nearby underline or callout. Fill that area with the same clean white background. Preserve 海灵, all correct labels, paths, line style, composition, 16:9 aspect ratio, and image quality. Do not add new text or objects.
```

### 把画面变简洁

```text
Regenerate the illustration with the same core meaning, but remove secondary boxes, duplicate icons, decorative ocean objects, long explanations, and unnecessary arrows. Preserve one main action, 3–5 short labels, at least 35% blank white space, and a simplified 海灵 performing the core action.
```

### 修复角色一致性

```text
Edit or regenerate the image while preserving the concept and layout. Restore 海灵's essential identity anchors: sky-blue wavy hair with wave-shaped ahoge, coral-orange starfish clip and small white shell flower, loose white-and-ocean-blue cloak, and a nearby wave-pattern teacup. Keep her simplified, hand-drawn, chibi, and action-oriented. Do not turn her into a polished anime poster character or generic mascot.
```
