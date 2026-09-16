# 故事流程图设计

> 用途：为 cocAIKeeper 提供可运行的分支剧情模型。把模组/剧本建模为**有向图**：
> 节点 = 场景/剧情段；边 = 转移（玩家选择、检定结果、随机/条件触发）。
>
> 设计约定：
> - **定义与运行分离**：`StoryGraph` 只描述图结构（可增删改、校验、序列化）；
>   `StorySession` 保存一局游戏的游标、历史、flag，负责条件求值与流转。
> - **list 为唯一事实来源**：`nodes` / `edges` 保序存储；
>   `id → Node`、`id → Edge`、`from → Edge[]`、`to → Edge[]` 索引惰性构建，增删改时同步维护。
> - 复用调查员类设计中的 `Difficulty`、`CheckResult`、`AttributeName`。
> - 边的 `condition` 决定该边是否可走；`priority` 决定多条可走边时的排序（大者优先）；
>   `label` 是对玩家展示的选项文案（`CHOICE` 边必填）。
> - 允许环（玩家可反复探索），但自动流转需设置步数上限防止死循环。

```typescript
// ==================== 基础类型 ====================

/** 节点类型 */
enum StoryNodeType {
  START = "start",  // 起始场景
  SCENE = "scene",  // 普通场景
  END   = "end",    // 结局/结束场景
}

/** 边类型 */
enum EdgeKind {
  AUTO = "auto",        // 无需玩家输入，自动转移
  CHOICE = "choice",    // 玩家选项，label 为选项文案
  CONDITION = "condition", // 由条件决定是否触发
}

type FlagValue = boolean | number | string;

/** 节点进入/离开时执行的动作 */
type StoryAction =
  | { kind: "setFlag"; flag: string; value: FlagValue }
  | { kind: "incFlag"; flag: string; delta: number }
  | { kind: "clearFlag"; flag: string }
  | { kind: "custom"; type: string; payload?: unknown };

// ==================== 条件 ====================

interface FlagCondition {
  kind: "flag";
  flag: string;
  op: "exists" | "not-exists" | "==" | "!=" | ">" | "<" | ">=" | "<=";
  value?: FlagValue; // op 为比较运算时必填
}

/** 检定条件：skillId 与 attribute 二选一 */
interface CheckCondition {
  kind: "check";
  skillId?: string;          // 用技能 id 判定
  attribute?: AttributeName; // 用属性名判定
  difficulty?: Difficulty;   // 缺省为 NORMAL
  requireSuccess: boolean;   // true=要求成功，false=要求失败
}

interface RandomCondition {
  kind: "random";
  chance: number; // 0~1，进入该边的概率
}

type Condition =
  | { kind: "always" }
  | FlagCondition
  | CheckCondition
  | RandomCondition
  | { kind: "not"; condition: Condition }
  | { kind: "all"; conditions: Condition[] }
  | { kind: "any"; conditions: Condition[] };

// ==================== 节点与边 ====================

interface StoryNode {
  id: string;
  type: StoryNodeType;
  title: string;          // 场景名（展示用）
  text: string;           // 场景描述 / Keeper 旁白
  enterActions?: StoryAction[];
  exitActions?: StoryAction[];
  metadata?: Record<string, unknown>;
}

interface StoryEdge {
  id: string;
  from: string;           // 源节点 id
  to: string;             // 目标节点 id
  kind: EdgeKind;
  label?: string;         // CHOICE 时的玩家选项文案
  condition?: Condition;  // 缺省等价 always
  priority?: number;      // 默认 0，大者优先
  metadata?: Record<string, unknown>;
}

// ==================== 故事图（定义，可序列化） ====================

interface StoryGraphData {
  id: string;
  title: string;
  description: string;
  startNodeId: string;
  nodes: StoryNode[];
  edges: StoryEdge[];
}

interface StoryValidation {
  ok: boolean;
  errors: string[];   // 阻断性问题：悬挂引用、缺 start、重复 id 等
  warnings: string[]; // 非阻断：孤立节点、无出边的非 END 节点等
}

/** 故事流程图：只描述结构，不保存运行状态 */
class StoryGraph {
  id: string;
  title: string;
  description: string;
  startNodeId: string;
  nodes: StoryNode[] = []; // 唯一事实来源，保序
  edges: StoryEdge[] = [];

  private _nodeIndex?: Map<string, StoryNode>;
  private _edgeIndex?: Map<string, StoryEdge>;
  private _fromIndex?: Map<string, StoryEdge[]>; // from -> edges
  private _toIndex?: Map<string, StoryEdge[]>;   // to -> edges

  constructor(init: Partial<StoryGraphData> = {}) { Object.assign(this, init); }

  // ---------- 查询 ----------
  getNode(id: string): StoryNode | undefined;
  getEdge(id: string): StoryEdge | undefined;
  getStartNode(): StoryNode;
  getOutgoingEdges(nodeId: string): StoryEdge[];
  getIncomingEdges(nodeId: string): StoryEdge[];
  /** 某节点的全部玩家选项（kind=CHOICE 且有 label 的边） */
  getChoiceOptions(nodeId: string): StoryEdge[];

  // ---------- 增删改（同步维护索引） ----------
  addNode(node: StoryNode): boolean;  // id 重复返回 false
  updateNode(id: string, patch: Partial<Omit<StoryNode, 'id'>>): boolean;
  removeNode(id: string): boolean;    // 连带删除指向/离开该节点的所有边

  addEdge(edge: StoryEdge): boolean;  // id 重复或端点不存在返回 false
  updateEdge(id: string, patch: Partial<Omit<StoryEdge, 'id'>>): boolean;
  removeEdge(id: string): boolean;

  // ---------- 校验 / 序列化 ----------
  validate(): StoryValidation;
  toJSON(): StoryGraphData;
  static fromJSON(data: StoryGraphData): StoryGraph;
}

// ==================== 运行时会话 ====================

interface StorySnapshot {
  currentNodeId: string;
  visited: string[];
  visitCount: Record<string, number>;
  flags: Record<string, FlagValue>;
}

interface StoryOption {
  edgeId: string;
  label: string;
  edge: StoryEdge;
}

/** 单局游戏状态：游标、历史、flag、条件求值 */
class StorySession {
  graph: StoryGraph;
  currentNodeId: string;
  visited: string[] = [];              // 按访问顺序记录节点 id
  visitCount: Map<string, number>;     // 每个节点的访问次数
  flags: Map<string, FlagValue>;

  constructor(
    graph: StoryGraph,
    init?: { startNodeId?: string; flags?: Record<string, FlagValue>; rng?: () => number }
  );

  /** 重置并进入起始节点，返回起始节点 */
  start(): StoryNode;

  getCurrent(): StoryNode;
  isFinished(): boolean; // 当前节点 type === END

  /** 当前节点所有可走的边：先按 condition 过滤，再按 priority 降序 */
  getAvailableEdges(): StoryEdge[];
  /** 对玩家可见的选项（CHOICE 且有 label） */
  getOptions(): StoryOption[];

  /** 沿指定边转移：执行源节点 exitActions、目标节点 enterActions，并记录历史 */
  choose(edgeId: string): StoryNode;

  /**
   * 自动流转：若当前节点恰好有一条可走的 AUTO 边则沿它前进，
   * 直到遇到需要玩家选择、条件分支或 END 为止；
   * 无可自动前进的边时返回 null。maxSteps 防止死循环。
   */
  advance(maxSteps: number = 100): StoryNode | null;

  /** 条件求值（使用会话内 flags 与注入的 rng） */
  evaluate(condition: Condition): boolean;

  getFlag(flag: string): FlagValue | undefined;
  setFlag(flag: string, value: FlagValue): void;

  // ---------- 存档 / 读档 ----------
  snapshot(): StorySnapshot;
  restore(snapshot: StorySnapshot): void;
}

// ==================== 使用示例 ====================

// 构建一个三节点流程图：开场 -> 选择 -> 结局
const graph = StoryGraph.fromJSON({
  id: "demo",
  title: "例：雾中灯塔",
  description: "演示故事图",
  startNodeId: "n_start",
  nodes: [
    { id: "n_start", type: StoryNodeType.START, title: "开场", text: "你来到灯塔下。" },
    { id: "n_choice", type: StoryNodeType.SCENE, title: "大门", text: "大门紧锁，旁边有扇窗。" },
    { id: "n_end", type: StoryNodeType.END, title: "结局", text: "你从窗户爬了进去。" },
  ],
  edges: [
    { id: "e1", from: "n_start", to: "n_choice", kind: EdgeKind.AUTO },
    {
      id: "e2", from: "n_choice", to: "n_end", kind: EdgeKind.CHOICE, label: "撬窗进入",
      condition: {
        kind: "check",
        skillId: "skill_lockpick",
        requireSuccess: true,
      },
    },
  ],
});

const session = new StorySession(graph);
const current = session.start();       // n_start
session.advance();                     // AUTO 边 -> n_choice
const options = session.getOptions();  // [{ edgeId: "e2", label: "撬窗进入", ... }]
session.choose(options[0].edgeId);     // 检定成功则进入 n_end
if (session.isFinished()) { /* 剧情结束 */ }
```

> 实例：已将《鬼屋》（七版）初步映射为同目录下的 [`HauntingStoryGraph.json`](./HauntingStoryGraph.json)，可直接作为 `StoryGraphData` 的 JSON 实例参考。

## 模组素材与 Agent 注入

### 问题

上面的 `StoryGraph` 只解决了“剧情怎么走”（节点、边、条件、动作），
但一个完整的 COC 模组还需要注入 Agent 的素材远不止流程：

- 故事背景 / 时代 / 地点 / 基调
- NPC 介绍、性格、动机、隐藏秘密
- 敌人/怪物的外观与守密人属性
- 物品、线索、给玩家的文字材料（Handouts）
- 调查员能知道的信息 vs 只有守密人知道的信息

### 扩展：`StoryModuleData`

把“流程图”和“模组素材”拆成两层：

- `StoryGraphData`：只描述流程（已有）。
- `StoryModuleData`：整体模组包，包含 `StoryGraphData` + 各类“卡片”。

```typescript
// ==================== 模组素材（注入 Agent 用） ====================

/** 可见性：玩家可见 / 仅守密人可见 */
type Visibility = "public" | "keeper";

interface StoryMeta {
  id: string;
  title: string;
  era: string;            // 时代，如 "1920s"
  location: string;       // 地点
  summary: string;        // 模组简介
  background: string;     // 故事背景（守密人也需要了解）
  hook: string;           // 开场钩子 / 委托
  tone?: string;          // 氛围基调
  expectedLength?: string;
  endingConditions?: string[];
}

interface NpcCard {
  id: string;
  name: string;
  role: string;
  appearance?: string;       // 玩家可见的外貌
  personality?: string;      // 玩家可感知的性格
  publicNotes?: string;      // 玩家已知/可透露的信息
  keeperNotes?: string;      // 仅守密人：真实动机、秘密、规则提示
  secrets?: string[];
  stats?: Record<string, number>;
  appearsIn?: string[];      // 关联节点 id
}

interface CreatureCard {
  id: string;
  name: string;
  appearance?: string;       // 玩家看到的形态
  stats: Record<string, number>;
  hp?: number;
  mp?: number;
  armor?: string;
  attacks?: string[];        // 攻击描述
  spells?: string[];
  tactics?: string;          // 守密人战术
  sanityLoss?: string;       // 理智损失，如 "1/1D4"
  appearsIn?: string[];
}

interface ItemCard {
  id: string;
  name: string;
  publicDescription?: string;  // 玩家可见描述
  keeperEffects?: string;      // 真实效果 / 隐藏属性
  hiddenProperties?: string[];
  location?: string;           // 所在节点或 NPC
  obtainedBy?: string[];       // 获取条件 / 来源节点
  appearsIn?: string[];
}

interface ClueCard {
  id: string;
  title: string;
  content: string;             // 调查员获得后可看的内容
  visibility: Visibility;      // public=可直接叙述；keeper=仅守密人掌握
  revealCondition?: Condition; // 何时可揭示
  sourceNode?: string;         // 来源节点
  relatedNpcIds?: string[];
  relatedItemIds?: string[];
  relatedClueIds?: string[];
}

interface HandoutCard {
  id: string;
  title: string;
  content: string;             // 给玩家的文字材料
  imageRef?: string;           // 图片/材料引用
  givenBy?: string;            // 由哪个节点/NPC 给出
  revealCondition?: Condition;
}

interface Secret {
  id: string;
  title: string;
  content: string;             // 仅守密人
  revealCondition?: Condition;
  relatedNpcIds?: string[];
  relatedClueIds?: string[];
}

interface StoryModuleData {
  meta: StoryMeta;
  graph: StoryGraphData;
  npcs: NpcCard[];
  creatures: CreatureCard[];
  items: ItemCard[];
  clues: ClueCard[];
  handouts: HandoutCard[];
  secrets: Secret[];
}

/** 模组包：加载全部素材，提供索引与按需检索 */
class StoryModule {
  meta: StoryMeta;
  graph: StoryGraph;
  npcs: NpcCard[];
  creatures: CreatureCard[];
  items: ItemCard[];
  clues: ClueCard[];
  handouts: HandoutCard[];
  secrets: Secret[];

  // 惰性索引：id -> Card；appearsIn -> Card[] 等
  getNpc(id: string): NpcCard | undefined;
  getCreature(id: string): CreatureCard | undefined;
  getItem(id: string): ItemCard | undefined;
  getClue(id: string): ClueCard | undefined;
  getHandout(id: string): HandoutCard | undefined;
  getSecret(id: string): Secret | undefined;
  /** 取某个场景相关的全部素材（NPC/敌人/物品/线索/秘密） */
  getEntitiesForNode(nodeId: string): {
    npcs: NpcCard[];
    creatures: CreatureCard[];
    items: ItemCard[];
    clues: ClueCard[];
    secrets: Secret[];
  };

  validate(): StoryValidation;
  toJSON(): StoryModuleData;
  static fromJSON(data: StoryModuleData): StoryModule;
}

// ==================== Agent 上下文组装 ====================

interface AgentContextOptions {
  includeKeeperInfo: boolean;   // 是否在 prompt 中包含仅守密人信息
  maxEntitiesPerScene?: number; // 每个场景最多注入多少张卡片
}

/** 把模组素材 + 运行状态组装成给 LLM 的上下文 */
class StoryAgentContext {
  module: StoryModule;
  session: StorySession;

  /** 系统提示：身份、规则、模组全局背景、Keeper 秘密 */
  buildSystemPrompt(): string;
  /** 当前场景：节点文本、在场 NPC/物品/线索、可用选项 */
  buildScenePrompt(): string;
  /** 调查员状态：已知线索、持有物品、访问历史、flag */
  buildStatePrompt(): string;
  /** 完整 prompt */
  buildPrompt(): string;
  /** 按需取实体卡片（Agent 主动查询时用） */
  resolveEntity(kind: "npc" | "creature" | "item" | "clue" | "handout", id: string): string;
  /** 已满足 revealCondition 的线索/秘密 */
  getRevealedClues(): ClueCard[];
  /** 供 Function Calling 使用的工具描述 */
  buildToolDefinitions(): unknown[];
}
```

### 注入策略

1. **分层注入，不一次性全塞**
   - `buildSystemPrompt()`：身份 + 规则 + 模组 `meta` + `secrets`（仅守密人）。
   - `buildScenePrompt()`：只注入当前节点相关的卡片（`appearsIn` 命中当前节点）。
   - `buildStatePrompt()`：已获得线索、物品、flag、访问历史。
   - 防止 token 爆炸，长文本（如整本 Handout）只在玩家索要或触发展示时再取。

2. **可见性过滤**
   - `public` 字段可被 Agent 直接叙述给玩家。
   - `keeper` / `Secret` / `keeperNotes` 只进系统侧 prompt，要求 Agent 不得主动泄露，仅在满足条件时揭示。

3. **按需检索 + Function Calling**
   - 玩家问到某个 NPC/物品/地点时，Agent 调用 `resolveEntity(...)` 取对应卡片，而不是把整个模组都放进上下文。
   - 提供 `revealClue`、`getNpc`、`getItem`、`choose`、`rollCheck`、`setFlag` 等工具。

4. **状态与素材联动**
   - `StorySession.flags` 记录“是否已获得某线索/物品”。
   - `ClueCard.revealCondition` 命中后，才把它从“待揭示”移入 `getRevealedClues()`。
   - Agent 叙述时以“已揭示线索 + 当前场景”为准，避免剧透。

> 实例：除流程 JSON 外，另将《鬼屋》的元数据/NPC/敌人/物品/线索/秘密整理为 [`HauntingStoryModule.json`](./HauntingStoryModule.json)，作为 `StoryModuleData` 的参考。

> Python 实现：接口已按本设计实现于 `keeper/base/story.py`，可通过 `StoryModule.from_json()` 加载 [`HauntingStoryModule.json`](./HauntingStoryModule.json) 进行运行。
