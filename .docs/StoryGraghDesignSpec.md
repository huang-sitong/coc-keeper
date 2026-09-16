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
