"""
五子棋 (Gomoku) - 最终美化版
基于 Pygame · 双人对战 + 人机对战 · 15×15 棋盘

总体架构说明：
  - 标准 15×15 棋盘，左侧为棋盘区（580px），右侧为控制面板（220px）
  - 棋盘使用像素坐标计算落点，鼠标悬停时显示半透明预览棋子
  - 数据结构：棋盘状态用二维列表 grid[row][col] 存储，0=空，1=黑，2=白
  - 坐标约定：网格索引 (row, col)，row 从上到下，col 从左到右
"""

import pygame
import sys
import math

# ==================== 常量配置 ====================

# ---------- 棋盘尺寸 ----------
# 棋盘 × 列）
BOARD_ROWS = 15                                  # 棋盘行数
BOARD_COLS = 15                                  # 棋盘列数

# ---------- 窗口与布局 ----------
# 窗口固定在 800×600，分为左侧棋盘区和右侧控制面板
SCREEN_W, SCREEN_H = 800, 600
PANEL_W = 220                                    # 右侧控制面板宽度
BOARD_AREA_W = SCREEN_W - PANEL_W                # 左侧棋盘区域宽度 (580px)

# ---------- 棋盘参数 ----------
# CELL_SIZE：相邻交叉点的像素间距
# FRAME_WIDTH：木质边框的厚度
# MARGIN_LEFT / MARGIN_TOP：棋盘线起点距窗口边界的偏移量
# 棋盘区域宽度 580px，(14 格 × 34px) = 476px，左右各留 52px 边距
CELL_SIZE = 34                                   # 每格像素间距
FRAME_WIDTH = 22                                 # 木质边框宽度
MARGIN_LEFT = (BOARD_AREA_W - (BOARD_COLS - 1) * CELL_SIZE) // 2  # 棋盘左边界X坐标
MARGIN_TOP = (SCREEN_H - (BOARD_ROWS - 1) * CELL_SIZE) // 2       # 棋盘上边界Y坐标

# 棋子绘制参数
# STONE_RADIUS = 15，略小于 CELL_SIZE/2（17），棋子之间留有间隙更美观
STONE_RADIUS = 15                                # 棋子半径（像素），略小于半格，棋子间有间隙

# 棋盘线总长度（从第一根线到最后一根线的像素跨度）
BOARD_W = (BOARD_COLS - 1) * CELL_SIZE           # 棋盘线宽度 (14 × 34 = 476px)
BOARD_H = (BOARD_ROWS - 1) * CELL_SIZE           # 棋盘线高度 (14 × 34 = 476px)

# 木质边框的四个边界坐标（不含FRAME_WIDTH时是棋盘线范围，加上后构成完整边框）
FRAME_LEFT = MARGIN_LEFT - FRAME_WIDTH           # 边框左边界
FRAME_TOP = MARGIN_TOP - FRAME_WIDTH             # 边框上边界
FRAME_RIGHT = MARGIN_LEFT + BOARD_W + FRAME_WIDTH  # 边框右边界
FRAME_BOTTOM = MARGIN_TOP + BOARD_H + FRAME_WIDTH  # 边框下边界

# ---------- 颜色定义 ----------
# 设计理念：暖色调木质主题，模拟实木棋盘+棋子的质感

# 背景 — 暖米色，柔和不刺眼，衬托木框
BG_COLOR = (240, 236, 224)

# 右侧面板 — 深木色系，与棋盘形成视觉分区
PANEL_BG = (45, 38, 32)                          # 面板底色（深）
PANEL_BORDER = (72, 58, 42)                      # 面板边界装饰线
PANEL_ACCENT = (62, 50, 38)                      # 面板分隔线色

# 木框 — 三层渐变叠加，模拟实木边框的立体感（由外向内：深→中→浅）
# 三层分别偏移 0px、5px、10px，形成嵌套层次
WOOD_FRAME_OUTER = (78, 48, 22)                  # 外框（最深）
WOOD_FRAME_MID = (118, 75, 38)                   # 中框
WOOD_FRAME_INNER = (158, 115, 68)                # 内框（较浅）

# 棋盘面板 — 柔和木色，棋盘线绘制在其上
BOARD_SURFACE = (226, 195, 150)

# 棋盘线及星位
LINE_COLOR = (52, 38, 22)                        # 网格线颜色
STAR_POINT_COLOR = (38, 28, 15)                  # 星位点颜色（比线稍深）

# 面板文字颜色
PANEL_TITLE = (248, 218, 140)                    # 标题（金色）
PANEL_TEXT = (222, 212, 192)                     # 正文（浅米色）
PANEL_SUBTLE = (155, 140, 120)                   # 次要文字（灰色）
HINT_COLOR = (125, 115, 98)                      # 提示文字（更淡）

# 按钮配色（悬停时颜色变亮，反馈鼠标交互）
BTN_NORMAL = (72, 55, 38)                        # 按钮默认背景
BTN_HOVER = (120, 92, 58)                        # 按钮悬停背景（高亮）
BTN_BORDER = (135, 105, 65)                      # 按钮边框
BTN_TEXT = (230, 220, 200)                       # 按钮文字

# ---------- 游戏状态常量 ----------
# 使用整型表示棋子归属，避免字符串比较的性能开销
EMPTY = 0                                        # 空位
BLACK = 1                                        # 黑棋（先手）
WHITE = 2                                        # 白棋（后手，AI 使用）


# ==================== 棋盘逻辑 ====================
class GomokuBoard:
    """管理棋盘数据和胜负判定

    职责：
      - 维护 15×15 棋盘状态（grid 二维列表）
      - 落子合法性检查（越界、重复、对局结束）
      - 五连珠胜负判定（四方向扫描）
      - 悔棋功能（基于 move_history 栈回退）
      - 记录首手和获胜连线，供渲染器高亮显示

    数据字段：
      grid[row][col]   — EMPTY(0) / BLACK(1) / WHITE(2)
      current_player   — 当前该谁落子
      winner           — 获胜方（EMPTY 表示未结束或平局）
      game_over        — 对局是否已结束
      move_count       — 已落子总数（用于判断棋盘满 → 平局）
      last_move        — 上一手坐标，供渲染器画标记
      win_line         — 获胜连珠的格子列表，供渲染器高亮脉冲
      move_history     — 完整落子历史 [(row, col, player), ...]，供悔棋回退
    """

    def __init__(self):
        # 棋盘初始化为全空：15×15 的二维列表，每个元素为 EMPTY(0)
        self.grid = [[EMPTY] * BOARD_COLS for _ in range(BOARD_ROWS)]
        self.current_player = BLACK                 # 黑棋先手
        self.winner = EMPTY                         # 无人获胜
        self.game_over = False                      # 对局进行中
        self.move_count = 0                         # 尚未落子
        self.last_move = None                       # 无上一手
        self.win_line = []                          # 无获胜连线
        self.move_history = []                      # 落子历史为空

    def reset(self):
        """重置棋盘到初始状态

        直接重新赋值而非修改原数据，确保状态一致。
        所有字段回到 __init__ 时的初始值。
        """
        self.grid = [[EMPTY] * BOARD_COLS for _ in range(BOARD_ROWS)]
        self.current_player = BLACK
        self.winner = EMPTY
        self.game_over = False
        self.move_count = 0
        self.last_move = None
        self.win_line.clear()
        self.move_history.clear()

    def place_stone(self, row: int, col: int) -> bool:
        """在 (row, col) 落子

        参数:
            row, col — 棋盘坐标（0~14）

        返回:
            True  — 落子成功
            False — 落子失败（已结束 / 越界 / 该位已有棋子）

        落子后自动执行：
            1. 记录到 grid、move_history、last_move
            2. 四方向扫描检测五连珠
            3. 若五连 → 设置 winner、game_over；否则检查平局
            4. 切换 current_player
        """
        if self.game_over:                           # 对局已结束，禁止落子
            return False
        if not (0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS):  # 越界
            return False
        if self.grid[row][col] != EMPTY:             # 该位已有棋子
            return False

        # 执行落子
        self.grid[row][col] = self.current_player
        self.move_count += 1
        self.last_move = (row, col)
        self.move_history.append((row, col, self.current_player))

        # 胜负检测：以刚落子的位置为中心，扫描四个方向
        self.win_line = self._check_win(row, col)
        if self.win_line:
            self.winner = self.current_player
            self.game_over = True
            return True

        # 平局检测：棋盘已满（15×15=225 格全部占满）且无人五连
        if self.move_count >= BOARD_ROWS * BOARD_COLS:
            self.game_over = True
            return True

        # 切换回合：黑→白，白→黑
        self.current_player = WHITE if self.current_player == BLACK else BLACK
        return True

    def _check_win(self, row: int, col: int):
        """检查在 (row, col) 落子后是否形成五连珠

        算法：
            从落点出发，沿四个方向（水平、垂直、主对角线、副对角线）
            分别向正负两端延伸，统计连续同色棋子数。
            方向向量：
                (0, 1)  → 水平（左右）
                (1, 0)  → 垂直（上下）
                (1, 1)  → 主对角线（左上↔右下）
                (1, -1) → 副对角线（右上↔左下）

        返回:
            形成五连珠时 → 返回连珠格子列表
            未形成       → 返回空列表 []
        """
        player = self.grid[row][col]
        # 四个扫描方向
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for dr, dc in directions:
            line = [(row, col)]                      # 连珠起点为刚落子处

            # 向正方向延伸
            r, c = row + dr, col + dc
            while 0 <= r < BOARD_ROWS and 0 <= c < BOARD_COLS and self.grid[r][c] == player:
                line.append((r, c))
                r += dr
                c += dc

            # 向反方向延伸
            r, c = row - dr, col - dc
            while 0 <= r < BOARD_ROWS and 0 <= c < BOARD_COLS and self.grid[r][c] == player:
                line.append((r, c))
                r -= dr
                c -= dc

            # 连珠数 ≥ 5 即判胜（允许六连、七连等）
            if len(line) >= 5:
                return line
        return []

    def undo(self) -> bool:
        """悔棋：撤销最近一步落子

        通过 move_history 栈实现：
            - 弹出最近一步记录 → 清空该格的棋子
            - 还原 move_count、winner、game_over、current_player
            - last_move 回溯到倒数第二步

        返回:
            True  — 悔棋成功
            False — 无棋可悔（move_history 为空）

        设计要点：
            人机模式下，悔棋一步意味着撤销 AI 的落子 AND 玩家的落子，
            这一步只会撤销最近的一手。外部调用 handle_undo() 处理双步撤销。
        """
        if not self.move_history:
            return False

        # 弹出最近一步，清空该格
        row, col, player = self.move_history.pop()
        self.grid[row][col] = EMPTY
        self.move_count -= 1

        # 重置胜负状态（悔棋后游戏应从结束状态恢复）
        self.win_line.clear()
        self.winner = EMPTY
        self.game_over = False

        # 回合回退到这一步的玩家（即：被撤销的那一手是谁下的，就轮到谁）
        self.current_player = player

        # 更新 last_move 为倒数第二步（没有则置 None）
        if self.move_history:
            self.last_move = self.move_history[-1][:2]  # 取 (row, col)，忽略 player
        else:
            self.last_move = None
        return True


# ==================== AI 对手 ====================
class GomokuAI:
    """评分制五子棋 AI

    核心思路：
        不进行博弈树搜索，而是遍历所有空位，计算每个候选位置的"攻防综合分"。
        得分 = 进攻分 + 防守分 × 1.1，最高分位置即最优落点。
        防守权重略高（1.1），使 AI 倾向于优先封堵对手的威胁。

    评分机制：
        对每个候选位，沿四个方向统计连续同色棋子数和开口数。
        "活N"（两端都空）评分远高于"眠N"（仅一端空），因为活棋更难防守。

    类方法设计：
        所有方法均为 @classmethod，AI 不持有状态，纯函数式计算。
    """

    # ---------- 评分表 ----------
    # 键 = (连续棋子数, 是否有开口)
    #   连续棋子数：当前方向上有多少颗同色连子（含模拟落子后）
    #   是否有开口：至少一端为空且未超出边界
    # 值 = 该棋型对应的分数
    # 分数级差约 10 倍，确保高阶棋型覆盖低阶
    _PATTERNS = {
        (5, True):  100000,       # 活五 → 必胜，最高分
        (5, False): 100000,       # 眠五也足够获胜
        (4, True):  50000,        # 活四 → 下一步必胜，极度危险
        (4, False): 8000,         # 眠四 → 虽不能直接胜，但威胁大
        (3, True):  8000,         # 活三 → 可发展为活四
        (3, False): 800,          # 眠三
        (2, True):  800,          # 活二 → 可发展
        (2, False): 80,           # 眠二
        (1, True):  80,           # 活一 → 基础发展空间
        (1, False): 10,           # 眠一 → 聊胜于无
    }

    # 防守权重倍数：评估对手（黑棋）的威胁时，乘以 1.1 放大
    # 这意味着"封堵对手活三"的优先级略高于"自己造活三"
    DEFENSE_WEIGHT = 1.1

    @classmethod
    def get_move(cls, board: "GomokuBoard") -> tuple:
        """返回 AI（执白棋，WHITE）选择的最佳落子坐标 (row, col)

        算法流程：
            1. 首手落在天元 (7, 7)
            2. 遍历所有空位 → 计算攻防综合分
            3. 得分相同时，优先选择离天元近的位置
            4. 返回得分最高的落点

        时间复杂度：
            O(N × D)，N = 空位数（最多 225），D = 方向数（4）
            实际表现：15×15 棋盘上毫秒级即可完成
        """
        grid = board.grid
        # 收集所有空位（列表推导式遍历全部 225 格）
        empty_cells = [(r, c) for r in range(BOARD_ROWS) for c in range(BOARD_COLS)
                       if grid[r][c] == EMPTY]
        if not empty_cells:                          # 理论上不会走到（已在前端判平局）
            return None
        if board.move_count == 0:                    # 首手落天元
            return (7, 7)

        best_score = -1                              # 当前最高分
        best_moves = []                              # 得分最高的候选落点列表

        for r, c in empty_cells:
            # 进攻分：假设在此落白棋，评估白棋的连子价值
            offense = cls._evaluate(grid, r, c, WHITE)
            # 防守分：假设对手（黑棋）在此落子，评估黑棋的连子价值
            defense = cls._evaluate(grid, r, c, BLACK)
            # 综合分 = 进攻 + 防守 × 1.1
            # 防守权重略高 → AI 优先封堵对手的活四、活三等致命威胁
            score = offense + defense * cls.DEFENSE_WEIGHT

            if score > best_score:
                best_score = score
                best_moves = [(r, c)]                # 发现更高分，替换候选集
            elif score == best_score:
                best_moves.append((r, c))            # 同分，加入候选集

        # 同分时选离天元 (7, 7) 最近的位置（通常更优的占位策略）
        center = (7, 7)
        best_moves.sort(key=lambda p: (p[0] - center[0]) ** 2 + (p[1] - center[1]) ** 2)
        return best_moves[0]

    @classmethod
    def _evaluate(cls, grid: list, row: int, col: int, player: int) -> int:
        """评估在 (row, col) 落 player 子后的综合分数

        模拟落子：假设当前格已落 player 子，然后沿四个方向统计。
        注意：不实际修改 grid，仅做"虚拟评估"。

        算法：
            对每个方向 (dr, dc)：
                1. 从 (row, col) 向正方向计数同色连子
                2. 向反方向计数同色连子
                3. 检查两端是否为空（开口）
                4. 查 _PATTERNS 表累加方向分
            最终返回四方向分数之和。
        """
        total = 0
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]  # 四个方向

        for dr, dc in directions:
            count = 1                                # 至少包含自身（模拟落子后）
            open_ends = 0                            # 开口端数量

            # 正方向延伸：向 dr, dc 方向走，直到遇到不同色的棋子或边界
            r, c = row + dr, col + dc
            while 0 <= r < BOARD_ROWS and 0 <= c < BOARD_COLS and grid[r][c] == player:
                count += 1
                r += dr
                c += dc
            # 停止处的格子：如果为空且未出界 → 有一端开口
            if 0 <= r < BOARD_ROWS and 0 <= c < BOARD_COLS and grid[r][c] == EMPTY:
                open_ends += 1

            # 反方向延伸
            r, c = row - dr, col - dc
            while 0 <= r < BOARD_ROWS and 0 <= c < BOARD_COLS and grid[r][c] == player:
                count += 1
                r -= dr
                c -= dc
            if 0 <= r < BOARD_ROWS and 0 <= c < BOARD_COLS and grid[r][c] == EMPTY:
                open_ends += 1

            # 连子数上限截断为 5（五连以上在评分意义上无区别）
            count = min(count, 5)
            # 从评分表中查分：键为 (连子数, 有开口?)
            # 活棋（open_ends > 0）比同数量的眠棋分高很多
            total += cls._PATTERNS.get((count, open_ends > 0), 0)

        return total


# ==================== 界面渲染 ====================
class GomokuRenderer:
    """负责所有画面绘制——左侧棋盘 + 右侧控制面板

    架构说明：
      本类将渲染逻辑与游戏数据（GomokuBoard）完全解耦。
      每次 draw() 都会从零重建画面，保证数据一致性。

    层级渲染管线（顶层 → 底层，按 draw() 中的调用顺序）：
      1. _draw_board_frame()       — 三层木质外框
      2. _draw_board_surface()     — 棋盘面板底色 + 木纹纹理
      3. _draw_grid_lines()        — 15×15 网格线
      4. _draw_star_points()       — 9 个星位点
      5. _draw_stone_shadows()     — 棋子柔和投影（画在棋子之前）
      6. _draw_stones()            — 棋子本体（含上一手标记）
      7. _draw_win_highlight()     — 获胜连线脉冲高亮
      8. _draw_hover()             — 鼠标悬停预览
      9. _draw_win_banner()        — 胜利弹窗动画
      10. _draw_panel()            — 右侧控制面板
      11. _draw_toast()            — 临时提示消息

    动画系统：
      - _frame_count：全局帧计数器，每帧 update() 加 1
      - _win_start_frame：记录 game_over 变为 True 的帧号
      - 所有动画均基于 elapsed = _frame_count - _win_start_frame 计算

    缓存策略：
      - 棋子 texture（立体渐变 + 高光）→ _stone_cache，只渲染一次
      - 阴影 texture → _shadow_cache，只渲染一次
      - 悬停 preview → _hover_stone_cache / _hover_shadow_cache
      - 木纹纹理 → _wood_grain，构造函数中预渲染，之后直接 blit
    """

    # 面板中显示的小棋子半径（px）
    PANEL_STONE_R = 9
    # Toast 提示持续帧数（90 帧 @ 60 FPS = 约 1.5 秒）
    TOAST_DURATION = 90

    def __init__(self, screen: pygame.Surface):
        """初始化渲染器

        参数:
            screen — pygame 显示 surface（800×600）
        """
        self.screen = screen
        # 按钮区域映射：{"restart": Rect, "undo": Rect, ...}，每帧 draw() 中重建
        self.btn_rects: dict = {}

        # ---------- Toast 提示状态 ----------
        self._toast_text = ""                        # 当前提示文字
        self._toast_timer = 0                        # 剩余帧数（0 = 不显示）

        # ---------- 动画帧计数器 ----------
        self._frame_count = 0                        # 全局帧计数（从 0 起递增）
        self._win_start_frame = -1                   # 胜利触发时的帧号（-1 表示未触发）
        self._prev_game_over = False                 # 上一帧的 game_over 状态（用于检测边沿变化）

        # ---------- 字体（统一使用微软雅黑，含粗体变体）----------
        self.title_font = pygame.font.SysFont("microsoftyahei", 24, bold=True)
        self.turn_font = pygame.font.SysFont("microsoftyahei", 18, bold=True)
        self.status_font = pygame.font.SysFont("microsoftyahei", 15)
        self.button_font = pygame.font.SysFont("microsoftyahei", 15)
        self.hint_font = pygame.font.SysFont("microsoftyahei", 13)
        self.toast_font = pygame.font.SysFont("microsoftyahei", 14)
        self.mode_font = pygame.font.SysFont("microsoftyahei", 14, bold=True)
        self.win_font_large = pygame.font.SysFont("microsoftyahei", 36, bold=True)
        self.win_font_small = pygame.font.SysFont("microsoftyahei", 17)

        # ---------- 预渲染纹理（仅构建一次，后续直接 blit）----------
        self._wood_grain = self._init_wood_grain()

    # ==================== 顶层 draw ====================
    def draw(self, board: GomokuBoard, hover_pos=None, hovered_button: str = None,
             mode: str = "pvp") -> None:
        """绘制完整画面

        参数:
            board          — 棋盘逻辑对象（GomokuBoard 实例）
            hover_pos      — 鼠标悬停的棋盘坐标 (row, col) 或 None
            hovered_button — 鼠标悬停的按钮 ID（如 "restart"）或 None
            mode           — 游戏模式："pvp"（双人对战）或 "pvai"（人机）

        绘图顺序固定，后画的覆盖先画的，遵循从后到前的层级关系。
        """
        self.btn_rects.clear()                       # 重置按钮区域（每帧重新注册）
        self.screen.fill(BG_COLOR)                   # 铺底色

        # ===== 棋盘区 =====
        self._draw_board_frame()                     # 1. 木质边框
        self._draw_board_surface()                   # 2. 棋盘面板（底色+木纹）
        self._draw_grid_lines()                      # 3. 网格线
        self._draw_star_points()                     # 4. 星位点
        self._draw_stone_shadows(board)              # 5. 棋子阴影（先于棋子）
        self._draw_stones(board)                     # 6. 棋子本体
        self._draw_win_highlight(board)              # 7. 获胜连线高亮脉冲
        self._draw_hover(board, hover_pos)           # 8. 悬停预览（半透明）
        self._draw_win_banner(board)                 # 9. 胜利弹窗（动画）

        # ===== 右侧面板 =====
        self._draw_panel(board, hovered_button, mode)  # 10. 控制面板
        self._draw_toast()                            # 11. Toast 提示

    def update(self) -> None:
        """每帧更新计时器与动画状态

        应在主循环中每帧调用一次（draw() 之前）。
        """
        self._frame_count += 1                       # 帧号递增
        if self._toast_timer > 0:
            self._toast_timer -= 1                   # Toast 倒计时
            if self._toast_timer == 0:
                self._toast_text = ""                # 倒计时结束，清除文字

    def _on_game_over_changed(self, game_over: bool) -> None:
        """在外部检测到 game_over 边沿变化时调用

        记录胜利动画的起始帧号，供后续动画计算 elapsed 时间。
        通过比较当前值与此前记录的 _prev_game_over 来检测上升沿。
        """
        if game_over and not self._prev_game_over:   # 刚变为 game_over（上升沿）
            self._win_start_frame = self._frame_count
        self._prev_game_over = game_over             # 更新状态记录

    # ==================== 木板外框 ====================
    def _draw_board_frame(self) -> None:
        """三层叠加木质边框，带圆角

        设计原理：
            由外到内缩进 0px、5px、10px，颜色由深到浅。
            每层先填充底色，再画 1px 深色边框（_darken 降低 35 亮度值），
            模拟实木边框的嵌套层次感和立体效果。
            所有矩形使用 border_radius=8 的圆角，软化视觉冲击。
        """
        offsets = [
            (0,  WOOD_FRAME_OUTER),                   # 最外层（最深），无缩进
            (5,  WOOD_FRAME_MID),                     # 中层，缩进 5px
            (10, WOOD_FRAME_INNER),                   # 最内层（最浅），缩进 10px
        ]
        for inset, color in offsets:
            rect = pygame.Rect(
                FRAME_LEFT + inset, FRAME_TOP + inset,
                FRAME_RIGHT - FRAME_LEFT - inset * 2 + 1,
                FRAME_BOTTOM - FRAME_TOP - inset * 2 + 1,
            )
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            # 每层边缘加 1px 暗线，模拟阴影/深度感
            pygame.draw.rect(self.screen, self._darken(color, 35),
                             rect, 1, border_radius=8)

    # ==================== 预渲染：木纹纹理 ====================
    @staticmethod
    def _init_wood_grain() -> pygame.Surface:
        """预渲染棋盘木纹纹理

        在初始化阶段调用一次，之后每帧直接 blit，避免重复构建。
        使用独立 random 模块 + 固定种子 seed(42) 确保每次启动纹理一致。
        seed() 后必须 reset 以避免污染全局 random 状态。

        实现：水平细线随机透明度叠加，模拟天然木纹。
        """
        import random
        random.seed(42)                              # 固定种子，保证木纹每次启动一致
        padding = 14                                 # 与棋盘面板边距保持同步
        w = FRAME_RIGHT - FRAME_LEFT - padding * 2 + 1
        h = FRAME_BOTTOM - FRAME_TOP - padding * 2 + 1
        surf = pygame.Surface((w, h), pygame.SRCALPHA)  # 带透明通道
        for y_off in range(0, h, 2):                 # 每 2px 一行（噪点密度适中）
            alpha = 3 + random.randint(0, 6)         # 极淡的透明细线
            pygame.draw.line(surf, (130, 90, 45, alpha),
                             (0, y_off), (w, y_off))
        random.seed()                                # 重置随机种子，避免影响其他随机逻辑
        return surf

    # ==================== 棋盘面板 ====================
    def _draw_board_surface(self) -> None:
        """棋盘面板底色 + 柔和木纹纹理

        在木框内层区域填充 BOARD_SURFACE 底色，再叠加预渲染的木纹 texture。
        padding=14 与木框最内层缩进匹配，确保纹理不超出面板范围。
        """
        padding = 14
        rect = pygame.Rect(
            FRAME_LEFT + padding, FRAME_TOP + padding,
            FRAME_RIGHT - FRAME_LEFT - padding * 2 + 1,
            FRAME_BOTTOM - FRAME_TOP - padding * 2 + 1,
        )
        pygame.draw.rect(self.screen, BOARD_SURFACE, rect, border_radius=3)
        if self._wood_grain is not None:             # 叠加预渲染木纹
            self.screen.blit(self._wood_grain, (FRAME_LEFT + padding, FRAME_TOP + padding))

    # ==================== 网格线 ====================
    def _draw_grid_lines(self) -> None:
        """绘制 15×15 网格线

        从 MARGIN_LEFT / MARGIN_TOP 开始，每格 CELL_SIZE(34px) 一根线。
        横线：y = MARGIN_TOP + i * CELL_SIZE, i = 0..14
        竖线：x = MARGIN_LEFT + i * CELL_SIZE, i = 0..14
        线条宽度统一为 1px，颜色为 LINE_COLOR。
        """
        for i in range(BOARD_ROWS):
            y = MARGIN_TOP + i * CELL_SIZE
            pygame.draw.line(self.screen, LINE_COLOR,
                             (MARGIN_LEFT, y), (MARGIN_LEFT + BOARD_W, y), 1)
            x = MARGIN_LEFT + i * CELL_SIZE
            pygame.draw.line(self.screen, LINE_COLOR,
                             (x, MARGIN_TOP), (x, MARGIN_TOP + BOARD_H), 1)

    # ==================== 星位点 ====================
    def _draw_star_points(self) -> None:
        """绘制标准星位点

        9 个星位：天元 (7,7) + 四个象限各 2 个。
        星位坐标为 (row, col)，需要转换为像素坐标后画圆。
        半径 3px，使用比棋盘线稍深的颜色以突出。

        星位分布：
            (3,3) (3,7) (3,11)
            (7,3) (7,7) (7,11)
            (11,3)(11,7)(11,11)
        """
        star_positions = [
            (3, 3), (3, 7), (3, 11),
            (7, 3), (7, 7), (7, 11),
            (11, 3), (11, 7), (11, 11),
        ]
        for r, c in star_positions:
            cx = MARGIN_LEFT + c * CELL_SIZE          # 星位 X 像素坐标
            cy = MARGIN_TOP + r * CELL_SIZE           # 星位 Y 像素坐标
            pygame.draw.circle(self.screen, STAR_POINT_COLOR, (cx, cy), 3)

    # ==================== 棋子渲染（带阴影）====================
    # 类级缓存：避免每帧重新构建棋子/阴影 texture
    # key = (player, radius) 或 radius，值 = pygame.Surface (带 alpha)
    _stone_cache: dict = {}                            # 棋子纹理缓存
    _shadow_cache: dict = {}                           # 阴影纹理缓存
    _hover_stone_cache: dict = {}                      # 半透明悬停棋子缓存
    _hover_shadow_cache: dict = {}                     # 半透明悬停阴影缓存

    @classmethod
    def _get_shadow_surface(cls, radius: int) -> pygame.Surface:
        """预渲染棋子投影

        原理：
            在透明 Surface 上逐层画渐变黑色圆，从大半径到小半径，
            alpha 按二次方衰减（1 - t²），中心最暗、边缘最柔和。
            圆心向右下偏移 2px，模拟右上光源。

        参数:
            radius — 棋子半径（15px for 棋盘棋子，9px for 面板棋子）

        返回:
            带 alpha 通道的阴影 Surface，尺寸略大于棋子。
        """
        key = radius
        if key in cls._shadow_cache:                   # 缓存命中，直接返回
            return cls._shadow_cache[key]

        size = radius * 2 + 8                          # 比棋子大 8px，给阴影留扩散空间
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        shadow_radius = radius + 1                     # 阴影半径略大于棋子
        cx, cy = size // 2 + 2, size // 2 + 2          # 圆心向右下偏移 2px

        for r in range(shadow_radius, 0, -1):
            t = r / shadow_radius
            alpha = int(80 * (1 - t * t))              # 二次方衰减：中心 α≈80，边缘 α→0
            pygame.draw.circle(surf, (0, 0, 0, max(0, alpha)), (cx, cy), r)

        cls._shadow_cache[key] = surf
        return surf

    @classmethod
    def _get_stone_surface(cls, player: int, radius: int) -> pygame.Surface:
        """预渲染一枚立体棋子

        通过径向渐变 + 高光实现立体感：

        黑棋：
          - 从内到外：深灰→黑（base + gradient）
          - 左上角白色高光（120→0 的 alpha 渐变）

        白棋：
          - 从内到外：白→浅灰
          - 左上角白色高光（220→0 的 alpha 渐变）
          - 右下角微弱高光（模拟环境光反射）

        参数:
            player — BLACK(1) 或 WHITE(2)
            radius — 棋子半径

        返回:
            带 alpha 通道的立体棋子 Surface。
        """
        key = (player, radius)
        if key in cls._stone_cache:                    # 缓存命中
            return cls._stone_cache[key]

        size = radius * 2 + 6                          # 比棋子直径大 6px 留边距
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2                            # Surface 中心点

        if player == BLACK:
            # 黑棋：从外到内逐层叠加，模拟"左上亮→右下暗"的光照
            for r in range(radius, 0, -1):
                t = r / radius                         # 距中心的归一化距离（1=最外, 0=中心）
                base = 20 + int(55 * t * t)            # 平方关系使中心快速变亮
                gradient = int(60 * (1 - t))           # 梯度成分：外暗内亮
                v = base + gradient
                color = (v, v, v, 255)
                pygame.draw.circle(surf, color, (cx, cy), r)

            # 左上角高光：模拟镜面反射
            hl_dx, hl_dy = -radius // 4, -radius // 3  # 高光位置（左上偏移）
            hl_r = max(2, radius // 3)                 # 高光斑点半径
            for r in range(hl_r, 0, -1):
                alpha = int(120 * r / hl_r)            # 从中心 120 → 边缘 0
                pygame.draw.circle(surf, (200, 200, 200, alpha),
                                   (cx + hl_dx, cy + hl_dy), r)
        else:
            # 白棋：从外到内渐变（外灰内白）
            for r in range(radius, 0, -1):
                t = r / radius
                v = 195 + int(55 * t * t)              # 外圈稍暗，内圈纯白
                color = (v, v, v, 255)
                pygame.draw.circle(surf, color, (cx, cy), r)

            # 左上角高光（比黑棋更亮，alpha 220）
            hl_dx, hl_dy = -radius // 4, -radius // 3
            hl_r = max(2, radius // 3)
            for r in range(hl_r, 0, -1):
                alpha = int(220 * r / hl_r)
                pygame.draw.circle(surf, (255, 255, 255, alpha),
                                   (cx + hl_dx, cy + hl_dy), r)

            # 右下角微弱高光（环境光 / 漫反射）
            amb_r = max(1, radius // 5)
            pygame.draw.circle(surf, (248, 248, 248, 50),
                               (cx + radius // 3, cy + radius // 4), amb_r)

        cls._stone_cache[key] = surf
        return surf

    def _draw_stone_shadows(self, board: GomokuBoard) -> None:
        """在所有棋子位置绘制柔和投影

        遍历棋盘所有非空格子，为每颗棋子绘制投影。
        必须在大棋子本体之前调用，确保阴影在棋子下方。
        投影圆心向右下偏移 1px，模拟左上光源。
        """
        shadow_surf = self._get_shadow_surface(STONE_RADIUS)  # 获取缓存阴影
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                if board.grid[r][c] == EMPTY:
                    continue
                cx = MARGIN_LEFT + c * CELL_SIZE
                cy = MARGIN_TOP + r * CELL_SIZE
                # Surface 贴入位置：使阴影中心在交叉点右下 1px
                bx = cx - shadow_surf.get_width() // 2
                by = cy - shadow_surf.get_height() // 2 + 1
                self.screen.blit(shadow_surf, (bx, by))

    def _draw_stones(self, board: GomokuBoard) -> None:
        """遍历棋盘，绘制所有棋子

        同时为上一手落子位置绘制一个小红点标记（对局未结束时显示）。
        """
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                stone = board.grid[r][c]
                if stone == EMPTY:
                    continue
                cx = MARGIN_LEFT + c * CELL_SIZE
                cy = MARGIN_TOP + r * CELL_SIZE
                self._draw_one_stone(cx, cy, stone)    # 画棋子

                # 上一手标记：在最后一手的棋子上画一个醒目小圆点
                if board.last_move == (r, c) and not board.game_over:
                    # 黑棋用亮红色，白棋用深红色（确保在白棋上可见）
                    marker_color = (255, 90, 75) if stone == BLACK else (210, 50, 40)
                    pygame.draw.circle(self.screen, marker_color, (cx, cy), 3)

    def _draw_one_stone(self, cx: int, cy: int, player: int) -> None:
        """在像素坐标 (cx, cy) 绘制一枚立体棋子

        从缓存获取棋子 Surface，计算 blit 位置使棋子中心对准交叉点。
        """
        surf = self._get_stone_surface(player, STONE_RADIUS)
        blit_x = cx - surf.get_width() // 2
        blit_y = cy - surf.get_height() // 2
        self.screen.blit(surf, (blit_x, blit_y))

    # ==================== 悬停预览 ====================
    @classmethod
    def _get_hover_shadow(cls, radius: int) -> pygame.Surface:
        """预渲染：半透明悬停阴影（缓存）

        基于完整阴影拷贝后降低 alpha 至 50，使悬停预览的阴影比实际棋子更淡。
        """
        key = radius
        if key in cls._hover_shadow_cache:
            return cls._hover_shadow_cache[key]
        src = cls._get_shadow_surface(radius)          # 获取完整阴影
        dest = pygame.Surface(src.get_size(), pygame.SRCALPHA)
        dest.blit(src, (0, 0))
        dest.set_alpha(50)                             # 半透明（20% 不透明度）
        cls._hover_shadow_cache[key] = dest
        return dest

    @classmethod
    def _get_hover_stone(cls, player: int, radius: int) -> pygame.Surface:
        """预渲染：半透明悬停棋子（缓存）

        基于完整棋子拷贝后降低 alpha 至 100，提示"即将落子位置"。
        """
        key = (player, radius)
        if key in cls._hover_stone_cache:
            return cls._hover_stone_cache[key]
        src = cls._get_stone_surface(player, radius)   # 获取完整棋子
        dest = pygame.Surface(src.get_size(), pygame.SRCALPHA)
        dest.blit(src, (0, 0))
        dest.set_alpha(100)                            # 半透明（约 40% 不透明度）
        cls._hover_stone_cache[key] = dest
        return dest

    def _draw_hover(self, board: GomokuBoard, hover_pos) -> None:
        """鼠标悬停时显示半透明预览棋子

        条件：
          - 鼠标在有效网格位置内
          - 对局未结束
          - 该位置为空

        先用 semi-transparent 阴影，再叠半透明棋子，颜色对应当前玩家。
        这样玩家在落子前就能看到落点效果。
        """
        if hover_pos is None or board.game_over:      # 无效位置或对局已结束
            return
        r, c = hover_pos
        if board.grid[r][c] != EMPTY:                  # 该位已有棋子
            return

        cx = MARGIN_LEFT + c * CELL_SIZE
        cy = MARGIN_TOP + r * CELL_SIZE

        # 先画半透明阴影（alpha=50）
        shadow = self._get_hover_shadow(STONE_RADIUS)
        self.screen.blit(shadow,
                         (cx - shadow.get_width() // 2,
                          cy - shadow.get_height() // 2 + 1))

        # 再画半透明棋子（alpha=100，颜色=当前玩家）
        stone = self._get_hover_stone(board.current_player, STONE_RADIUS)
        self.screen.blit(stone,
                         (cx - stone.get_width() // 2,
                          cy - stone.get_height() // 2))

    # ==================== 获胜连线高亮（脉冲动画）====================
    def _draw_win_highlight(self, board: GomokuBoard) -> None:
        """用脉冲金色圆环高亮获胜连珠

        围绕获胜连线上的每一颗棋子绘制：
          - 外圈：金色光环，半径和颜色随正弦波脉动
          - 内圈：红色细环

        动画参数：
          pulse = 0.6 + 0.4 * sin(elapsed * 0.06)
          脉冲值在 [0.2, 1.0] 之间振荡，控制光环的大小和亮度。

        优化：直接使用 pygame.draw.circle 的 line 模式（width=1），
              避免每帧创建临时 Surface，提升性能。
        """
        if not board.win_line:                         # 无获胜连线
            return

        # 从胜利触发帧开始计算经过的帧数
        elapsed = self._frame_count - self._win_start_frame \
                  if self._win_start_frame >= 0 else 0
        # 正弦波脉冲系数：范围 [0.2, 1.0]
        pulse = 0.6 + 0.4 * math.sin(elapsed * 0.06)

        outer_r = STONE_RADIUS + 4 + int(2 * pulse)    # 外圈半径（脉冲变化）
        inner_r = STONE_RADIUS + 1                     # 内圈半径（固定）

        for r, c in board.win_line:
            cx = MARGIN_LEFT + c * CELL_SIZE
            cy = MARGIN_TOP + r * CELL_SIZE

            # 外圈：金色光环（脉冲变化粗细和透明度）
            alpha = int(180 + 75 * pulse)
            color = (255, int(180 + 40 * pulse), int(40 + 20 * pulse))
            width = max(1, int(3 * pulse))
            for w in range(width):                     # 多层同心圆模拟粗线
                pygame.draw.circle(self.screen, color + (alpha,),
                                   (cx, cy), outer_r - w, 1)

            # 内圈：红色细环（随 pulse 微调颜色）
            pygame.draw.circle(self.screen, (220, int(50 + 30 * pulse), 50),
                               (cx, cy), inner_r, 1)

    # ==================== 胜利弹窗（缩放 + 呼吸动画）====================
    def _draw_win_banner(self, board: GomokuBoard) -> None:
        """在棋盘区中央绘制带缩放/呼吸动画的胜利弹窗

        动画三阶段：
          阶段 1（0~30帧）：弹出 — scale 从 0.3 弹性缓出到 1.08
            公式：scale = 0.3 + 0.78 * (1 - (1-t)³)，三次方缓出产生弹性感
          阶段 2（30~45帧）：回弹 — scale 从 1.08 回落到 1.0
            公式：scale = 1.08 - 0.08 * t²，抛物线平滑回落
          阶段 3（45帧+）：呼吸 — scale 在 1.0 附近微微振荡
            公式：scale = 1.0 + 0.012 * sin((elapsed-45) * 0.04)

        实现：先绘制到独立 Surface（card），再 smoothscale 缩放后 blit，
              避免像素化（仅 scale 偏离 1.0 较多时才执行 smoothscale）。
        """
        if not board.game_over:
            return

        elapsed = self._frame_count - self._win_start_frame \
                  if self._win_start_frame >= 0 else 0

        # 动画阶段判断
        if elapsed < 30:
            t = elapsed / 30
            # 弹性缓出（ease-out cubic）：末尾加速但不过冲太猛
            scale = 0.3 + (1.08 - 0.3) * (1 - (1 - t) ** 3)
        elif elapsed < 45:
            t = (elapsed - 30) / 15
            scale = 1.08 + (1.0 - 1.08) * (t ** 2)    # 抛物线回弹
        else:
            # 呼吸效果：周期约 157 帧（2.6 秒）
            scale = 1.0 + 0.012 * math.sin((elapsed - 45) * 0.04)

        # 弹窗尺寸（基准 320×110）
        card_w, card_h = 320, 110
        scaled_w = int(card_w * scale)
        scaled_h = int(card_h * scale)
        # 居中放置（仅在棋盘区域 BOARD_AREA_W 内）
        card_x = (BOARD_AREA_W - scaled_w) // 2
        card_y = (SCREEN_H - scaled_h) // 2

        # 创建弹窗 Surface（带 alpha，基准尺寸）
        card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)

        # 半透明深色背景
        pygame.draw.rect(card, (22, 15, 8, 235),
                         (0, 0, card_w, card_h), border_radius=14)

        # 金色边框（透明度随呼吸微调）
        border_alpha = int(160 + 40 * math.sin(elapsed * 0.05))
        pygame.draw.rect(card, (255, 195, 50, border_alpha),
                         (0, 0, card_w, card_h), 3, border_radius=14)

        # 内层装饰线
        margin = 10
        pygame.draw.rect(card, (255, 195, 50, 50),
                         (margin, margin, card_w - margin * 2, card_h - margin * 2),
                         1, border_radius=8)

        # 胜利文字（根据 winner 选择文字和颜色）
        if board.winner == BLACK:
            main_text = "黑棋胜利！"
            main_color = (255, 215, 60)               # 金色
        elif board.winner == WHITE:
            main_text = "白棋胜利！"
            main_color = (255, 215, 60)
        else:
            main_text = "平局"
            main_color = (210, 210, 210)              # 灰色

        # 大号主文字
        surf_main = self.win_font_large.render(main_text, True, main_color)
        text_x = (card_w - surf_main.get_width()) // 2
        text_y = (card_h - surf_main.get_height()) // 2 - 8
        card.blit(surf_main, (text_x, text_y))

        # 小字提示
        hint = self.win_font_small.render("按 R 重新开始", True, (175, 155, 125))
        card.blit(hint, ((card_w - hint.get_width()) // 2,
                         text_y + surf_main.get_height() + 4))

        # 缩放到实际尺寸（仅偏离超过 0.5% 时才执行开销较大的 smoothscale）
        if abs(scale - 1.0) > 0.005:
            card = pygame.transform.smoothscale(card, (scaled_w, scaled_h))
        self.screen.blit(card, (card_x, card_y))

    # ================================================================
    #  右侧控制面板
    # ================================================================
    def _draw_panel(self, board: GomokuBoard, hovered_button: str = None,
                    mode: str = "pvp") -> None:
        """绘制右侧控制面板

        布局从上到下：
          ① 标题 "优雅五子棋" + 装饰点
          ② 对战模式指示（双人对战/人机对战）+ 切换链接
          ③ 当前回合/游戏结果
          ④ 已下步数
          ⑤ 按钮："再来一局"、"悔棋"、"退出游戏"
          ⑥ 快捷键提示
        """
        px = BOARD_AREA_W                            # 面板左边界 X（580）
        pw = PANEL_W                                 # 面板宽度（220）

        # 面板底色 + 边界装饰线
        pygame.draw.rect(self.screen, PANEL_BG, (px, 0, pw, SCREEN_H))
        pygame.draw.line(self.screen, PANEL_BORDER, (px, 0), (px, SCREEN_H), 2)   # 左边框
        pygame.draw.line(self.screen, PANEL_BORDER, (px, 0), (px + pw, 0), 2)     # 顶部边框

        center_x = px + pw // 2                      # 面板水平中心线
        y = 30                                       # 垂直起始位置

        # ===== ① 标题 =====
        title = self.title_font.render("优雅五子棋", True, PANEL_TITLE)
        self.screen.blit(title, (center_x - title.get_width() // 2, y))
        y += title.get_height() + 6

        # 标题下方装饰点（中心 3 个亮色 + 两端 2 个暗色）
        dot_x = center_x
        for i in range(-2, 3):
            dot_color = PANEL_TITLE if abs(i) < 2 else PANEL_ACCENT
            pygame.draw.circle(self.screen, dot_color,
                               (dot_x + i * 6, y + 4), 2)
        y += 14

        y = self._draw_separator(px, y)
        y += 10

        # ===== ② 对战模式 =====
        y = self._draw_section_label(px, y, "对战模式")
        y = self._draw_mode_indicator(px, y, mode)
        y += 6

        y = self._draw_separator(px, y)
        y += 10

        # ===== ③ 当前回合 / 游戏结果 =====
        if board.game_over:
            y = self._draw_section_label(px, y, "游戏结果")
            winner_text = "黑棋获胜" if board.winner == BLACK else (
                "白棋获胜" if board.winner == WHITE else "平局")
            color = (255, 215, 80) if board.winner != EMPTY else (200, 200, 200)
            surf = self.turn_font.render(winner_text, True, color)
            self.screen.blit(surf, (center_x - surf.get_width() // 2, y))
            y += surf.get_height() + 6
        else:
            y = self._draw_section_label(px, y, "当前回合")
            y = self._draw_turn_indicator(px, y, board.current_player, mode)
            y += 4

        # ===== ④ 步数 =====
        steps = f"已下 {board.move_count} 手"
        step_surf = self.status_font.render(steps, True, PANEL_SUBTLE)
        self.screen.blit(step_surf, (center_x - step_surf.get_width() // 2, y))
        y += 32

        y = self._draw_separator(px, y)
        y += 14

        # ===== ⑤ 按钮 =====
        self._draw_button(px, y, "再来一局", "restart", hovered_button)
        y += 48
        self._draw_button(px, y, "悔     棋", "undo", hovered_button)
        y += 48
        self._draw_button(px, y, "退出游戏", "exit", hovered_button)

        # ===== ⑥ 底部快捷键提示 =====
        y = SCREEN_H - 42                             # 固定在底部
        self._draw_section_label(px, y, "快捷键")
        hints = ["左键 落子", "Ctrl+Z 悔棋", "R 重来"]
        hint_x = center_x
        for i, h in enumerate(hints):
            hs = self.hint_font.render(h, True, HINT_COLOR)
            if i == 0:
                self.screen.blit(hs, (hint_x - hs.get_width() // 2, y + 16))
            else:
                self.screen.blit(hs, (hint_x - hs.get_width() // 2, y + 16 + i * 15))

    # ---------- 按钮 ----------
    def _draw_button(self, px: int, y: int, text: str, btn_id: str,
                     hovered: str = None) -> None:
        """绘制圆角按钮

        三部分组成：
          1. 主体矩形（hover 时颜色变亮）
          2. 1px 边框
          3. 顶部高光条（模拟立体凸起效果）

        同时将按钮区域注册到 btn_rects，供外部的 get_button_at() 命中检测。
        """
        btn_w = PANEL_W - 36                          # 按钮宽度（左右各留 18px 边距）
        btn_h = 38                                    # 按钮高度
        bx = px + 18                                  # 按钮左边界
        rect = pygame.Rect(bx, y, btn_w, btn_h)

        is_hover = (hovered == btn_id)                 # 当前按钮是否被鼠标悬停
        bg_color = BTN_HOVER if is_hover else BTN_NORMAL

        # 1. 按钮主体
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=10)

        # 2. 边框（悬停时颜色加亮）
        border_c = BTN_HOVER if is_hover else BTN_BORDER
        pygame.draw.rect(self.screen, border_c, rect, 1, border_radius=10)

        # 3. 顶部高光条：只占按钮上半部分，颜色比底色亮 35
        hl_h = btn_h // 2 - 2
        hl_rect = pygame.Rect(bx + 3, y + 1, btn_w - 6, hl_h)
        hl_color = tuple(min(c + 35, 255) for c in bg_color)
        pygame.draw.rect(self.screen, hl_color, hl_rect, border_radius=6)

        # 文字居中
        text_color = (255, 238, 210) if is_hover else BTN_TEXT   # 悬停时文字也变亮
        surf = self.button_font.render(text, True, text_color)
        tw = surf.get_width()
        self.screen.blit(surf, (bx + (btn_w - tw) // 2,
                                y + (btn_h - surf.get_height()) // 2))
        self.btn_rects[btn_id] = rect                  # 注册按钮区域

    def get_button_at(self, mx: int, my: int):
        """检测鼠标坐标 (mx, my) 落在哪个按钮区域内

        返回:
            按钮 ID 字符串（"restart"/"undo"/"exit"）或 None（未命中）
        """
        for btn_id, rect in self.btn_rects.items():
            if rect.collidepoint(mx, my):
                return btn_id
        return None

    # ---------- 面板子组件 ----------
    def _draw_section_label(self, px: int, y: int, text: str) -> int:
        """绘制面板分区标签

        使用 hint_font + PANEL_SUBTLE 颜色，左对齐于 px+20。
        返回更新后的 y 坐标（标签底部 + 6px 间距）。
        """
        surf = self.hint_font.render(text, True, PANEL_SUBTLE)
        self.screen.blit(surf, (px + 20, y))
        return y + surf.get_height() + 6

    def _draw_mode_indicator(self, px: int, y: int, mode: str) -> int:
        """绘制对战模式标识 + 切换链接

        双人对战模式：黑棋子 + 白棋子图标
        人机对战模式：黑棋子 + AI 标签（圆角矩形内的 "AI" 文字）

        底部有"切换模式 →"链接，点击切换。
        """
        center_x = px + PANEL_W // 2
        icon_gap = 18                                  # 两个图标之间的间距

        stone_y = y + self.PANEL_STONE_R + 2           # 棋子中心 Y 坐标
        if mode == "pvp":
            # 双人对战：黑棋子 + 白棋子
            self._draw_panel_stone(center_x - icon_gap, stone_y, BLACK)
            self._draw_panel_stone(center_x + icon_gap, stone_y, WHITE)
        else:
            # 人机对战：黑棋子 + AI 标识
            self._draw_panel_stone(center_x - icon_gap, stone_y, BLACK)
            ai_bg_r = 10                               # AI 标识背景圆角矩形半径
            ai_rect = pygame.Rect(
                center_x + icon_gap - ai_bg_r, stone_y - ai_bg_r,
                ai_bg_r * 2, ai_bg_r * 2)
            pygame.draw.rect(self.screen, (60, 50, 38), ai_rect, border_radius=3)
            pygame.draw.rect(self.screen, PANEL_BORDER, ai_rect, 1, border_radius=3)
            ai_label = self.hint_font.render("AI", True, PANEL_TITLE)
            self.screen.blit(ai_label,
                             (center_x + icon_gap - ai_label.get_width() // 2,
                              stone_y - ai_label.get_height() // 2))

        # 模式文字
        mode_text_str = "双人对战" if mode == "pvp" else "人机对战"
        mode_surf = self.mode_font.render(mode_text_str, True, PANEL_TEXT)
        text_y = stone_y + self.PANEL_STONE_R + 7
        self.screen.blit(mode_surf, (center_x - mode_surf.get_width() // 2, text_y))

        # 切换链接文字（可点击区域注册到 btn_rects["switch_mode"]）
        sw_text = "切换模式 →"
        sw_surf = self.hint_font.render(sw_text, True, (175, 155, 120))
        sw_x = center_x - sw_surf.get_width() // 2
        sw_y = text_y + mode_surf.get_height() + 3
        self.screen.blit(sw_surf, (sw_x, sw_y))
        # 可点击热区略大于文字
        sw_rect = pygame.Rect(sw_x - 5, sw_y - 3,
                              sw_surf.get_width() + 10, sw_surf.get_height() + 6)
        self.btn_rects["switch_mode"] = sw_rect

        return sw_y + sw_surf.get_height()

    def _draw_turn_indicator(self, px: int, y: int, player: int,
                             mode: str = "pvp") -> int:
        """绘制当前回合指示器

        包含：
          - 一枚棋子图标（当前回合玩家的颜色）
          - 脉冲光圈（正弦波调制 alpha，增强动感）
          - 回合文字标签（含玩家名称 / AI 提示）
        """
        center_x = px + PANEL_W // 2
        stone_y = y + self.PANEL_STONE_R + 2

        # 脉冲光圈参数：正弦波在 [0, 1] 范围内振荡
        elapsed = self._frame_count
        pulse = 0.5 + 0.5 * math.sin(elapsed * 0.05)

        # 棋子图标
        self._draw_panel_stone(center_x, stone_y, player)

        # 光标环：根据 pulse 调整粗细和透明度
        ring_r = self.PANEL_STONE_R + 4
        ring_alpha = int(60 + 40 * pulse)
        ring_color = (255, 200, 60) if player == BLACK else (220, 210, 190)
        # Pygame 的 circle 不支持直接设置 alpha，这里用 color + alpha 元组
        pygame.draw.circle(self.screen, ring_color + (ring_alpha,),
                           (center_x, stone_y), ring_r, 2)

        # 文字标签
        if mode == "pvai":
            label = "你的回合" if player == BLACK else "AI 思考中..."
            label_color = (255, 215, 80) if player == BLACK else (155, 185, 215)
        else:
            label = "黑棋回合" if player == BLACK else "白棋回合"
            label_color = (220, 215, 200) if player == BLACK else (235, 230, 215)

        surf = self.turn_font.render(label, True, label_color)
        text_y = stone_y + self.PANEL_STONE_R + 10
        self.screen.blit(surf, (center_x - surf.get_width() // 2, text_y))
        return text_y + surf.get_height()

    def _draw_panel_stone(self, cx: int, cy: int, player: int) -> None:
        """在面板中绘制一枚小尺寸立体棋子

        复用 _get_stone_surface 方法，传入 PANEL_STONE_R(9) 作为半径，
        与棋盘棋子（半径 15）使用相同的渐变渲染逻辑。
        """
        surf = self._get_stone_surface(player, self.PANEL_STONE_R)
        self.screen.blit(surf, (cx - surf.get_width() // 2,
                                cy - surf.get_height() // 2))

    # ---------- 辅助方法 ----------
    @staticmethod
    def _darken(color: tuple, amount: int) -> tuple:
        """将颜色 RGB 分量各减去 amount（不低于 0）

        用于生成比原色偏暗的同色调颜色，模拟阴影/深度效果。
        注意：只修改 RGB 前三个通道，忽略 alpha（如果有）。
        """
        return tuple(max(0, c - amount) for c in color[:3])

    def _draw_separator(self, panel_x: int, y: int) -> int:
        """绘制面板中的横向分隔线

        在面板左右各留 20px 边距，线宽 PANEL_W - 40。
        返回分隔线下方 4px 处的 y 坐标（供后续元素定位）。
        """
        y += 4
        line_w = PANEL_W - 40
        lx = panel_x + 20
        pygame.draw.line(self.screen, PANEL_ACCENT, (lx, y), (lx + line_w, y), 1)
        return y + 4

    # ---------- Toast 提示 ----------
    def show_toast(self, text: str) -> None:
        """显示临时提示消息

        调用后 toast 会显示 TOAST_DURATION(90) 帧（约 1.5 秒），
        最后 25 帧带渐隐效果。

        参数:
            text — 提示文字内容
        """
        self._toast_text = text
        self._toast_timer = self.TOAST_DURATION

    def _draw_toast(self) -> None:
        """在面板中部偏下绘制 toast 提示条（渐隐效果）

        实现：
          - 深浅色背景条 + 金色文字，圆角矩形
          - 最后 25 帧 alpha 从 255 线性衰减至 0（渐隐）
          - 位置固定在按钮上方（SCREEN_H - 115）
        """
        if self._toast_timer <= 0:
            return

        px = BOARD_AREA_W                              # 面板左边界
        pw = PANEL_W

        # 渐隐 alpha：最后 25 帧线性衰减
        alpha = 255
        if self._toast_timer < 25:
            alpha = int(255 * self._toast_timer / 25)

        # 文字渲染
        text_surf = self.toast_font.render(self._toast_text, True, (255, 232, 175))
        tw, th = text_surf.get_size()
        pad_x, pad_y = 12, 8
        bar_w = tw + pad_x * 2                        # toast 背景宽度（文字宽 + 24）
        bar_h = th + pad_y                            # toast 背景高度（文字高 + 8）
        bx = px + (pw - bar_w) // 2                   # 水平居中
        by = SCREEN_H - 115                           # 固定在按钮上方

        # 背景条 + 边框（带 alpha）
        bar = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
        bar.fill((65, 50, 32, min(alpha, 220)))       # 背景色，上限 220
        pygame.draw.rect(bar, (150, 120, 80, min(alpha, 180)),
                         (0, 0, bar_w, bar_h), 1, border_radius=7)
        self.screen.blit(bar, (bx, by))
        text_surf.set_alpha(alpha)                    # 文字 alpha 同步渐隐
        self.screen.blit(text_surf, (bx + pad_x, by + (bar_h - th) // 2))

    # ==================== 坐标转换 ====================
    def mouse_to_grid(self, mouse_x: int, mouse_y: int):
        """将鼠标像素坐标转换为棋盘行列索引 (row, col)

        转换流程：
          1. 用 round() 找到最近的交叉点索引
          2. 检查行列是否在有效范围 [0, 14]
          3. 计算鼠标到交叉点的几何距离，仅当距离 ≤ STONE_RADIUS+6 时才算有效

        参数:
            mouse_x, mouse_y — 鼠标像素坐标

        返回:
            (row, col) — 棋盘坐标，或 None — 鼠标不在任何有效交叉点附近

        设计要点：
            采用圆形判定而非矩形判定，更符合"点击交叉点"的直觉。
            radius+6 的容差范围确保即使稍微偏出交叉点也能命中。
        """
        col = round((mouse_x - MARGIN_LEFT) / CELL_SIZE)
        row = round((mouse_y - MARGIN_TOP) / CELL_SIZE)
        if not (0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS):
            return None
        # 验证距离：鼠标到交叉点中心的欧几里德距离
        cx = MARGIN_LEFT + col * CELL_SIZE
        cy = MARGIN_TOP + row * CELL_SIZE
        if ((mouse_x - cx) ** 2 + (mouse_y - cy) ** 2) > (STONE_RADIUS + 6) ** 2:
            return None                               # 距离太远，不算落子位置
        return (row, col)


# ==================== 主程序 ====================

# AI 落子延迟帧数
# AI 在回合到来时不会立即落子，而是延迟 AI_DELAY 帧后再执行，
# 产生"AI 在思考"的观感。在 60 FPS 下 25 帧 ≈ 0.42 秒。
AI_DELAY = 25


def main():
    """游戏入口

    主循环结构（每帧执行）：
      1. 获取鼠标位置 → 计算 hover_pos / hovered_button
      2. 通知渲染器 game_over 变化 → 驱动胜利动画
      3. AI 定时器递减 → 到 1 时执行 AI.get_move() 并落子
      4. 处理事件（关闭 / 键盘 / 鼠标点击）
      5. 调用渲染器 update() + draw() + flip()
      6. clock.tick(60) 锁定 60 FPS
    """
    # 初始化 Pygame
    pygame.init()

    # 创建窗口（800×600，固定大小）
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("优雅五子棋")

    # 创建游戏核心对象
    board = GomokuBoard()                          # 棋盘逻辑
    renderer = GomokuRenderer(screen)              # 界面渲染

    clock = pygame.time.Clock()                     # 帧率控制器
    hover_pos = None                                # 鼠标悬停的棋盘坐标
    mode = "pvp"                                    # 默认模式：双人对战
    ai_timer = 0                                    # AI 延迟计数器（0=未启动, 1=即将执行）

    # ========== 悔棋统一处理 ==========
    # 闭包函数：同时被 Ctrl+Z 快捷键和「悔棋」按钮调用
    def handle_undo() -> bool:
        """统一悔棋处理；返回是否需要重置 ai_timer

        人机模式特殊处理：
          - 悔棋需要连续撤销两步（AI 的一手 + 玩家的一手）
          - 条件：board.move_count >= 2 且两次 undo() 均成功
          - 成功后重置 ai_timer，避免 AI 在新回合立即落子

        双人模式：
          - 普通悔棋，只撤销一步
        """
        if mode == "pvai":
            # 人机模式：连续悔两步（玩家手 + AI 手）
            if board.move_count >= 2 and board.undo() and board.undo():
                renderer.show_toast("悔棋成功")
                return True                          # 需要重置 ai_timer
            else:
                renderer.show_toast("无棋可悔")
                return False
        else:
            # 双人模式：普通悔棋一步
            if board.undo():
                renderer.show_toast("悔棋成功")
            else:
                renderer.show_toast("无棋可悔")
            return False

    # ==================== 主循环 ====================
    running = True
    while running:
        # 1. 获取鼠标状态（每帧更新）
        mouse_x, mouse_y = pygame.mouse.get_pos()
        hover_pos = renderer.mouse_to_grid(mouse_x, mouse_y)       # 棋盘悬停位置
        hovered_button = renderer.get_button_at(mouse_x, mouse_y)  # 面板按钮悬停

        # 2. 检测 game_over 边沿变化（用于触发胜利动画）
        renderer._on_game_over_changed(board.game_over)

        # ===== AI 自动落子 =====
        # 条件：人机模式 + 对局未结束 + 轮到白棋（AI）
        # 延迟机制：ai_timer 从 AI_DELAY 逐帧递减，到 1 时执行落子
        if mode == "pvai" and not board.game_over and board.current_player == WHITE:
            if ai_timer == 0:
                ai_timer = AI_DELAY                   # 启动延迟计时器
            elif ai_timer == 1:
                move = GomokuAI.get_move(board)       # 延迟结束，AI 计算落子
                if move is not None:
                    board.place_stone(*move)          # 解包 (row, col) 传入
                ai_timer = 0                          # 重置计时器
            else:
                ai_timer -= 1                         # 计时器递减

        # ===== 事件处理 =====
        for event in pygame.event.get():
            # --- 关闭窗口 ---
            if event.type == pygame.QUIT:
                running = False

            # --- 键盘快捷键 ---
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:       # ESC：退出
                    running = False
                elif event.key == pygame.K_r:          # R：重新开始
                    board.reset()
                    ai_timer = 0                       # 重置 AI 计时
                elif event.key == pygame.K_z and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    # Ctrl+Z：悔棋
                    if handle_undo():
                        ai_timer = 0                   # 人机模式下重置

            # --- 鼠标点击 ---
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:                  # 仅处理左键
                    btn = renderer.get_button_at(mouse_x, mouse_y)
                    if btn == "restart":
                        board.reset()                  # 再来一局
                        ai_timer = 0
                    elif btn == "switch_mode":
                        # 切换模式（pvp ↔ pvai），重置棋盘
                        mode = "pvai" if mode == "pvp" else "pvp"
                        board.reset()
                        ai_timer = 0
                    elif btn == "undo":
                        if handle_undo():              # 悔棋按钮
                            ai_timer = 0
                    elif btn == "exit":
                        running = False                # 退出游戏
                    elif hover_pos is not None:
                        # 点击棋盘区域：尝试落子
                        # 人机模式下仅黑棋（玩家）可点击落子
                        if mode == "pvai" and board.current_player != BLACK:
                            continue                   # 非玩家回合，忽略点击
                        board.place_stone(*hover_pos)  # 解包 (row, col)

        # ===== 画面渲染 =====
        renderer.update()                              # 更新动画计时器
        renderer.draw(board, hover_pos, hovered_button, mode)  # 绘制完整画面
        pygame.display.flip()                          # 刷新屏幕
        clock.tick(60)                                 # 锁定 60 FPS

    # 退出清理
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
