# YFS

---

## 📊 技术分析

### 使用步骤

1. **输入股票代码**
   - 在顶部输入框输入代码（如 `AAPL`、`TSLA`、`NVDA`）
   - 支持热门股票自动补全
   - 自动转换为大写

2. **查看分析结果**
   - 点击「开始分析」按钮
   - 自动显示：
     * 价格信息和趋势
     * K线图（TradingView）
     * 移动平均线（MA5/10/20/50）
     * 20+ 技术指标
     * 关键价位（支撑/压力位）
     * 交易信号和综合评分
     * 风险等级和建议

3. **AI分析报告**（需配置Ollama）
   - 如果Ollama可用，自动生成AI分析
   - 点击右下角🤖按钮查看详细报告
   - 包含趋势判断、操作建议等

4. **刷新数据**
   - 点击「刷新」按钮强制更新
   - 跳过缓存，获取最新数据

### 指标说明

- 每个指标标题旁有 **?** 图标
- 点击可查看指标的详细说明：
  - 指标含义
  - 计算方法
  - 参考范围
  - 使用方法
- 帮助理解各项技术指标

---

## 📊 技术指标说明

### 趋势指标

- **MA (Moving Average)**：移动平均线，包括 MA5、MA10、MA20、MA50
- **ADX (Average Directional Index)**：平均趋向指数，衡量趋势强度
- **SuperTrend**：超级趋势指标，判断趋势方向
- **Ichimoku Cloud**：一目均衡表，综合趋势指标

### 动量指标

- **RSI (Relative Strength Index)**：相对强弱指数
  - < 30: 超卖
  - \> 70: 超买
- **MACD**：指数平滑移动平均线
  - MACD线、信号线、柱状图
- **KDJ**：随机指标
- **StochRSI**：随机相对强弱指数

### 波动指标

- **Bollinger Bands**：布林带
  - 上轨、中轨（MA20）、下轨
- **ATR (Average True Range)**：平均真实波幅
- **Volatility**：历史波动率

### 成交量指标

- **Volume Ratio**：成交量比率
- **OBV (On-Balance Volume)**：能量潮指标
- **VWAP (Volume Weighted Average Price)**：成交量加权平均价
- **Volume Profile**：成交量分布

### 支撑压力指标

- **Support/Resistance**：支撑位和压力位
- **Pivot Points**：枢轴点
- **SAR (Parabolic SAR)**：抛物线转向指标
- **Fibonacci Retracement**：斐波那契回撤位

---

## 🐳 部署方式

### Docker Compose 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/yfs.git
cd yfs

# 2. 构建并启动所有服务
docker-compose up -d --build

# 3. 访问应用
# 前端: http://localhost:8086
# 后端API: http://localhost:8086/api/ (通过 Nginx 代理)

# 查看日志
docker-compose logs -f backend    # 后端日志
docker-compose logs -f frontend   # 前端日志
docker-compose logs -f nginx      # Nginx 日志

# 停止服务
docker-compose down

# 重新构建后端
docker-compose build backend
docker-compose up -d backend
```

**服务说明：**
- **Nginx**: 反向代理，端口 8086，转发请求到前端和后端
- **Backend**: Django 后端，使用 gunicorn 启动，端口 8080（内部）
- **Frontend**: React 前端，端口 80（内部）

### 本地开发部署

#### 后端启动（Django）

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 数据库迁移（首次运行）
python manage.py migrate

# 5. 启动开发服务器
python manage.py runserver 0.0.0.0:8080
# 服务运行在 http://localhost:8080

# 或使用 gunicorn（生产模式）
gunicorn --bind 0.0.0.0:8080 --workers 4 backend.wsgi:application
```

#### 前端启动

```bash
# 1. 安装依赖
cd web
npm install

# 2. 启动开发服务器
npm run dev
# 服务运行在 http://localhost:5173
```

### Ollama 配置（可选，用于 AI 分析）

```bash
# 1. 安装 Ollama
# 访问 https://ollama.ai 下载安装

# 2. 拉取推荐模型
ollama pull deepseek-v3.1:671b-cloud

# 3. 启动 Ollama 服务
ollama serve
```

### 环境变量配置

Docker 环境变量在 `docker-compose.yml` 中已配置：
- `OLLAMA_HOST=http://host.docker.internal:11434` - Ollama 服务地址（宿主机）
- `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` - Python 3.14 兼容性设置

**注意事项：**
- 如果 Ollama 在宿主机运行：使用 `http://host.docker.internal:11434`
- 如果 Ollama 在 Docker 中运行：使用容器网络地址
- 确保 Ollama 监听 `0.0.0.0:11434` 而不是 `127.0.0.1:11434`，以便 Docker 容器访问


## 🔌 API 端点

### 核心接口

- `GET /api/health` - 健康检查
- `GET /api/analyze/<symbol>` - 技术分析（支持缓存）
- `POST /api/refresh-analyze/<symbol>` - 强制刷新分析
- `POST /api/ai-analyze/<symbol>` - AI 分析（异步，支持轮询）
- `GET /api/analysis-status/<symbol>` - 查询分析状态

### 数据接口

- `GET /api/fundamental/<symbol>` - 基本面数据
- `GET /api/institutional/<symbol>` - 机构持仓
- `GET /api/insider/<symbol>` - 内部交易
- `GET /api/recommendations/<symbol>` - 分析师推荐
- `GET /api/earnings/<symbol>` - 收益数据
- `GET /api/news/<symbol>` - 新闻
- `GET /api/options/<symbol>` - 期权数据
- `GET /api/comprehensive/<symbol>` - 综合分析
- `GET /api/all-data/<symbol>` - 所有原始数据

### 辅助接口

- `GET /api/hot-stocks` - 热门股票列表
- `GET /api/indicator-info` - 技术指标说明


## 📄 许可证

MIT License

