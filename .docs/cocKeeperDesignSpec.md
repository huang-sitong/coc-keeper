# coc-keeper设计说明书

## 数据对象

### 调查员相关类

> 模型依据 `nouxiaxia.json`（COC7 调查员角色卡）定义。
> `experiencedModules`、`friends` 在 JSON 中为字符串序列化数组，建模统一为强类型数组，由存储层负责序列化。
> 索引策略：list 为唯一事实来源（保序、可容纳重名占位项），`id → Skill`、`skillId → Weapon[]` 索引惰性构建、增删改时同步维护；重名占位技能一律按 `id` 区分，按名查询仅用于展示。
> `characterStatus` 在 JSON 中为中文布尔键（`"重伤"` 等），建模统一映射为英文属性名，由存储层转换。

```typescript
// ==================== 通用：检定系统 ====================

/** 检定难度 */
enum Difficulty { NORMAL, HARD, EXTREME } // 普通 / 困难(1/2) / 极难(1/5)

type CheckLevel = 'critical' | 'extreme' | 'hard' | 'success' | 'fail' | 'fumble';

interface CheckResult {
  roll: number;    // 骰出值 1-100
  target: number;  // 按难度换算后的目标值
  success: boolean;
  level: CheckLevel;
}

/** 掷 d100 */
function rollD100(rng: () => number = Math.random): number {
  return Math.floor(rng() * 100) + 1;
}

/** 解析掷骰表达式（"2D6+1"、"1D3+DB"），DB 替换为角色伤害加值后整体计算 */
function rollDice(expr: string, db: string = '0', rng: () => number = Math.random): number {
  const normalized = expr.replace(/DB/gi, db || '0').replace(/\+-/g, '-');
  return normalized.split(/(?=[+-])/).reduce((sum, term) => {
    const sign = term.startsWith('-') ? -1 : 1;
    const t = term.replace(/^[+-]/, '');
    const m = t.match(/^(\d*)d(\d+)$/i);
    if (m) {
      const times = m[1] === '' ? 1 : Number(m[1]);
      const die = Number(m[2]);
      let s = 0;
      for (let i = 0; i < times; i++) s += Math.floor(rng() * die) + 1;
      return sum + sign * s;
    }
    return sum + sign * (Number(t) || 0);
  }, 0);
}

/**
 * COC7 检定裁决（Skill / Attributes 共用）：
 * 大失败 = 100，技能值 <50 时 96-99 亦失败；
 * 大成功 = 01-05 且不超过技能值；极难 ≤1/5；困难 ≤1/2；普通 ≤技能值。
 */
function resolveCheck(roll: number, value: number, difficulty: Difficulty = Difficulty.NORMAL): CheckResult {
  const target = difficulty === Difficulty.HARD    ? Math.floor(value / 2)
               : difficulty === Difficulty.EXTREME ? Math.floor(value / 5)
               : value;

  if (roll === 100 || (roll >= 96 && value < 50))
    return { roll, target, success: false, level: 'fumble' };
  if (roll <= 5 && roll <= value)
    return { roll, target, success: true, level: 'critical' };
  if (roll <= target) {
    const level = difficulty === Difficulty.EXTREME ? 'extreme'
                : difficulty === Difficulty.HARD     ? 'hard'
                : 'success';
    return { roll, target, success: true, level };
  }
  return { roll, target, success: false, level: 'fail' };
}

/** 攻击结算结果 */
interface AttackResult {
  weaponId: string;
  weaponName: string;
  damage: string;            // 伤害公式，DB 已替换为角色伤害加值
  attacks: string;           // 攻击次数说明（tho）
  range: string;
  ammoLeft: number | string; // 扣 1 发后的剩余弹药
  jammed: boolean;           // 大失败时按 err 判定的卡壳
}

/** 完整攻击流程结果：检定 + 结算 + 伤害掷骰 */
interface AttackBySkillResult {
  skillId: string;
  skillName: string;
  weaponId?: string;       // 实际使用的武器（未指定时自动选第一把）
  check: CheckResult;
  attack?: AttackResult;   // 命中或大失败（故障判定）时存在
  hit: boolean;
  damageRoll?: number;     // 命中时的伤害掷骰
}

/** 受到伤害结算结果 */
interface DamageResult {
  amount: number;          // 本次伤害值
  current: number;         // 结算后的当前 HP（可为负）
  majorWound: boolean;     // 是否大伤害（一次伤害 ≥ max 的一半）
  conCheck?: CheckResult;  // 大伤害时的体质检定
  unconscious: boolean;    // 是否陷入昏迷
  dying: boolean;          // 是否濒死（HP ≤ 0 且 > -max）
  dead: boolean;           // 是否死亡（HP ≤ -max）
}

// ==================== 技能 ====================

/** 技能所属类目（与 JSON skillGroups 键一一对应） */
enum SkillGroup {
  SPECIAL = "special", EXPLORE = "explore", SOCIAL = "social", COMBAT = "combat",
  MEDICAL = "medical", MOVE = "move", KNOWLEDGE = "knowledge", TECH = "tech",
  DRIVE = "drive", OTHER = "other"
}

/**
 * 技能条目。占位技能（如 "科学:"、"外语:"）靠 id 区分，
 * 总值与各级成功率均为派生值，不入库。
 */
class Skill {
  id: string;
  name: string;            // 可定制项以冒号前缀占位，如 "科学:"
  base: number;            // 基础值
  job: number;             // 职业技能点
  interest: number;        // 兴趣技能点
  growth: number;          // 成长值
  isProfessional: boolean; // 是否职业技能

  constructor(init: Partial<Skill> = {}) { Object.assign(this, init); }

  get total(): number          { return this.base + this.job + this.interest + this.growth; }
  get success(): number        { return this.total; }
  get hardSuccess(): number    { return Math.floor(this.total / 2); }
  get extremeSuccess(): number { return Math.floor(this.total / 5); }

  check(difficulty: Difficulty = Difficulty.NORMAL, rng: () => number = Math.random): CheckResult {
    return resolveCheck(rollD100(rng), this.total, difficulty);
  }

  /** 成长检定：检定成功且骰值 > 当前值，则 growth += 1d10 */
  grow(rng: () => number = Math.random): boolean {
    const c = this.check(Difficulty.NORMAL, rng);
    if (!c.success || c.roll <= this.total) return false;
    this.growth += Math.floor(rng() * 10) + 1;
    return true;
  }
}

/** 技能组：十个类目各持一个列表；id 索引惰性构建，增删时同步维护 */
class SkillGroups {
  special:   Skill[] = [];
  explore:   Skill[] = [];
  social:    Skill[] = [];
  combat:    Skill[] = [];
  medical:   Skill[] = [];
  move:      Skill[] = [];
  knowledge: Skill[] = [];
  tech:      Skill[] = [];
  drive:     Skill[] = [];
  other:     Skill[] = [];

  private _index?: Map<string, Skill>; // id -> Skill

  private allGroupLists(): Skill[][] {
    return [this.special, this.explore, this.social, this.combat, this.medical,
            this.move, this.knowledge, this.tech, this.drive, this.other];
  }

  /** 全部技能扁平列表 */
  getAllSkills(): Skill[] { return this.allGroupLists().flat(); }

  /** 某类目下的技能 */
  getSkillsByGroup(group: SkillGroup): Skill[] { return this[group]; }

  /** 按 id 取技能（O(1)；判定一律走 id） */
  getSkillById(id: string): Skill | undefined {
    if (!this._index) {
      this._index = new Map(this.getAllSkills().map(s => [s.id, s]));
    }
    return this._index.get(id);
  }

  /** 按名查询（仅展示用）；重名占位项返回第一个 */
  getSkillByName(name: string): Skill | undefined {
    return this.getSkillsByName(name)[0];
  }

  /** 按名查询全部同名技能 */
  getSkillsByName(name: string): Skill[] {
    return this.getAllSkills().filter(s => s.name === name);
  }

  /** 新增技能；id 重复返回 false */
  addSkill(group: SkillGroup, s: Skill): boolean {
    if (this.getSkillById(s.id)) return false;
    this[group].push(s);
    this._index?.set(s.id, s);
    return true;
  }

  /** 按 id 移除 */
  removeSkill(id: string): boolean {
    for (const list of this.allGroupLists()) {
      const i = list.findIndex(s => s.id === id);
      if (i >= 0) {
        list.splice(i, 1);
        this._index?.delete(id);
        return true;
      }
    }
    return false;
  }

  /** 局部更新（id 不可改） */
  updateSkill(id: string, patch: Partial<Omit<Skill, 'id'>>): boolean {
    const s = this.getSkillById(id);
    if (!s) return false;
    Object.assign(s, patch);
    return true;
  }

  /** 全员成长检定，返回发生成长的技能 */
  applyGrowth(rng: () => number = Math.random): Skill[] {
    return this.getAllSkills().filter(s => s.grow(rng));
  }
}

// ==================== 属性 ====================

/** 八项基础属性 + 幸运（字符串值与 JSON attributes 键一致，供按名访问） */
enum AttributeName {
  STR = "str", DEX = "dex", CON = "con", APP = "app",
  POW = "pow", SIZ = "siz", EDU = "edu", INT = "int", LUC = "luc"
}

class Attributes {
  str = 0; dex = 0; con = 0; app = 0; pow = 0;
  siz = 0; edu = 0; int = 0; luc = 0;

  /** 按名取值 */
  get(name: AttributeName): number { return this[name]; }

  /** 属性检定 */
  check(name: AttributeName, difficulty: Difficulty = Difficulty.NORMAL, rng: () => number = Math.random): CheckResult {
    return resolveCheck(rollD100(rng), this.get(name), difficulty);
  }
}

/** 派生属性：理智 / 生命 / 魔法 */
class DeriveAttributes {
  sanity: { current: number; start: number; max: number } = { current: 0, start: 0, max: 99 };
  hp:     { current: number; max: number } = { current: 0, max: 0 };
  mp:     { current: number; max: number } = { current: 0, max: 0 };
}

/** 战斗属性 */
class BattleAttributes {
  db = "0";      // 伤害加值，如 "+1d4"
  build = 0;     // 体型值
  mov = 8;       // 移动力
  movNote = "";  // 移动力备注
  armor = "0";   // 护甲
}

// ==================== 状态 ====================

/** 身体状态 */
class BodyStates {
  injured = false;     // 重伤
  dead = false;        // 死亡
  unconscious = false; // 昏迷
}

/** 精神状态 */
class MentalStates {
  permanentlyInsane = false;  // 永久疯狂
  temporarilyInsane = false;  // 临时疯狂
  indefinitelyInsane = false; // 不定期疯狂
}

/** 角色状态 */
class CharacterStatus {
  bodyStates = new BodyStates();
  mentalStates = new MentalStates();

  /** 生效中的身体状态名列表 */
  getActiveBodyStates(): string[] {
    return (Object.keys(this.bodyStates) as Array<keyof BodyStates>)
      .filter(k => this.bodyStates[k]);
  }

  /** 生效中的精神状态名列表 */
  getActiveMentalStates(): string[] {
    return (Object.keys(this.mentalStates) as Array<keyof MentalStates>)
      .filter(k => this.mentalStates[k]);
  }

  /** 是否失去行动能力 */
  isIncapacitated(): boolean { return this.bodyStates.unconscious || this.bodyStates.dead; }

  /** 是否处于任意疯狂状态 */
  isMad(): boolean {
    return this.mentalStates.permanentlyInsane
        || this.mentalStates.temporarilyInsane
        || this.mentalStates.indefinitelyInsane;
  }
}

// ==================== 武器 ====================

/** 武器条目 */
class Weapon {
  id: string;
  name: string;
  skill: string;   // 关联技能名（与技能名写法需归一化）
  skillId: string; // 关联技能 id（推荐，O(1) 取技能）
  damage: string;  // 伤害公式，如 "2D6+1"
  range = "";
  tho = "1";       // 每轮攻击次数
  round = "";      // 弹夹/连射说明
  num = "";        // 弹药数
  err = "";        // 故障值
  weight = "";
  note = "";
  success = "";    // 成功率（留空，由技能派生）

  constructor(init: Partial<Weapon> = {}) { Object.assign(this, init); }
}

/** 武器表：list 存储，skillId 反向索引惰性构建、增删改时同步维护 */
class WeaponList {
  items: Weapon[] = [];

  private _indexBySkill?: Map<string, Weapon[]>;

  /** skillId -> Weapon[]（一个技能可对应多把武器） */
  getWeaponsBySkillId(skillId: string): Weapon[] {
    if (!this._indexBySkill) {
      this._indexBySkill = new Map();
      for (const w of this.items) {
        if (!w.skillId) continue;
        const list = this._indexBySkill.get(w.skillId);
        if (list) list.push(w);
        else this._indexBySkill.set(w.skillId, [w]);
      }
    }
    return this._indexBySkill.get(skillId) ?? [];
  }

  getWeaponById(id: string): Weapon | undefined {
    return this.items.find(w => w.id === id);
  }

  /** 新增；id 重复返回 false */
  addWeapon(w: Weapon): boolean {
    if (this.getWeaponById(w.id)) return false;
    this.items.push(w);
    if (this._indexBySkill) this.addToIndex(w);
    return true;
  }

  /** 按 id 移除，同步清理索引 */
  removeWeapon(id: string): boolean {
    const i = this.items.findIndex(w => w.id === id);
    if (i < 0) return false;
    const [w] = this.items.splice(i, 1);
    if (this._indexBySkill && w.skillId) this.removeFromIndex(id, w.skillId);
    return true;
  }

  /** 局部更新；skillId 变更时同步迁移索引 */
  updateWeapon(id: string, patch: Partial<Omit<Weapon, 'id'>>): boolean {
    const w = this.getWeaponById(id);
    if (!w) return false;
    const oldSkillId = w.skillId;
    Object.assign(w, patch);
    if (this._indexBySkill && oldSkillId !== w.skillId) {
      this.removeFromIndex(id, oldSkillId);
      this.addToIndex(w);
    }
    return true;
  }

  private addToIndex(w: Weapon): void {
    if (!w.skillId) return;
    const list = this._indexBySkill!.get(w.skillId);
    if (list) list.push(w);
    else this._indexBySkill!.set(w.skillId, [w]);
  }

  private removeFromIndex(id: string, skillId: string): void {
    const list = this._indexBySkill!.get(skillId);
    if (!list) return;
    const j = list.findIndex(x => x.id === id);
    if (j >= 0) list.splice(j, 1);
    if (list.length === 0) this._indexBySkill!.delete(skillId);
  }
}

// ==================== 背景 ====================

/** 个人故事与描述 */
class Stories {
  app = "";      // 形象描述
  belief = "";   // 思想与信念
  IPerson = "";  // 重要之人
  IPlace = "";   // 重要之地
  IItem = "";    // 重要之物
  trait = "";    // 特质
  scar = "";     // 伤口与疤痕
  mad = "";      // 恐惧与疯狂
  desc = "";     // 个人介绍
}

/** 资产与随身物品 */
class Assets {
  cash = "0";        // 现金
  consumption = "0"; // 消费水平
  assets = "";       // 资产
  items = "";        // 随身物品
  magicItems = "";   // 魔法物品
  magics = "";       // 法术/魔法
  touches = "";      // 接触之物
}

/** 经历过的模组 */
class ExperiencedModule {
  name = "";
  experience = "";
}

/** 盟友/好友 */
class Friend {
  character = "";
  relationship = "";
  player = "";
}

// ==================== 调查员（根对象） ====================

/** 完整调查员角色卡，对应 nouxiaxia.json 根对象 */
class Investigator {
  // ---- 基本信息 ----
  name = "";
  playerName = "";
  time = "";
  job = "";
  age = "";
  gender = "";
  location = "";
  hometown = "";
  era = "";
  isEditable = true;

  // ---- 属性 ----
  attributes = new Attributes();
  deriveAttributes = new DeriveAttributes();
  battleAttributes = new BattleAttributes();

  // ---- 状态 ----
  characterStatus = new CharacterStatus();

  // ---- 点数 ----
  pointValues: Record<string, number> = {}; // 剩余职业/兴趣点等
  proSkills: string[] = [];                 // 职业可选技能
  skillPoints: number[] = [];

  // ---- 战斗 / 背景 / 技能 ----
  weapons = new WeaponList();
  stories = new Stories();
  assets = new Assets();
  experiencedModules: ExperiencedModule[] = [];
  friends: Friend[] = [];
  skillGroups = new SkillGroups();

  // ============ 委托访问 ============

  getSkill(skillId: string): Skill | undefined {
    return this.skillGroups.getSkillById(skillId);
  }

  /** 按名取技能（仅展示用） */
  getSkillByName(name: string): Skill | undefined {
    return this.skillGroups.getSkillByName(name);
  }

  /** 按名查询全部同名技能 */
  getSkillsByName(name: string): Skill[] {
    return this.skillGroups.getSkillsByName(name);
  }

  getAttribute(name: AttributeName): number {
    return this.attributes.get(name);
  }

  getWeaponsBySkill(skillId: string): Weapon[] {
    return this.weapons.getWeaponsBySkillId(skillId);
  }

  // ============ 检定 ============

  /** 技能检定（按 id） */
  checkSkill(skillId: string, difficulty: Difficulty = Difficulty.NORMAL, rng?: () => number): CheckResult | undefined {
    return this.getSkill(skillId)?.check(difficulty, rng);
  }

  /** 属性检定（按名） */
  checkAttribute(name: AttributeName, difficulty: Difficulty = Difficulty.NORMAL, rng?: () => number): CheckResult {
    return this.attributes.check(name, difficulty, rng);
  }

  // ============ 攻击 ============

  /**
   * 命中后的结算（不做检定，由调用方先行检定）：
   * 伤害公式（DB 替换）、弹药扣 1 发、大失败时按 err 判卡壳。
   */
  attack(weaponId: string, checkResult?: CheckResult, rng: () => number = Math.random): AttackResult | undefined {
    const w = this.weapons.getWeaponById(weaponId);
    if (!w) return undefined;

    let ammoLeft: number | string = w.num;
    if (w.num !== '' && !isNaN(Number(w.num))) {
      ammoLeft = Number(w.num) - 1;
      w.num = String(ammoLeft);
    }

    let jammed = false;
    if (checkResult?.level === 'fumble' && w.err !== '') {
      jammed = rollD100(rng) >= Number(w.err);
    }

    return {
      weaponId: w.id,
      weaponName: w.name,
      damage: w.damage.replace(/DB/gi, this.battleAttributes.db),
      attacks: w.tho,
      range: w.range,
      ammoLeft,
      jammed,
    };
  }

  /** 掷武器伤害（解析伤害公式） */
  rollWeaponDamage(weaponId: string, rng: () => number = Math.random): number | undefined {
    const w = this.weapons.getWeaponById(weaponId);
    if (!w || w.damage === '') return undefined;
    return rollDice(w.damage, this.battleAttributes.db, rng);
  }

  /**
   * 完整攻击流程：技能检定 → 选武器（指定或自动取第一把）→ 命中结算 →
   * 伤害掷骰。大失败不命中但走 attack 判卡壳；技能/武器不存在返回 undefined。
   */
  attackBySkill(
    skillId: string,
    weaponId?: string,
    difficulty: Difficulty = Difficulty.NORMAL,
    rng: () => number = Math.random
  ): AttackBySkillResult | undefined {
    const sk = this.getSkill(skillId);
    if (!sk) return undefined;

    const check = sk.check(difficulty, rng);
    const w = weaponId
      ? this.weapons.getWeaponById(weaponId)
      : this.weapons.getWeaponsBySkillId(skillId)[0];

    const attack = w && (check.success || check.level === 'fumble')
      ? this.attack(w.id, check, rng)
      : undefined;
    const hit = check.success && !!attack;

    return {
      skillId,
      skillName: sk.name,
      weaponId: w?.id,
      check,
      attack,
      hit,
      damageRoll: hit ? this.rollWeaponDamage(w!.id, rng) : undefined,
    };
  }

  // ============ 伤害 ============

  /**
   * 受到伤害结算（COC7）：
   *  - 扣血并写回 hp.current（下限 -max）
   *  - 大伤害（一次 ≥ max 一半）：CON 检定失败 → 昏迷
   *  - HP ≤ 0：濒死（昏迷 + 重伤标记）；HP ≤ -max：死亡
   */
  takeDamage(amount: number, rng: () => number = Math.random): DamageResult {
    const hp = this.deriveAttributes.hp;
    const body = this.characterStatus.bodyStates;

    hp.current = Math.max(hp.current - amount, -hp.max);

    const majorWound = amount > 0 && amount * 2 >= hp.max && hp.max > 0;
    let conCheck: CheckResult | undefined;
    let unconscious = false;
    if (majorWound) {
      conCheck = this.checkAttribute(AttributeName.CON, Difficulty.NORMAL, rng);
      unconscious = !conCheck.success;
      if (unconscious) body.unconscious = true;
    }

    const dying = hp.current <= 0 && hp.current > -hp.max;
    const dead = hp.current <= -hp.max;
    if (dead) {
      body.dead = true;
      body.unconscious = true;
    } else if (dying) {
      body.injured = true;
      body.unconscious = true;
    }

    return { amount, current: hp.current, majorWound, conCheck, unconscious, dying, dead };
  }

  /**
   * 濒死轮检定：每轮 CON 检定失败则 HP -1 恶化，直至死亡或获救（HP 回正后停止）。
   * 返回 true 表示本轮检定成功（暂时稳住）。
   */
  resolveDying(rng: () => number = Math.random): boolean {
    const hp = this.deriveAttributes.hp;
    if (hp.current > 0 || hp.current <= -hp.max) return false;

    const c = this.checkAttribute(AttributeName.CON, Difficulty.NORMAL, rng);
    if (!c.success) {
      hp.current -= 1;
      if (hp.current <= -hp.max) this.characterStatus.bodyStates.dead = true;
    }
    return c.success;
  }

  // ============ COC7 派生计算 ============

  /** 克苏鲁神话技能值（该技能唯一，按名取安全） */
  getCthulhuMythos(): number {
    return this.getSkillByName('克苏鲁神话')?.total ?? 0;
  }

  deriveHpMax(): number    { return Math.floor((this.attributes.con + this.attributes.siz) / 10); }
  deriveMpMax(): number    { return Math.floor(this.attributes.pow / 5); }
  deriveSanityMax(): number { return 99 - this.getCthulhuMythos(); }

  /** 伤害加值 / 体型值（STR+SIZ 查表） */
  deriveDamageBonus(): string {
    const s = this.attributes.str + this.attributes.siz;
    if (s <= 64)  return '-2';
    if (s <= 84)  return '-1';
    if (s <= 124) return '0';
    if (s <= 164) return '+1d4';
    if (s <= 204) return '+1d6';
    if (s <= 284) return '+2d6';
    if (s <= 364) return '+3d6';
    return '+4d6';
  }

  deriveBuild(): number {
    const s = this.attributes.str + this.attributes.siz;
    if (s <= 64)  return -2;
    if (s <= 84)  return -1;
    if (s <= 124) return 0;
    if (s <= 164) return 1;
    if (s <= 204) return 2;
    if (s <= 284) return 3;
    if (s <= 364) return 4;
    return 5;
  }

  /** 移动力：STR/SIZ 均 <8 → 9；均 <12 → 8；任一 ≥12 → 7 */
  deriveMov(): number {
    const { str, siz } = this.attributes;
    if (str < 8 && siz < 8) return 9;
    if (str < 12 && siz < 12) return 8;
    return 7;
  }

  /** 同步全部派生值（创建/洗点时调用） */
  syncDerived(): void {
    this.deriveAttributes.hp.max = this.deriveHpMax();
    this.deriveAttributes.mp.max = this.deriveMpMax();
    this.deriveAttributes.sanity.max = this.deriveSanityMax();
    this.battleAttributes.db = this.deriveDamageBonus();
    this.battleAttributes.build = this.deriveBuild();
    this.battleAttributes.mov = this.deriveMov();
  }
}
```
