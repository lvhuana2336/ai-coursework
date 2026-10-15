"""
贪吃蛇 - 基础框架
基于 Pygame · 方向键控制 · 吃到食物增长 · 撞墙/撞身体结束
"""

import pygame
import sys
import random
import math
import json
import os
import array
import wave
from collections import deque

# ==================== 常量配置 ====================
CELL_SIZE = 20                                  # 每格像素大小
GRID_W = 30                                     # 网格宽度（列数）
GRID_H = 22                                     # 网格高度（行数）
SCREEN_W = CELL_SIZE * GRID_W
SCREEN_H = CELL_SIZE * GRID_H

FPS_BASE = 8                                     # 基础速度（帧/秒，默认值，实际由难度覆盖）
FPS_MAX = 20                                     # 速度上限
FPS_PER_SCORE = 0.15                              # 每得 1 分增加的速度（平缓）
RENDER_FPS = 60                                   # 画面渲染帧率
WALL_COUNT = 6                                    # 初始随机墙体数量（默认值，实际由难度覆盖）
ENEMY_COUNT = 2                                   # 敌对生物数量（默认值，实际由难度覆盖）
ENEMY_MOVE_DELAY = 3                               # 敌对生物每 N 帧移动一次（慢于蛇）
GIANT_FOOD_INTERVAL = 12                            # 巨大食物生成间隔（秒）
GIANT_FOOD_DURATION = 6                             # 巨大食物持续时间（秒）
GIANT_FOOD_SCORE = 5                                # 巨大食物分值
SHIELD_SPAWN_INTERVAL = 30                          # 光盾生成间隔（秒）
SHIELD_DURATION = 6                                 # 光盾停留时间（秒）
SHIELD_EFFECT_TIME = 5                              # 拾取后护盾持续时长（秒）

# ---------- 颜色 ----------
BG_COLOR = (28, 32, 40)                         # 深色背景
GRID_COLOR = (38, 42, 52)                       # 网格线
SNAKE_HEAD = (100, 200, 120)                    # 蛇头色
SNAKE_BODY = (70, 160, 90)                      # 蛇身色
FOOD_COLOR = (230, 80, 70)                      # 食物色
WALL_COLOR = (90, 85, 100)                       # 墙体色
ENEMY_COLOR = (210, 105, 40)                     # 敌对生物色
GIANT_FOOD_COLOR = (255, 200, 50)                  # 巨大食物色
GIANT_FOOD_OUTLINE = (180, 140, 30)                # 巨大食物描边
SCORE_COLOR = (180, 190, 200)                   # 分数字色
GAMEOVER_COLOR = (220, 210, 180)                # 结束文字色
SHIELD_COLOR = (100, 180, 255)                  # 光盾道具色（浅蓝）
SHIELD_GLOW = (130, 200, 255)                   # 光盾发光色

# ---------- 菜单配色 ----------
MENU_BG = (28, 32, 40)                          # 菜单背景（与游戏一致）
MENU_TITLE = (120, 220, 140)                    # 菜单标题（蛇绿）
MENU_SUBTITLE = (150, 160, 175)                 # 副标题
MENU_BTN_NORMAL = (45, 52, 64)                  # 按钮默认底色
MENU_BTN_HOVER = (62, 74, 92)                   # 按钮悬停底色
MENU_BTN_BORDER = (82, 98, 120)                 # 按钮边框
MENU_BTN_TEXT = (212, 222, 232)                 # 按钮文字
MENU_BTN_TEXT_HOVER = (255, 255, 255)          # 按钮悬停文字
MENU_ACCENT = (120, 220, 140)                   # 强调绿
MENU_RECORD = (210, 200, 170)                   # 历史记录文字

# ==================== 难度配置 ====================
# 难度等级：0=简单, 1=中等, 2=困难
DIFFICULTY_NAMES = ["简单", "中等", "困难"]

# 各难度对应的游戏参数预设
DIFFICULTY_PRESETS = [
    {"fps_base": 6,  "fps_max": 14, "fps_per_score": 0.12, "wall_count": 3,  "enemy_count": 1},  # 简单
    {"fps_base": 8,  "fps_max": 20, "fps_per_score": 0.15, "wall_count": 6,  "enemy_count": 2},  # 中等
    {"fps_base": 11, "fps_max": 26, "fps_per_score": 0.20, "wall_count": 10, "enemy_count": 4},  # 困难
]

DIFFICULTY = 1                                   # 当前难度（默认中等）

DIFFICULTY_DESC = [
    "3处障碍 · 1只怪物 · 较低的初始速度",     # 简单
    "6处障碍 · 2只怪物 · 初始速度适中",       # 中等
    "10处障碍 · 4只怪物 · 较高的初始速度",    # 困难
]

# ==================== 历史记录 ====================
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snake_history.json")
HISTORY_MAX = 10                                 # 每个难度最多保留的记录条数


def load_all_history() -> dict:
    """读取全部历史记录，返回 {难度: [{'score': int, 'date': str}, ...]}"""
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                # 兼容旧格式 → 全部归入 "默认"
                return {"_legacy": data}
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_history(difficulty: int) -> list:
    """读取指定难度的历史记录（分数降序）"""
    all_records = load_all_history()
    return all_records.get(str(difficulty), [])


def add_history(score: int, difficulty: int) -> None:
    """将一局得分追加进对应难度的历史记录并保留 Top N"""
    if score <= 0:
        return
    from datetime import datetime
    all_records = load_all_history()
    key = str(difficulty)
    records = all_records.get(key, [])
    records.append({
        "score": score,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    records.sort(key=lambda r: r["score"], reverse=True)
    all_records[key] = records[:HISTORY_MAX]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(all_records, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def set_difficulty(level: int) -> None:
    """设置当前难度等级（0/1/2）"""
    global DIFFICULTY
    DIFFICULTY = max(0, min(2, level))

# ==================== 音效管理 ====================
class SoundManager:
    """程序化合成并播放得分/扣分音效，无音频设备时静默降级"""

    RATE = 22050                                # 采样率（Hz）
    AMPLITUDE = 8000                            # 峰值振幅

    def __init__(self):
        self.enabled = True
        try:
            # 初始化混音器（无设备或已初始化时容错）
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(self.RATE, -16, 1, 512)
        except pygame.error:
            self.enabled = False

        self._score_sound = None
        self._penalty_sound = None
        if self.enabled:
            try:
                # 生成临时 WAV 文件 → 加载为 Sound 对象
                self._score_sound = self._make_sound(
                    [self._tone(f0=900, f1=1500, dur=0.16)])     # 得分：上扬"叮"
                self._penalty_sound = self._make_sound(
                    [self._tone(f0=260, f1=180, dur=0.30)])      # 扣分：低沉"嘟"
            except Exception:
                self.enabled = False
                self._score_sound = None
                self._penalty_sound = None

    # ---------- 波形合成 ----------
    def _tone(self, f0: float, f1: float, dur: float) -> array.array:
        """生成从 f0 线性过渡到 f1 的正弦波，带淡入淡出包络，返回 16bit 采样"""
        n = int(self.RATE * dur)
        samples = array.array("h")
        for i in range(n):
            t = i / n
            freq = f0 + (f1 - f0) * t
            # 正弦波 + 谐波增强，末段加入颤音使扣分音更明显
            value = math.sin(2 * math.pi * freq * (i / self.RATE))
            value += 0.25 * math.sin(4 * math.pi * freq * (i / self.RATE))
            # 淡入淡出包络（避免爆音）
            env = min(1.0, i / max(1, int(self.RATE * 0.01)),
                      1.0 - max(0.0, (t - 0.85) / 0.15))
            samples.append(int(value * self.AMPLITUDE * env))
        return samples

    @staticmethod
    def _make_sound(channels: list) -> pygame.mixer.Sound:
        """将若干采样片段写为临时 WAV 并加载为 Sound"""
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            with wave.open(path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(SoundManager.RATE)
                for ch in channels:
                    w.writeframes(ch.tobytes())
            return pygame.mixer.Sound(path)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    # ---------- 播放 ----------
    def play_score(self) -> None:
        """播放得分音效"""
        if self.enabled and self._score_sound is not None:
            self._score_sound.play()

    def play_penalty(self) -> None:
        """播放扣分音效"""
        if self.enabled and self._penalty_sound is not None:
            self._penalty_sound.play()


# ==================== 方向常量 ====================
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

# 字体缓存
_font_cache = {}
_score_font = None
_gameover_font = None


def _get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """字体缓存，避免重复创建"""
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("microsoftyahei", size, bold=bold)
    return _font_cache[key]


# ==================== 游戏逻辑 ====================
class SnakeGame:
    """管理蛇的数据、食物、碰撞检测和分数"""

    def __init__(self):
        self.sound = SoundManager()      # 音效管理器（得分/扣分音效）
        self.reset()

    # ---------- 2×2 方块工具 ----------
    @staticmethod
    def _block_cells(pos: tuple) -> set:
        """返回以 pos 为左上角的 2×2 方块占用的 4 个格子"""
        x, y = pos
        return {(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)}

    def _enemy_cells(self) -> set:
        """返回所有敌对生物占用的格子集合"""
        cells = set()
        for pos in self.enemies:
            cells |= self._block_cells(pos)
        return cells

    def _giant_food_cells(self) -> set:
        """返回巨大食物占用的格子集合"""
        if self.giant_food is None:
            return set()
        return self._block_cells(self.giant_food)

    def _shield_cells(self) -> set:
        """返回光盾道具占用的格子集合"""
        if self.shield_powerup is None:
            return set()
        return {self.shield_powerup}

    # ---------- 重置 ----------
    def reset(self):
        """重置游戏到初始状态（难度参数从当前难度预设读取）"""
        # 读取难度预设（速度、墙体数、敌人数等）
        preset = DIFFICULTY_PRESETS[DIFFICULTY]
        self.fps_base = preset["fps_base"]
        self.fps_max = preset["fps_max"]
        self.fps_per_score = preset["fps_per_score"]
        self.wall_count = preset["wall_count"]
        self.enemy_count = preset["enemy_count"]

        # 蛇初始位置：水平 3 格，居中
        start_x = GRID_W // 2
        start_y = GRID_H // 2
        self.snake = [
            (start_x, start_y),
            (start_x - 1, start_y),
            (start_x - 2, start_y),
        ]
        self.direction = RIGHT
        self.direction_queue = deque()               # 预输入队列
        self.enemies = []                            # 先初始化为空（_spawn_food 需要引用）
        self.giant_food = None                       # 先初始化为空（_spawn_food 需要引用）
        self.shield_powerup = None                    # 必须先于 _spawn_obstacles 初始化
        self.shield_powerup_spawn_time = 0
        self.last_shield_spawn_time = pygame.time.get_ticks()
        self.shield_active_until = 0
        self.obstacles = self._spawn_obstacles()     # 必须先于食物/敌人生成
        self.food = self._spawn_food()
        self.enemies = self._spawn_enemies()         # 敌对生物
        self.giant_food_spawn_time = 0               # 当前巨大食物的生成时刻（ms）
        self.last_giant_spawn_time = pygame.time.get_ticks()  # 上次生成时刻
        self.score = 0
        self.game_over = False
        self.frame_count = 0
        self.move_timer = 0.0                         # 移动计时累积器（秒）
        self.speed_boost = False                      # 加速标记（同向按键按下时 1.2x）

    def _spawn_obstacles(self) -> set:
        """在空白区域随机生成墙体（避开蛇身和四周边缘）"""
        occupied = set(self.snake) | self._shield_cells()
        # 排除边缘一格（留出活动空间）
        buffer = 1
        available = [
            (x, y) for x in range(buffer, GRID_W - buffer)
            for y in range(buffer, GRID_H - buffer)
            if (x, y) not in occupied
        ]
        count = min(self.wall_count, len(available))
        return set(random.sample(available, count)) if count > 0 else set()

    def _spawn_enemies(self) -> list:
        """在空白区域生成敌对生物（2×2 方块，避开蛇身、墙体、食物和边缘）"""
        occupied = set(self.snake) | self.obstacles | self._shield_cells()
        if self.food is not None:
            occupied.add(self.food)
        # 2×2 方块需要离边缘至少 1 格
        available = []
        for x in range(1, GRID_W - 2):
            for y in range(1, GRID_H - 2):
                cells = self._block_cells((x, y))
                if not (cells & occupied):
                    available.append((x, y))
        count = min(self.enemy_count, len(available))
        return random.sample(available, count) if count > 0 else []

    def _move_enemies(self) -> None:
        """移动所有敌对生物（2×2 方块整体移动，纯随机，规避障碍）"""
        enemy_cells = self._enemy_cells()
        occupied = set(self.snake) | self.obstacles | enemy_cells | self._shield_cells()
        if self.food is not None:
            occupied.add(self.food)
        occupied |= self._giant_food_cells()

        directions = [UP, DOWN, LEFT, RIGHT]

        for i, (ex, ey) in enumerate(self.enemies):
            # 从占用集中移除当前敌人
            for cell in self._block_cells((ex, ey)):
                occupied.discard(cell)

            valid_moves = []
            for dr, dc in directions:
                nx, ny = ex + dr, ey + dc
                new_cells = self._block_cells((nx, ny))
                # 所有 4 格必须在边界内且不与其他障碍重叠
                if all(0 <= c < GRID_W and 0 <= r < GRID_H for c, r in new_cells):
                    if not (new_cells & occupied):
                        valid_moves.append((nx, ny))

            if valid_moves:
                chosen = random.choice(valid_moves)
                self.enemies[i] = chosen
                for cell in self._block_cells(chosen):
                    occupied.add(cell)
            else:
                for cell in self._block_cells((ex, ey)):
                    occupied.add(cell)

    def _spawn_food(self) -> tuple:
        """在空白格子生成食物（偏向中心区域，避开蛇身、墙体、敌人、巨大食物）"""
        occupied = set(self.snake) | self.obstacles
        occupied |= self._enemy_cells() | self._giant_food_cells() | self._shield_cells()
        available = [
            (x, y) for x in range(GRID_W) for y in range(GRID_H)
            if (x, y) not in occupied
        ]
        if not available:
            return None

        # 加权随机：离边界越近权重越低（边界权重 0.15，中心权重 1.0）
        cx, cy = (GRID_W - 1) / 2, (GRID_H - 1) / 2
        max_dist = min(cx, cy)                       # 到中心的最大曼哈顿分量
        weights = []
        for x, y in available:
            near_border = min(x, y, GRID_W - 1 - x, GRID_H - 1 - y)
            w = 0.15 + 0.85 * (near_border / max_dist) if max_dist > 0 else 1.0
            weights.append(w)

        chosen = random.choices(available, weights=weights, k=1)
        return chosen[0]

    def _spawn_giant_food(self) -> None:
        """在空白区域生成 2×2 巨大食物"""
        enemy_cells = self._enemy_cells()
        occupied = set(self.snake) | self.obstacles | enemy_cells | self._shield_cells()
        if self.food is not None:
            occupied.add(self.food)

        available = []
        for x in range(1, GRID_W - 2):
            for y in range(1, GRID_H - 2):
                cells = self._block_cells((x, y))
                if not (cells & occupied):
                    available.append((x, y))

        if available:
            self.giant_food = random.choice(available)
            self.giant_food_spawn_time = pygame.time.get_ticks()
        else:
            self.giant_food = None

    def _spawn_shield(self) -> None:
        """在空白区域生成光盾道具（单格）"""
        occupied = (set(self.snake) | self.obstacles
                    | self._enemy_cells() | self._giant_food_cells())
        if self.food is not None:
            occupied.add(self.food)
        available = [
            (x, y) for x in range(GRID_W) for y in range(GRID_H)
            if (x, y) not in occupied
        ]
        if available:
            self.shield_powerup = random.choice(available)
            self.shield_powerup_spawn_time = pygame.time.get_ticks()

    def update(self, dt: float) -> None:
        """每帧更新游戏状态（dt = 距上帧的秒数）"""
        if self.game_over:
            return

        now = pygame.time.get_ticks()

        # ----- 巨大食物定时刷新（每 12 秒，时间驱动）-----
        if now - self.last_giant_spawn_time >= GIANT_FOOD_INTERVAL * 1000:
            self.last_giant_spawn_time = now
            if self.giant_food is None:
                self._spawn_giant_food()

        # ----- 巨大食物过期（6 秒后消失）-----
        if self.giant_food is not None:
            if now - self.giant_food_spawn_time >= GIANT_FOOD_DURATION * 1000:
                self.giant_food = None

        # ----- 光盾定时刷新（每 30 秒）-----
        if now - self.last_shield_spawn_time >= SHIELD_SPAWN_INTERVAL * 1000:
            self.last_shield_spawn_time = now
            if self.shield_powerup is None:
                self._spawn_shield()

        # ----- 光盾过期（6 秒后消失）-----
        if self.shield_powerup is not None:
            if now - self.shield_powerup_spawn_time >= SHIELD_DURATION * 1000:
                self.shield_powerup = None

        # ----- 护盾效果过期 -----
        if self.shield_active_until > 0 and now >= self.shield_active_until:
            self.shield_active_until = 0

        # ----- 蛇移动计时器（时间累积驱动）-----
        self.move_timer += dt
        move_interval = self.get_move_interval()
        if self.speed_boost:
            move_interval /= 1.2                       # 同向按键 → 1.2 倍速
        if self.move_timer < move_interval:
            return                                     # 还没到移动时刻，跳过逻辑更新

        # 到达移动时刻，扣减计时（保留余数避免误差累积）
        self.move_timer -= move_interval

        self.frame_count += 1

        # ----- 敌对生物移动（每 ENEMY_MOVE_DELAY 逻辑帧一次）-----
        if self.enemies and self.frame_count % ENEMY_MOVE_DELAY == 0:
            self._move_enemies()

        # 从预输入队列取出有效方向（跳过反向，每逻辑帧最多消费一个）
        while self.direction_queue:
            nd = self.direction_queue[0]
            ndx, ndy = nd
            cx, cy = self.direction
            if (ndx + cx, ndy + cy) == (0, 0):      # 反向 → 丢弃
                self.direction_queue.popleft()
            else:
                self.direction = nd
                self.direction_queue.popleft()
                break                                # 每帧只消费一个

        # 计算新蛇头
        head = self.snake[0]
        new_head = (head[0] + self.direction[0],
                    head[1] + self.direction[1])

        # 撞墙检测
        if not (0 <= new_head[0] < GRID_W and 0 <= new_head[1] < GRID_H):
            self.game_over = True
            return

        # 撞自己检测（排除即将移走的尾部）
        if new_head in self.snake[:-1]:
            self.game_over = True
            return

        # 撞障碍检测
        if new_head in self.obstacles:
            if self.shield_active_until > 0 and now < self.shield_active_until:
                self.obstacles.discard(new_head)      # 护盾：摧毁障碍
                self.score += 1
                self.sound.play_score()               # 得分音效
            else:
                self.game_over = True
                return

        # 移动蛇
        self.snake.insert(0, new_head)

        # ----- 敌对生物碰撞检测 -----
        enemy_cells = self._enemy_cells()
        if new_head in enemy_cells:
            if self.shield_active_until > 0 and now < self.shield_active_until:
                # 护盾：摧毁碰撞的敌人
                for idx, pos in enumerate(self.enemies):
                    if new_head in self._block_cells(pos):
                        self.enemies.pop(idx)
                        self.score += 1
                        self.sound.play_score()       # 得分音效
                        break
            else:
                self._on_enemy_hit(new_head)

        ate = False

        # ----- 巨大食物检测 -----
        if self.giant_food is not None:
            if new_head in self._giant_food_cells():
                self.score += GIANT_FOOD_SCORE
                self.giant_food = None
                ate = True
                self.sound.play_score()              # 得分音效

        # ----- 普通食物检测 -----
        if not ate and new_head == self.food:
            self.score += 1
            self.food = self._spawn_food()
            if self.food is None:                    # 棋盘已满 → 胜利
                self.game_over = True
            ate = True
            self.sound.play_score()                  # 得分音效

        # ----- 光盾道具检测 -----
        if self.shield_powerup is not None and new_head == self.shield_powerup:
            self.shield_powerup = None
            self.shield_active_until = now + SHIELD_EFFECT_TIME * 1000

        if not ate:
            self.snake.pop()                         # 没吃到 → 去尾

    def _on_enemy_hit(self, hit_pos: tuple) -> None:
        """处理与敌对生物的碰撞：扣分、减长、重定位敌人"""
        self.score = max(0, self.score - 1)          # 扣 1 分，不低于 0
        self.sound.play_penalty()                    # 扣分音效
        # 蛇长度减少 1（保持至少 3 格）
        if len(self.snake) > 3:
            self.snake.pop()
        # 找到命中的敌人索引
        enemy_idx = None
        for idx, pos in enumerate(self.enemies):
            if hit_pos in self._block_cells(pos):
                enemy_idx = idx
                break
        if enemy_idx is None:
            return
        # 将敌人重新放置到随机安全位置（2×2 方块）
        occupied = set(self.snake) | self.obstacles | self._enemy_cells() | self._shield_cells()
        if self.food is not None:
            occupied.add(self.food)
        occupied |= self._giant_food_cells()
        available = []
        for x in range(1, GRID_W - 2):
            for y in range(1, GRID_H - 2):
                cells = self._block_cells((x, y))
                if not (cells & occupied):
                    available.append((x, y))
        if available:
            self.enemies[enemy_idx] = random.choice(available)

    def set_direction(self, direction: tuple) -> None:
        """将方向加入预输入队列（最多缓存 3 个）"""
        if len(self.direction_queue) < 3:
            self.direction_queue.append(direction)

    def get_move_interval(self) -> float:
        """返回当前蛇的移动间隔（秒），分数越高越快（受难度影响）"""
        speed = min(self.fps_base + self.score * self.fps_per_score, self.fps_max)
        return 1.0 / speed


# ==================== 界面渲染 ====================
class SnakeRenderer:
    """负责蛇、食物、分数和结束画面的绘制"""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen

    def draw(self, game: SnakeGame) -> None:
        """绘制完整画面"""
        self.screen.fill(BG_COLOR)
        self._draw_grid()
        self._draw_obstacles(game)
        self._draw_giant_food(game)
        self._draw_enemies(game)
        self._draw_food(game)
        self._draw_snake(game)
        self._draw_score(game)

        if game.game_over:
            self._draw_game_over(game)

    # ---------- 网格 ----------
    def _draw_grid(self) -> None:
        """绘制淡色网格线"""
        for x in range(0, SCREEN_W, CELL_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (x, 0), (x, SCREEN_H), 1)
        for y in range(0, SCREEN_H, CELL_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y), (SCREEN_W, y), 1)

    # ---------- 墙体 ----------
    def _draw_obstacles(self, game: SnakeGame) -> None:
        """绘制随机墙体（圆角方块 + 斜线纹理）"""
        for ox, oy in game.obstacles:
            rect = pygame.Rect(
                ox * CELL_SIZE + 1, oy * CELL_SIZE + 1,
                CELL_SIZE - 2, CELL_SIZE - 2,
            )
            pygame.draw.rect(self.screen, WALL_COLOR, rect, border_radius=3)
            # 对角线装饰
            margin = 4
            pygame.draw.line(self.screen, (65, 60, 75),
                             (rect.left + margin, rect.top + margin),
                             (rect.right - margin, rect.bottom - margin), 1)
            pygame.draw.line(self.screen, (65, 60, 75),
                             (rect.right - margin, rect.top + margin),
                             (rect.left + margin, rect.bottom - margin), 1)

    # ---------- 敌对生物 ----------
    def _draw_enemies(self, game: SnakeGame) -> None:
        """绘制敌对生物（2×2 方块，带脉动效果和描边）"""
        for ex, ey in game.enemies:
            px = ex * CELL_SIZE
            py = ey * CELL_SIZE
            size = CELL_SIZE * 2
            # 脉动效果
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.003)) * 0.12 + 0.88
            inflate = int((1 - pulse) * size * 0.3)
            rect = pygame.Rect(
                px + 1 + inflate, py + 1 + inflate,
                size - 2 - inflate * 2, size - 2 - inflate * 2,
            )
            # 深色轮廓
            pygame.draw.rect(self.screen, (80, 40, 10), rect, border_radius=6)
            # 主体填充
            inner = rect.inflate(-4, -4)
            if inner.width > 0 and inner.height > 0:
                pygame.draw.rect(self.screen, ENEMY_COLOR, inner, border_radius=4)
            # 眼睛
            eye_r = max(4, CELL_SIZE // 3)
            cx, cy = rect.centerx, rect.centery
            offset = CELL_SIZE // 2
            pygame.draw.circle(self.screen, (255, 255, 255), (cx - offset, cy), eye_r)
            pygame.draw.circle(self.screen, (255, 255, 255), (cx + offset, cy), eye_r)

    # ---------- 光盾 ----------
    def _draw_shield(self, game: SnakeGame) -> None:
        """绘制光盾道具（呼吸发光圆环）+ 蛇头护盾光环"""
        # --- 光盾道具 ---
        if game.shield_powerup is not None:
            sx, sy = game.shield_powerup
            cx = sx * CELL_SIZE + CELL_SIZE // 2
            cy = sy * CELL_SIZE + CELL_SIZE // 2

            now = pygame.time.get_ticks()
            # 临期闪烁（剩余 < 2 秒）
            remaining = SHIELD_DURATION - (now - game.shield_powerup_spawn_time) / 1000
            if remaining < 2 and int(remaining * 5) % 2 == 0:
                return

            pulse = 0.5 + 0.5 * math.sin(now * 0.005)
            r = CELL_SIZE // 2 - 2

            # 外层光晕
            glow_r = r + 4
            glow_d = glow_r * 4
            glow_surf = pygame.Surface((glow_d, glow_d), pygame.SRCALPHA)
            alpha_outer = int(30 + 25 * pulse)
            pygame.draw.circle(glow_surf, (*SHIELD_GLOW, alpha_outer),
                               (glow_d // 2, glow_d // 2), glow_r + 2)
            self.screen.blit(glow_surf, (cx - glow_d // 2, cy - glow_d // 2))

            # 主体圆
            pygame.draw.circle(self.screen, SHIELD_COLOR, (cx, cy), r)
            # 菱形图标
            inner = r - 4
            if inner > 0:
                pts = [(cx, cy - inner), (cx + inner, cy),
                       (cx, cy + inner), (cx - inner, cy)]
                pygame.draw.polygon(self.screen, (255, 255, 255), pts)

        # --- 蛇头护盾光环 ---
        if game.shield_active_until > 0 and game.shield_active_until > pygame.time.get_ticks():
            hx, hy = game.snake[0]
            hcx = hx * CELL_SIZE + CELL_SIZE // 2
            hcy = hy * CELL_SIZE + CELL_SIZE // 2
            sr = CELL_SIZE // 2 + 4
            sd = sr * 2 + 4
            ssurf = pygame.Surface((sd, sd), pygame.SRCALPHA)

            angle = pygame.time.get_ticks() * 0.003
            segments = 6
            for i in range(segments):
                a = angle + i * (2 * math.pi / segments)
                arc_rect = pygame.Rect(2, 2, sd - 4, sd - 4)
                pygame.draw.arc(ssurf, SHIELD_COLOR + (160,), arc_rect, a, a + 0.8, 3)
            self.screen.blit(ssurf, (hcx - sd // 2, hcy - sd // 2))

    # ---------- 巨大食物 ----------
    def _draw_giant_food(self, game: SnakeGame) -> None:
        """绘制巨大食物（2×2 金色方块，临期闪烁）"""
        if game.giant_food is None:
            return
        gx, gy = game.giant_food

        # 剩余时间 < 2 秒时闪烁
        remaining = GIANT_FOOD_DURATION - (pygame.time.get_ticks() - game.giant_food_spawn_time) / 1000
        if remaining < 2 and int(remaining * 5) % 2 == 0:
            return

        px = gx * CELL_SIZE
        py = gy * CELL_SIZE
        size = CELL_SIZE * 2
        rect = pygame.Rect(px + 1, py + 1, size - 2, size - 2)

        # 外发光
        glow_rect = rect.inflate(8, 8)
        glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        glow_surf.fill((255, 220, 80, 60))
        self.screen.blit(glow_surf, (glow_rect.x, glow_rect.y))

        # 深色描边
        pygame.draw.rect(self.screen, GIANT_FOOD_OUTLINE, rect, border_radius=6)
        # 金色填充
        inner = rect.inflate(-4, -4)
        pygame.draw.rect(self.screen, GIANT_FOOD_COLOR, inner, border_radius=4)
        # 星形标记
        cx, cy = rect.centerx, rect.centery
        r = CELL_SIZE // 2 - 2
        pygame.draw.circle(self.screen, (255, 255, 200), (cx, cy), r, 2)

    # ---------- 蛇 ----------
    def _draw_snake(self, game: SnakeGame) -> None:
        """绘制蛇：头+身体"""
        for i, (sx, sy) in enumerate(game.snake):
            rect = pygame.Rect(
                sx * CELL_SIZE + 1, sy * CELL_SIZE + 1,
                CELL_SIZE - 2, CELL_SIZE - 2,
            )
            color = SNAKE_HEAD if i == 0 else SNAKE_BODY
            pygame.draw.rect(self.screen, color, rect, border_radius=4)

    # ---------- 食物 ----------
    def _draw_food(self, game: SnakeGame) -> None:
        """绘制食物（圆形）"""
        if game.food is None:
            return
        fx, fy = game.food
        cx = fx * CELL_SIZE + CELL_SIZE // 2
        cy = fy * CELL_SIZE + CELL_SIZE // 2
        pygame.draw.circle(self.screen, FOOD_COLOR, (cx, cy), CELL_SIZE // 2 - 2)

    # ---------- 分数 ----------
    def _draw_score(self, game: SnakeGame) -> None:
        """左上角显示分数、速度和护盾倒计时"""
        global _score_font
        if _score_font is None:
            _score_font = _get_font(18, bold=True)
        speed = 1.0 / game.get_move_interval()

        # 护盾倒计时
        shield_str = ""
        if game.shield_active_until > 0:
            remaining = max(0, (game.shield_active_until - pygame.time.get_ticks()) / 1000)
            shield_str = f"    光盾: {remaining:.1f}s"

        text = f"分数: {game.score}    速度: {speed:.1f}{shield_str}"
        surf = _score_font.render(text, True, SCORE_COLOR)
        # 护盾激活时分数栏高亮
        if game.shield_active_until > 0:
            shield_label = _score_font.render(text, True, SHIELD_COLOR)
            self.screen.blit(shield_label, (12, 8))
        else:
            self.screen.blit(surf, (12, 8))

    # ---------- 结束画面 ----------
    def _draw_game_over(self, game: SnakeGame) -> None:
        """半透明遮罩 + 结束文字"""
        global _gameover_font
        if _gameover_font is None:
            _gameover_font = _get_font(36, bold=True)

        # 半透明遮罩
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        # 主文字
        main = _gameover_font.render("游戏结束", True, GAMEOVER_COLOR)
        self.screen.blit(
            main, ((SCREEN_W - main.get_width()) // 2,
                   SCREEN_H // 2 - main.get_height() - 10))

        # 提示
        hint_font = _get_font(16)
        hint = hint_font.render("按 R 重新开始 · 按 ESC 返回菜单", True, (150, 155, 165))
        self.screen.blit(
            hint, ((SCREEN_W - hint.get_width()) // 2,
                   SCREEN_H // 2 + 10))


# ==================== 菜单背景动画 ====================
class MenuBackground:
    """在主菜单背景上绘制随机移动的幽灵蛇和幽灵食物，模拟实机游戏动画"""

    def __init__(self):
        self.snakes = [self._make_snake() for _ in range(5)]
        self.foods = [self._make_food() for _ in range(7)]

    # ---------- 生成 ----------
    @staticmethod
    def _make_snake() -> dict:
        dirs = [UP, DOWN, LEFT, RIGHT]
        d = random.choice(dirs)
        hx = random.randint(6, GRID_W - 7)
        hy = random.randint(4, GRID_H - 5)
        body = [(hx, hy)]
        dx, dy = -d[0], -d[1]
        length = random.randint(3, 6)
        for i in range(1, length):
            body.append((hx + dx * i, hy + dy * i))
        return {
            "body": body,
            "dir": d,
            "speed": random.uniform(2.5, 5.0),
            "acc": random.uniform(0, 0.3),
            "cd_timer": 0.0,
            "cd_interval": random.uniform(1.2, 3.5),
        }

    @staticmethod
    def _make_food() -> dict:
        return {
            "pos": (random.randint(1, GRID_W - 2), random.randint(1, GRID_H - 2)),
            "life": random.uniform(0, 5.0),
            "max_life": random.uniform(3.0, 7.0),
        }

    # ---------- 更新 ----------
    def update(self, dt: float) -> None:
        # ----- 幽灵蛇移动 -----
        for s in self.snakes:
            s["cd_timer"] += dt
            if s["cd_timer"] >= s["cd_interval"]:
                s["cd_timer"] = 0.0
                s["cd_interval"] = random.uniform(1.2, 3.5)
                rev = (-s["dir"][0], -s["dir"][1])
                choices = [UP, DOWN, LEFT, RIGHT]
                # 避免反向与其他蛇碰撞
                s["dir"] = random.choice([d for d in choices if d != rev])

            s["acc"] += dt
            move_int = 1.0 / s["speed"]
            while s["acc"] >= move_int:
                s["acc"] -= move_int
                head = s["body"][0]
                nx = (head[0] + s["dir"][0] + GRID_W) % GRID_W   # 边界回绕
                ny = (head[1] + s["dir"][1] + GRID_H) % GRID_H
                s["body"].insert(0, (nx, ny))
                if len(s["body"]) > 6:
                    s["body"].pop()

        # ----- 幽灵食物闪烁 -----
        for f in self.foods:
            f["life"] += dt
            if f["life"] >= f["max_life"]:
                f["life"] = 0.0
                f["max_life"] = random.uniform(3.0, 7.0)
                f["pos"] = (
                    random.randint(1, GRID_W - 2),
                    random.randint(1, GRID_H - 2),
                )

    # ---------- 绘制 ----------
    def draw(self, screen: pygame.Surface) -> None:
        # 幽灵蛇（半透明暗绿）
        for s in self.snakes:
            for i, (sx, sy) in enumerate(s["body"]):
                alpha = max(15, 70 - i * 15)
                size = CELL_SIZE - (2 if i > 0 else 1)
                margin = 1 + (0 if i > 0 else 0)
                rect = (sx * CELL_SIZE + margin, sy * CELL_SIZE + margin, size, size)
                surf = pygame.Surface((size, size), pygame.SRCALPHA)
                pygame.draw.rect(surf, (55, 100, 65, alpha), (0, 0, size, size), border_radius=3)
                screen.blit(surf, rect)

        # 幽灵食物（半透明红色圆点，呼吸效果）
        for f in self.foods:
            fx, fy = f["pos"]
            t = f["life"] / f["max_life"]                          # 0→1 渐变
            fade = 1.0 - abs(t - 0.5) * 2                           # 0→1→0 呼吸
            alpha = max(15, int(70 * fade))
            cx = fx * CELL_SIZE + CELL_SIZE // 2
            cy = fy * CELL_SIZE + CELL_SIZE // 2
            r = CELL_SIZE // 2 - 3
            d = r * 2 + 2
            surf = pygame.Surface((d, d), pygame.SRCALPHA)
            pygame.draw.circle(surf, (200, 70, 45, alpha), (r + 1, r + 1), r)
            screen.blit(surf, (cx - r - 1, cy - r - 1))


# ==================== 主菜单 ====================
class MainMenu:
    """主菜单界面：开始游戏 / 难度设置 / 历史纪录"""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.state = "main"          # 子状态："main" / "difficulty" / "history"
        self._hover = None           # 当前悬停按钮 ID
        self.history_diff = 1        # 历史纪录当前查看的难度（默认中等）
        self.bg = MenuBackground()   # 背景实机动画
        self._init_fonts()
        self._compute_rects()

    def _init_fonts(self) -> None:
        self.title_font = _get_font(48, bold=True)
        self.subtitle_font = _get_font(20)
        self.btn_font = _get_font(28, bold=True)
        self.small_font = _get_font(18)
        self.hint_font = _get_font(14)

    def _compute_rects(self) -> None:
        """预计算各屏幕按钮矩形"""
        bw, bh = 240, 56                 # 按钮尺寸
        cx = SCREEN_W // 2
        start_y = SCREEN_H // 2 - 30
        gap = 72
        # —— 主菜单按钮 ——
        self.btn_start = pygame.Rect(cx - bw // 2, start_y, bw, bh)
        self.btn_difficulty = pygame.Rect(cx - bw // 2, start_y + gap, bw, bh)
        self.btn_history = pygame.Rect(cx - bw // 2, start_y + gap * 2, bw, bh)

        # —— 难度选择按钮（三个并排） ——
        dbw, dbh = 160, 48
        dgap = 20
        total_w = dbw * 3 + dgap * 2
        dstart_x = cx - total_w // 2
        dy = SCREEN_H // 2 - 10
        self.diff_btns = [
            pygame.Rect(dstart_x + i * (dbw + dgap), dy, dbw, dbh)
            for i in range(3)
        ]

        # —— 返回按钮（共用） ——
        back_w, back_h = 140, 42
        self.btn_back = pygame.Rect(cx - back_w // 2, SCREEN_H - 70, back_w, back_h)

        # —— 历史纪录难度标签页 ——
        tab_w, tab_h = 120, 36
        tab_gap = 12
        tab_total = tab_w * 3 + tab_gap * 2
        tab_start_x = cx - tab_total // 2
        self.history_tabs = [
            pygame.Rect(tab_start_x + i * (tab_w + tab_gap), 172, tab_w, tab_h)
            for i in range(3)
        ]

    # ========== 事件处理 ==========
    def handle_event(self, event: pygame.event.Event) -> str | None:
        """
        处理菜单事件，返回：
        - "game"   → 开始游戏
        - "quit"   → 退出程序
        - None     → 保持菜单
        """
        if event.type == pygame.MOUSEMOTION:
            self._hover = self._hit_test(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._on_click(event.pos)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.state == "main":
                    return "quit"
                self.state = "main"
        return None

    def _hit_test(self, pos: tuple) -> str | None:
        """返回当前鼠标指向的按钮 ID"""
        if self.state == "main":
            if self.btn_start.collidepoint(pos):
                return "start"
            if self.btn_difficulty.collidepoint(pos):
                return "difficulty"
            if self.btn_history.collidepoint(pos):
                return "history"
        elif self.state == "difficulty":
            for i, r in enumerate(self.diff_btns):
                if r.collidepoint(pos):
                    return f"diff_{i}"
            if self.btn_back.collidepoint(pos):
                return "back"
        elif self.state == "history":
            for i, r in enumerate(self.history_tabs):
                if r.collidepoint(pos):
                    return f"hist_tab_{i}"
            if self.btn_back.collidepoint(pos):
                return "back"
        return None

    def _on_click(self, pos: tuple) -> str | None:
        hit = self._hit_test(pos)
        if hit == "start":
            return "game"
        elif hit == "difficulty":
            self.state = "difficulty"
        elif hit == "history":
            self.state = "history"
        elif hit == "back":
            self.state = "main"
        elif hit and hit.startswith("diff_"):
            level = int(hit.split("_")[1])
            set_difficulty(level)
        elif hit and hit.startswith("hist_tab_"):
            self.history_diff = int(hit.split("_")[2])
        return None

    # ========== 绘制 ==========
    def update(self, dt: float) -> None:
        """更新背景动画"""
        self.bg.update(dt)

    def draw(self) -> None:
        self.screen.fill(MENU_BG)
        self.bg.draw(self.screen)       # 先画背景动画
        if self.state == "main":
            self._draw_main()
        elif self.state == "difficulty":
            self._draw_difficulty()
        elif self.state == "history":
            self._draw_history()

    def _draw_title(self) -> None:
        """绘制标题（共用）"""
        title = self.title_font.render("贪 吃 蛇", True, MENU_TITLE)
        self.screen.blit(title, ((SCREEN_W - title.get_width()) // 2, 60))
        sub = self.subtitle_font.render("S N A K E", True, MENU_SUBTITLE)
        self.screen.blit(sub, ((SCREEN_W - sub.get_width()) // 2, 130))

    def _draw_button(self, rect: pygame.Rect, text: str, btn_id: str) -> None:
        """绘制单个按钮（悬停高亮）"""
        hover = btn_id == self._hover
        bg = MENU_BTN_HOVER if hover else MENU_BTN_NORMAL
        fg = MENU_BTN_TEXT_HOVER if hover else MENU_BTN_TEXT
        border = MENU_ACCENT if hover else MENU_BTN_BORDER
        border_w = 2 if hover else 1

        pygame.draw.rect(self.screen, bg, rect, border_radius=10)
        pygame.draw.rect(self.screen, border, rect, border_w, border_radius=10)

        label = self.btn_font.render(text, True, fg)
        self.screen.blit(
            label,
            (rect.centerx - label.get_width() // 2,
             rect.centery - label.get_height() // 2),
        )

    def _draw_main(self) -> None:
        """绘制主菜单"""
        self._draw_title()
        self._draw_button(self.btn_start, "开始游戏", "start")
        self._draw_button(self.btn_difficulty, "难度设置", "difficulty")
        self._draw_button(self.btn_history, "历史纪录", "history")

        # 底部提示
        hint = self.hint_font.render("鼠标点击操作 · ESC 退出", True, MENU_SUBTITLE)
        self.screen.blit(hint, ((SCREEN_W - hint.get_width()) // 2, SCREEN_H - 28))

    def _draw_difficulty(self) -> None:
        """绘制难度选择界面"""
        self._draw_title()

        # 标题
        label = self.subtitle_font.render("选择难度", True, MENU_BTN_TEXT_HOVER)
        self.screen.blit(label, ((SCREEN_W - label.get_width()) // 2,
                                  SCREEN_H // 2 - 60))

        # 三个难度按钮
        for i, name in enumerate(DIFFICULTY_NAMES):
            btn_id = f"diff_{i}"
            # 当前选中的难度用强调色边框
            rect = self.diff_btns[i]
            hover = btn_id == self._hover
            bg = MENU_BTN_HOVER if hover else MENU_BTN_NORMAL
            fg = MENU_BTN_TEXT_HOVER if hover else MENU_BTN_TEXT
            border = MENU_ACCENT if (hover or i == DIFFICULTY) else MENU_BTN_BORDER
            border_w = 2 if (hover or i == DIFFICULTY) else 1

            pygame.draw.rect(self.screen, bg, rect, border_radius=10)
            pygame.draw.rect(self.screen, border, rect, border_w, border_radius=10)

            label = self.btn_font.render(name, True, fg)
            self.screen.blit(
                label,
                (rect.centerx - label.get_width() // 2,
                 rect.centery - label.get_height() // 2),
            )

            # 选中标记
            if i == DIFFICULTY:
                mark = self.hint_font.render("✓ 当前", True, MENU_ACCENT)
                self.screen.blit(
                    mark,
                    (rect.centerx - mark.get_width() // 2,
                     rect.bottom + 6),
                )

        # 悬停时显示难度介绍
        for i in range(3):
            if f"diff_{i}" == self._hover:
                desc = self.small_font.render(DIFFICULTY_DESC[i], True, MENU_ACCENT)
                self.screen.blit(
                    desc,
                    ((SCREEN_W - desc.get_width()) // 2,
                     self.diff_btns[0].bottom + 42),
                )
                break

        self._draw_button(self.btn_back, "返回", "back")

    def _draw_history(self) -> None:
        """绘制历史纪录界面（可按难度切换）"""
        self._draw_title()

        # ----- 难度标签页 -----
        for i, name in enumerate(DIFFICULTY_NAMES):
            tab = self.history_tabs[i]
            active = i == self.history_diff
            hover = f"hist_tab_{i}" == self._hover
            bg = MENU_BTN_HOVER if (active or hover) else MENU_BTN_NORMAL
            fg = MENU_BTN_TEXT_HOVER if active else (MENU_BTN_TEXT_HOVER if hover else MENU_BTN_TEXT)
            border = MENU_ACCENT if active else (MENU_BTN_BORDER if not hover else MENU_ACCENT)
            border_w = 2 if active else 1

            pygame.draw.rect(self.screen, bg, tab, border_radius=8)
            pygame.draw.rect(self.screen, border, tab, border_w, border_radius=8)
            label = self.small_font.render(name, True, fg)
            self.screen.blit(label,
                             (tab.centerx - label.get_width() // 2,
                              tab.centery - label.get_height() // 2))

        # ----- 记录列表 -----
        records = load_history(self.history_diff)
        if not records:
            empty = self.subtitle_font.render("暂无记录", True, MENU_SUBTITLE)
            self.screen.blit(empty, ((SCREEN_W - empty.get_width()) // 2,
                                      SCREEN_H // 2 + 30))
        else:
            start_y = 225
            line_h = 32
            visible = min(len(records), 8)
            for i in range(visible):
                r = records[i]
                rank_text = f"#{i + 1}"
                score_text = f"{r['score']:>4} 分"
                date_text = r.get("date", "")

                y = start_y + i * line_h

                rank_font = _get_font(17, bold=True) if i < 3 else self.small_font
                rank_color = MENU_ACCENT if i < 3 else MENU_RECORD
                rank_surf = rank_font.render(rank_text, True, rank_color)
                self.screen.blit(rank_surf, (SCREEN_W // 2 - 120, y))

                score_surf = self.small_font.render(score_text, True, MENU_RECORD)
                self.screen.blit(score_surf, (SCREEN_W // 2 - 20, y))

                date_surf = self.small_font.render(date_text, True, MENU_SUBTITLE)
                self.screen.blit(date_surf, (SCREEN_W // 2 + 80, y))

        self._draw_button(self.btn_back, "返回", "back")


# ==================== 主程序 ====================
def main():
    """游戏入口 —— 状态机：menu → game → menu → …"""
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("贪吃蛇")

    clock = pygame.time.Clock()
    top_state = "menu"               # 顶层状态："menu" / "game"

    menu = MainMenu(screen)
    game = SnakeGame()
    renderer = SnakeRenderer(screen)

    last_score = 0                   # 记录上次游戏得分（用于历史保存）

    running = True
    while running:
        dt = clock.tick(RENDER_FPS) / 1000.0

        # ==================== 菜单状态 ====================
        if top_state == "menu":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    action = menu.handle_event(event)
                    if action == "game":
                        game.reset()
                        last_score = 0
                        top_state = "game"
                    elif action == "quit":
                        running = False

            menu.update(dt)
            menu.draw()
            pygame.display.flip()
            continue

        # ==================== 游戏状态 ====================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game.game_over:
                        last_score = game.score      # 确保后续 auto-save 不会重复触发
                    top_state = "menu"
                elif event.key == pygame.K_r:
                    if game.game_over:
                        last_score = 0               # 重置以便新一局可以保存
                    game.reset()
                elif not game.game_over:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        game.set_direction(UP)
                        game.speed_boost = (game.direction == UP)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        game.set_direction(DOWN)
                        game.speed_boost = (game.direction == DOWN)
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        game.set_direction(LEFT)
                        game.speed_boost = (game.direction == LEFT)
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        game.set_direction(RIGHT)
                        game.speed_boost = (game.direction == RIGHT)

            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s,
                                 pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                    game.speed_boost = False

        # ----- 保存得分（游戏结束时自动记录，仅一次）-----
        if game.game_over and last_score == 0:
            last_score = game.score
            add_history(game.score, DIFFICULTY)

        # ----- 游戏更新 -----
        game.update(dt)

        # ----- 画面渲染 -----
        renderer.draw(game)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
