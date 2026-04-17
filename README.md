# 基于CNN的校园课堂智能考勤系统

> 重庆邮电大学 2025届 毕业设计  
> 学生：苏东煌（2022214380）  指导教师：张晓霞

## 项目简介

利用摄像头采集课堂画面，通过 MTCNN 人脸检测 + ResNet50/VGG16 特征提取，实现课堂自动点名考勤。系统支持 Web 端实时监控、考勤记录查询和报表导出。

## 技术栈

| 层次 | 技术 |
|------|------|
| AI 推理 | PyTorch + facenet-pytorch（MTCNN）+ ResNet50/VGG16 |
| 后端 | Flask 3 + SQLAlchemy 2 + Flask-JWT-Extended + Flask-SocketIO |
| 前端 | Vue 3 + Vite 5 + Pinia + Element Plus + ECharts + Socket.IO |
| 数据库 | MySQL 8.0 |
| 实时通信 | WebSocket（Socket.IO + eventlet）|

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0

### 安装与启动

```bash
# 1. 克隆仓库
git clone https://github.com/sudonghuang/CNN.git
cd CNN

# 2. 一键初始化（创建venv、安装依赖、初始化数据库）
bash setup.sh

# 3. 启动后端（另开一个终端）
cd backend
.venv/bin/python run.py

# 4. 启动前端
cd frontend
npm run dev
```

访问 http://localhost:5173，默认管理员账号：`admin / Admin@123456`

### 手动配置数据库

```bash
cd backend
cp .env.example .env        # 修改 DEV_DATABASE_URL 中的数据库密码
.venv/bin/flask db upgrade  # 创建表结构
.venv/bin/python scripts/seed_admin.py  # 创建管理员账号
```

## 项目结构

```
CNN/
├── backend/                # Flask 后端
│   ├── app/
│   │   ├── api/            # REST API 蓝图（auth/students/faces/attendance/courses/reports）
│   │   ├── services/       # 业务逻辑层
│   │   ├── models/         # SQLAlchemy ORM 模型
│   │   ├── ai/             # AI 推理模块（人脸检测/识别/特征库）
│   │   └── ws/             # WebSocket 处理器（Socket.IO）
│   ├── model/              # 模型训练脚本
│   ├── tests/              # pytest 测试套件
│   ├── scripts/            # 数据库初始化脚本
│   └── requirements.txt
├── frontend/               # Vue 3 前端
│   ├── src/
│   │   ├── views/          # 页面组件（仪表盘/学生/人脸采集/考勤/报表）
│   │   ├── stores/         # Pinia 状态管理
│   │   ├── api/            # Axios API 封装
│   │   └── router/         # 路由配置（含角色守卫）
│   └── package.json
├── docs/                   # 设计文档（需求/概要/详细/测试/流程图/类图）
└── setup.sh                # 一键环境初始化脚本
```

## 核心功能

- **人脸采集**：支持摄像头实时拍照和图片批量上传（每人≥5张）
- **模型训练**：迁移学习微调 ResNet50/VGG16，L2归一化余弦相似度匹配
- **实时考勤**：WebSocket 推流，500ms/帧，识别结果实时回显
- **考勤管理**：任务创建/开始/结束，支持教师人工修正
- **统计报表**：出勤率折线图，Excel导出，缺勤预警

## 性能指标

- 人脸检测准确率 ≥ 90%
- 身份识别准确率（Top-1）≥ 85%
- 考勤响应时间 ≤ 5秒/次

## 许可证

仅供学术研究使用
