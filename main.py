import pygame
import numpy as np

# ===================== 初始化配置 =====================
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("反走样贝塞尔曲线 + 三次B样条曲线")
clock = pygame.time.Clock()
FPS = 60

# 颜色定义
WHITE = (255, 255, 255)
BLUE = (0, 100, 255)
RED = (255, 50, 50)
BLACK = (0, 0, 0)

# 全局参数
control_points = []  # 控制点列表
use_bspline = False  # 曲线模式：False=贝塞尔，True=B样条
AA_RADIUS = 1.2      # 反走样作用半径
AA_STRENGTH = 1.0    # 反走样强度

# ===================== 【关键修复】中文字体加载 =====================
# 优先使用系统自带的中文字体，确保Windows下100%可用
def get_chinese_font(size=24):
    # 按优先级尝试常见中文字体
    font_names = [
        "Microsoft YaHei",  # 微软雅黑（Windows自带）
        "SimHei",            # 黑体
        "SimSun",            # 宋体
        "PingFang SC",       # 苹方（macOS）
        "WenQuanYi Zen Hei"  # 文泉驿（Linux）
    ]
    for name in font_names:
        try:
            return pygame.font.SysFont(name, size)
        except:
            continue
    # 兜底：用默认字体（极端情况）
    return pygame.font.SysFont(None, size)

# 预加载字体
font = get_chinese_font(24)
large_font = get_chinese_font(36)

# ===================== 核心数学函数 =====================
def bezier_point(points, t):
    """计算贝塞尔曲线上的点（德卡斯特里奥算法）"""
    p = points.copy()
    n = len(p)
    for k in range(1, n):
        for i in range(n - k):
            p[i] = (
                (1 - t) * p[i][0] + t * p[i+1][0],
                (1 - t) * p[i][1] + t * p[i+1][1]
            )
    return p[0]

def uniform_cubic_bspline(points):
    """生成均匀三次B样条曲线点（每4个控制点一段）"""
    curve_points = []
    n = len(points)
    if n < 4:
        return curve_points

    # 三次B样条基矩阵（标准矩阵）
    M = np.array([
        [-1,  3, -3, 1],
        [ 3, -6,  3, 0],
        [-3,  0,  3, 0],
        [ 1,  4,  1, 0]
    ]) / 6

    # 遍历所有分段（n个控制点生成n-3段曲线）
    for i in range(n - 3):
        p0, p1, p2, p3 = points[i:i+4]
        P = np.array([p0, p1, p2, p3])
        
        # 采样生成曲线点
        for t in np.linspace(0, 1, 30):
            t_vec = np.array([t**3, t**2, t, 1])
            point = t_vec @ M @ P
            curve_points.append((point[0], point[1]))
    
    return curve_points

# ===================== 反走样渲染核心 =====================
def draw_antialiasedot(surface, x, y, color, radius=AA_RADIUS, strength=AA_STRENGTH):
    """亚像素反走样点绘制：3x3邻域距离衰减渲染"""
    cx = int(x)
    cy = int(y)
    
    # 遍历3x3邻域像素
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            px = cx + dx
            py = cy + dy
            if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                # 计算像素中心到几何点的欧氏距离
                dist = np.hypot(px + 0.5 - x, py + 0.5 - y)
                # 距离衰减权重：越近权重越大
                weight = max(0, 1 - dist / radius) * strength
                if weight > 0:
                    # 获取原始像素颜色
                    orig = surface.get_at((px, py))
                    # 颜色混合
                    new_r = int(orig[0] * (1 - weight) + color[0] * weight)
                    new_g = int(orig[1] * (1 - weight) + color[1] * weight)
                    new_b = int(orig[2] * (1 - weight) + color[2] * weight)
                    surface.set_at((px, py), (new_r, new_g, new_b))

def draw_antialiased_line(surface, p1, p2, color):
    """反走样线段绘制（用于曲线渲染）"""
    length = int(np.hypot(p2[0]-p1[0], p2[1]-p1[1]) * 1.5)
    for i in range(length):
        t = i / max(length - 1, 1)
        x = p1[0] + (p2[0] - p1[0]) * t
        y = p1[1] + (p2[1] - p1[1]) * t
        draw_antialiasedot(surface, x, y, color)

# ===================== 曲线渲染函数 =====================
def draw_curve():
    """根据当前模式渲染曲线（反走样）"""
    if len(control_points) < 2:
        return
    
    if not use_bspline:
        # 渲染反走样贝塞尔曲线
        curve_points = []
        for t in np.linspace(0, 1, 100):
            curve_points.append(bezier_point(control_points, t))
    else:
        # 渲染反走样三次B样条曲线
        curve_points = uniform_cubic_bspline(control_points)
    
    # 绘制连续的反走样曲线
    for i in range(len(curve_points) - 1):
        p1 = curve_points[i]
        p2 = curve_points[i+1]
        draw_antialiased_line(screen, p1, p2, BLUE)

def draw_control_points():
    """绘制控制点"""
    for (x, y) in control_points:
        pygame.draw.circle(screen, RED, (int(x), int(y)), 4)
    # 绘制控制点连线
    if len(control_points) > 1:
        pygame.draw.lines(screen, (150,150,150), False, control_points, 1)

# ===================== 主循环 =====================
running = True
screen.fill(BLACK)
while running:
    # 半透明清屏（保留轨迹效果）
    s = pygame.Surface((WIDTH, HEIGHT))
    s.set_alpha(255)
    s.fill(BLACK)
    screen.blit(s, (0,0))

    # 事件处理
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        # 鼠标左键添加控制点
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            control_points.append(pygame.mouse.get_pos())
        # 键盘B键切换模式
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_b:
                use_bspline = not use_bspline
            # 清空屏幕
            if event.key == pygame.K_c:
                control_points.clear()
                screen.fill(BLACK)

    # 绘制
    draw_control_points()
    draw_curve()

    # 【修复后】显示提示文字（使用中文字体）
    mode_text = "模式：B样条曲线" if use_bspline else "模式：贝塞尔曲线"
    tip1 = font.render("鼠标左键：添加控制点", True, WHITE)
    tip2 = font.render("B键：切换曲线模式", True, WHITE)
    tip3 = font.render("C键：清空屏幕", True, WHITE)
    tip4 = font.render(mode_text, True, RED)
    screen.blit(tip1, (10, 10))
    screen.blit(tip2, (10, 35))
    screen.blit(tip3, (10, 60))
    screen.blit(tip4, (10, 85))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()