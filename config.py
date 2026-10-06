"""全局配置"""
# 分支练习

import os

# ---------- 项目路径 ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORT_DIR = os.path.join(BASE_DIR, "reports")
SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshots")

# ---------- 数据文件 ----------
USERS_CSV = os.path.join(DATA_DIR, "users.csv")

# ---------- 环境配置 ----------
BASE_URL = "http://localhost"

# ---------- 登录账号 ----------
USERNAME = "admin"
PASSWORD = "admin123"

# ---------- 超时（秒） ----------
TIMEOUT = 10

# ---------- 浏览器 ----------
HEADLESS = True
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080

# ---------- 数据库 ----------
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "root"
DB_NAME = "ry-vue"

# ---------- 环境配置 ----------
BASE_URL = "http://localhost"
API_BASE_URL = "http://localhost:8080"