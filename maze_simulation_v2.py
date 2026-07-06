import sys
import random
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QSlider, QFrame)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPolygon, QFont
from PySide6.QtCore import Qt, QTimer, QPoint

GRID_SIZE = 30
CELL_SIZE = 20 # UI pixel size per cell
MAZE_WIDTH = GRID_SIZE * CELL_SIZE
MAZE_HEIGHT = GRID_SIZE * CELL_SIZE

# Directions bitmasks
N, S, E, W = 1, 2, 4, 8
DX = {E: 1, W: -1, N: 0, S: 0}
DY = {E: 0, W: 0, N: -1, S: 1}
OPPOSITE = {E: W, W: E, N: S, S: N}
RIGHT_TURN = {N: E, E: S, S: W, W: N}
LEFT_TURN = {N: W, W: S, S: E, E: N}
BACK_TURN = {N: S, S: N, E: W, W: E}

class Maze:
    def __init__(self, size=30, seed=42):
        self.size = size
        self.seed = seed
        self.grid = [[0 for _ in range(size)] for _ in range(size)]
        self.generate()
        
    def generate(self):
        random.seed(self.seed)
        visited = [[False]*self.size for _ in range(self.size)]
        
        def carve_passages_from(cx, cy):
            directions = [N, S, E, W]
            random.shuffle(directions)
            
            for direction in directions:
                nx, ny = cx + DX[direction], cy + DY[direction]
                
                if 0 <= nx < self.size and 0 <= ny < self.size and not visited[ny][nx]:
                    self.grid[cy][cx] |= direction
                    self.grid[ny][nx] |= OPPOSITE[direction]
                    visited[ny][nx] = True
                    carve_passages_from(nx, ny)
                    
        visited[0][0] = True
        carve_passages_from(0, 0)
        
    def has_wall(self, x, y, direction):
        return (self.grid[y][x] & direction) == 0

class MouseAgent:
    def __init__(self, maze, start_x=0, start_y=0, start_dir=E):
        self.maze = maze
        self.x = start_x
        self.y = start_y
        self.direction = start_dir
        self.steps = 0
        self.decisions = 0
        
    def step(self):
        right = RIGHT_TURN[self.direction]
        left = LEFT_TURN[self.direction]
        back = BACK_TURN[self.direction]
        
        self.decisions += 1
        
        # Right-Hand Rule priority: Right -> Front -> Left -> Back
        if not self.maze.has_wall(self.x, self.y, right):
            self.direction = right
            self.move_forward()
        elif not self.maze.has_wall(self.x, self.y, self.direction):
            self.move_forward()
        elif not self.maze.has_wall(self.x, self.y, left):
            self.direction = left
            self.move_forward()
        else:
            self.direction = back
            self.move_forward()
            
    def move_forward(self):
        self.x += DX[self.direction]
        self.y += DY[self.direction]
        self.steps += 1

class MazeCanvas(QWidget):
    def __init__(self, app_main):
        super().__init__()
        self.app_main = app_main
        self.maze = app_main.maze
        self.agent = app_main.agent
        # เพิ่มพื้นที่ด้านบนสำหรับวาดตัวจับเวลา
        self.setMinimumSize(MAZE_WIDTH + 40, MAZE_HEIGHT + 80)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor("#1e1e1e"))
        
        offset_x, offset_y = 20, 60 # ขยับ Y ลงมา 60 px เพื่อเว้นที่ให้ตัวจับเวลา
        
        # วาดตัวจับเวลาแบบ Digital บน Canvas ให้เห็นชัดเจนตลอดเวลา
        rem = max(0, self.app_main.time_limit - self.app_main.sim_time)
        mins = int(rem // 60)
        secs = int(rem % 60)
        ms = int((rem - int(rem)) * 100)
        time_text = f"Time Left: {mins:02d}:{secs:02d}.{ms:02d}"
        
        if self.app_main.state == "SUCCESS":
            painter.setPen(QPen(QColor("#00FF00")))
            time_text = f"SUCCESS! Time: {mins:02d}:{secs:02d}.{ms:02d}"
        elif self.app_main.state == "DEAD":
            painter.setPen(QPen(QColor("#FF0000")))
            time_text = f"DEAD (Timeout)! 00:00.00"
        else:
            painter.setPen(QPen(QColor("#FFD700")))
            
        painter.setFont(QFont("Consolas", 20, QFont.Bold))
        painter.drawText(offset_x, 40, time_text)

        # 1. วาดตาราง (Grid) ให้เห็นเป็นช่องชัดๆ ตามคำขอ
        grid_pen = QPen(QColor("#333333"), 1)
        painter.setPen(grid_pen)
        for y in range(self.maze.size + 1):
            py = offset_y + y * CELL_SIZE
            painter.drawLine(offset_x, py, offset_x + MAZE_WIDTH, py)
        for x in range(self.maze.size + 1):
            px = offset_x + x * CELL_SIZE
            painter.drawLine(px, offset_y, px, offset_y + MAZE_HEIGHT)
        
        # 2. วาดกำแพง (Walls) ทับเส้นตาราง
        wall_pen = QPen(QColor("#00d2ff"), 2)
        painter.setPen(wall_pen)
        
        for y in range(self.maze.size):
            for x in range(self.maze.size):
                px = offset_x + x * CELL_SIZE
                py = offset_y + y * CELL_SIZE
                
                cell = self.maze.grid[y][x]
                if not (cell & N): painter.drawLine(px, py, px + CELL_SIZE, py)
                if not (cell & S): painter.drawLine(px, py + CELL_SIZE, px + CELL_SIZE, py + CELL_SIZE)
                
                # ทางเข้า (0,0) ฝั่งซ้ายเปิด
                if x == 0 and y == 0:
                    pass 
                elif not (cell & W): 
                    painter.drawLine(px, py, px, py + CELL_SIZE)
                
                # ทางออก (29,29) ฝั่งขวาเปิด
                if x == self.maze.size - 1 and y == self.maze.size - 1:
                    pass 
                elif not (cell & E): 
                    painter.drawLine(px + CELL_SIZE, py, px + CELL_SIZE, py + CELL_SIZE)

        # วาดเป้าหมาย (ชีส)
        cheese_x = offset_x + (self.maze.size - 1) * CELL_SIZE
        cheese_y = offset_y + (self.maze.size - 1) * CELL_SIZE
        painter.setBrush(QBrush(QColor("#FFD700")))
        painter.setPen(Qt.NoPen)
        poly = QPolygon([
            QPoint(cheese_x + 4, cheese_y + CELL_SIZE - 4),
            QPoint(cheese_x + CELL_SIZE - 4, cheese_y + CELL_SIZE - 4),
            QPoint(cheese_x + CELL_SIZE // 2, cheese_y + 4)
        ])
        painter.drawPolygon(poly)
        
        # วาดเส้น Direct Vector
        mx = offset_x + self.agent.x * CELL_SIZE + CELL_SIZE // 2
        my = offset_y + self.agent.y * CELL_SIZE + CELL_SIZE // 2
        c_cx = cheese_x + CELL_SIZE // 2
        c_cy = cheese_y + CELL_SIZE // 2
        
        line_pen = QPen(QColor("#FFA500"), 2, Qt.DashLine)
        painter.setPen(line_pen)
        painter.drawLine(mx, my, c_cx, c_cy)
        
        # วาดตัวหนู
        painter.setBrush(QBrush(QColor("#FF7F50")))
        painter.setPen(QPen(QColor("#FFFFFF"), 1))
        painter.drawEllipse(mx - 6, my - 6, 12, 12)
        
        # จมูกบอกทิศทางหนู
        nx, ny = mx, my
        if self.agent.direction == N: ny -= 8
        elif self.agent.direction == S: ny += 8
        elif self.agent.direction == E: nx += 8
        elif self.agent.direction == W: nx -= 8
        
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(nx - 2, ny - 2, 4, 4)

class MazeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Maze & Mouse Agent Simulation - V2")
        self.setStyleSheet("background-color: #2b2b2b; color: white;")
        
        self.maze = Maze(size=GRID_SIZE, seed=42)
        self.agent = MouseAgent(self.maze)
        
        self.time_limit = 180.0
        self.sim_time = 0.0
        self.last_real_time = 0.0
        self.state = "IDLE"
        
        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self.update_sim)
        self.sim_speed = 50
        
        # Timer สำหรับอัปเดตหน้าจอ UI แยกจากการเคลื่อนที่ของหนู
        # เพื่อให้ตัวจับเวลาเดินละเอียดแบบ Real-time แม้หนูจะยังไม่ขยับ
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_ui_timer)
        self.ui_timer.start(16) # ~60fps
        
        self.init_ui()
        
    def init_ui(self):
        main_widget = QWidget()
        layout = QHBoxLayout(main_widget)
        
        self.canvas = MazeCanvas(self)
        layout.addWidget(self.canvas)
        
        sidebar = QFrame()
        sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        
        title = QLabel("Mouse Agent\nSimulator V2")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #00d2ff;")
        sidebar_layout.addWidget(title)
        
        self.lbl_time = QLabel("Time Left: 03:00.00")
        self.lbl_time.setFont(QFont("Consolas", 14, QFont.Bold))
        self.lbl_time.setStyleSheet("color: #FFD700; margin-top: 20px;")
        sidebar_layout.addWidget(self.lbl_time)
        
        self.lbl_state = QLabel("State: IDLE")
        self.lbl_state.setFont(QFont("Arial", 12))
        sidebar_layout.addWidget(self.lbl_state)
        
        self.lbl_steps = QLabel("Steps: 0")
        self.lbl_steps.setFont(QFont("Arial", 12))
        sidebar_layout.addWidget(self.lbl_steps)
        
        self.lbl_decisions = QLabel("Decisions: 0")
        self.lbl_decisions.setFont(QFont("Arial", 12))
        sidebar_layout.addWidget(self.lbl_decisions)
        
        sidebar_layout.addSpacing(20)
        
        btn_start = QPushButton("Start / Pause")
        btn_start.clicked.connect(self.toggle_sim)
        btn_start.setStyleSheet("background-color: #007acc; padding: 10px; font-weight: bold; font-size: 14px; border-radius: 5px;")
        sidebar_layout.addWidget(btn_start)
        
        btn_reset = QPushButton("Reset")
        btn_reset.clicked.connect(self.reset_sim)
        btn_reset.setStyleSheet("background-color: #cc4444; padding: 10px; font-weight: bold; font-size: 14px; border-radius: 5px;")
        sidebar_layout.addWidget(btn_reset)
        
        sidebar_layout.addSpacing(20)
        
        lbl_speed = QLabel("Simulation Speed (Step Interval):")
        lbl_speed.setFont(QFont("Arial", 10))
        sidebar_layout.addWidget(lbl_speed)
        
        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(5, 200)
        self.slider_speed.setValue(50)
        self.slider_speed.setInvertedAppearance(True)
        self.slider_speed.valueChanged.connect(self.change_speed)
        sidebar_layout.addWidget(self.slider_speed)
        
        sidebar_layout.addStretch()
        layout.addWidget(sidebar)
        self.setCentralWidget(main_widget)
        
    def toggle_sim(self):
        if self.state in ["SUCCESS", "DEAD"]: return
        if self.sim_timer.isActive():
            self.sim_timer.stop()
            self.state = "PAUSED"
        else:
            self.last_real_time = time.time()
            self.sim_timer.start(self.sim_speed)
            self.state = "RUNNING"
        self.canvas.update()
        
    def reset_sim(self):
        self.sim_timer.stop()
        self.agent = MouseAgent(self.maze)
        self.canvas.agent = self.agent
        self.sim_time = 0.0
        self.state = "IDLE"
        self.update_labels()
        self.canvas.update()
        
    def change_speed(self):
        self.sim_speed = self.slider_speed.value()
        if self.sim_timer.isActive():
            self.sim_timer.setInterval(self.sim_speed)
            
    def update_ui_timer(self):
        # ให้อัปเดตตัวจับเวลาแม้หนูจะขยับตาม interval ที่ช้ากว่า
        if self.state == "RUNNING":
            now = time.time()
            dt = now - self.last_real_time
            # ถ้าหนูไปถึงเป้าหมายหรือตายแล้ว ให้หยุดเวลา
            if self.agent.x == self.maze.size - 1 and self.agent.y == self.maze.size - 1:
                self.sim_time += dt
                self.last_real_time = now
                self.state = "SUCCESS"
                self.sim_timer.stop()
            elif self.sim_time + dt >= self.time_limit:
                self.sim_time = self.time_limit
                self.state = "DEAD"
                self.sim_timer.stop()
            else:
                self.sim_time += dt
                self.last_real_time = now
                
            self.update_labels()
            self.canvas.update()
            
    def update_sim(self):
        if self.state != "RUNNING": return
        self.agent.step()
        self.update_labels()
        self.canvas.update()
        
    def update_labels(self):
        rem = max(0, self.time_limit - self.sim_time)
        mins = int(rem // 60)
        secs = int(rem % 60)
        ms = int((rem - int(rem)) * 100)
        self.lbl_time.setText(f"Time Left: {mins:02d}:{secs:02d}.{ms:02d}")
        
        if self.state == "SUCCESS":
            self.lbl_state.setStyleSheet("color: #00FF00; font-weight: bold;")
        elif self.state == "DEAD":
            self.lbl_state.setStyleSheet("color: #FF0000; font-weight: bold;")
        else:
            self.lbl_state.setStyleSheet("color: white;")
            
        self.lbl_state.setText(f"State: {self.state}")
        self.lbl_steps.setText(f"Steps: {self.agent.steps}")
        self.lbl_decisions.setText(f"Decisions: {self.agent.decisions}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MazeApp()
    window.show()
    sys.exit(app.exec())
