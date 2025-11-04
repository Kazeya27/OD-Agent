## 数据库构建与使用文档（SQLite）

本项目后端依赖 SQLite 数据库，表结构固定为 `places`、`relations`、`dyna`。可通过提供的脚本从原始数据构建或生成测试库。

### 相关位置
- 数据库默认路径（后端环境变量）：`DB_PATH=./geo_points.db`
- 后端读取配置：`agent/backend/database.py`
- 构建脚本：
  - 生产数据：`agent/backend/build_db_from_baidu.py`
  - 测试数据：`agent/backend/generate_test_db.py`
- 示例数据目录：`agent/data/`（需要包含 `baidu.geo`、`baidu.rel`、`baidu.od`）

---

### 表结构摘要
- `places(geo_id PRIMARY KEY, type TEXT, coordinates TEXT, name TEXT NOT NULL, province TEXT)`
- `relations(rel_id PRIMARY KEY, type TEXT, origin_id INTEGER, destination_id INTEGER, cost REAL)`
- `dyna(dyna_id PRIMARY KEY, type TEXT, time TEXT, origin_id INTEGER, destination_id INTEGER, flow REAL)`

索引（构建脚本自动创建）：
- `dyna`: time, origin_id, destination_id, type
- `relations`: origin_id, destination_id

---

### 一、从百度原始数据构建数据库（生产数据）
前置条件：准备原始文件（UTF-8 CSV 格式）放置到 `agent/data/`：
- `baidu.geo`、`baidu.rel`、`baidu.od`

执行构建：
```bash
cd agent/backend
python build_db_from_baidu.py
```
说明：
- 若存在旧库，会提示确认删除；脚本将创建 `geo_points.db`
- `baidu.od` 仅导入 2024 年及之后的数据（可在脚本内调整 `MIN_YEAR`）
- 自动补齐缺失列（如 `province`、`type`）并批量插入
- 自动创建索引与输出统计信息

完成后，在后端环境中配置：
```bash
# .env 或环境变量
DB_PATH=/绝对路径/agent/backend/geo_points.db
TABLE_PLACES=places
TABLE_RELATIONS=relations
TABLE_DYNA=dyna
```

---

### 二、生成测试数据库（内置小数据）
适用于本地开发与自动化测试：
```bash
cd agent/backend
python generate_test_db.py
```
脚本特性：
- 生成一致的三表结构
- 自动生成若干城市、关系、700 天左右的 OD 样本
- 创建必要索引并输出统计信息

配置后端指向测试库：
```bash
export DB_PATH=/绝对路径/agent/backend/geo_points.db
# 或写入 .env
```

---

### 三、后端如何读取数据库
后端通过 `agent/backend/database.py` 读取：
- `DB_PATH`、`TABLE_PLACES`、`TABLE_RELATIONS`、`TABLE_DYNA`（均可由环境变量覆盖）
- 连接开启 `PRAGMA foreign_keys=ON`、`row_factory=sqlite3.Row`
- 辅助函数示例：`load_nodes(conn)` 加载所有 `geo_id`

健康检查：
- `GET http://localhost:8502/` 返回当前 `DB_PATH` 与表名

---

### 四、性能与运维建议
- 使用 WAL 模式与合理的 `synchronous`、`cache_size`（参考脚本中的 PRAGMA 配置）
- 大规模导入时采用批量写入（脚本已实现 `BATCH_SIZE`）
- 为常用查询字段建立索引（脚本已覆盖）
- 数据备份：定期复制 `geo_points.db` 并保留多版本
- 清理与压缩：可周期性执行 `VACUUM`（仓库根目录有 `vacuum.py`）

---

### 五、常见问题
1) 文件编码错误：确保 CSV 为 UTF-8；含中文列需正确命名
2) 列缺失：脚本会做兜底（如 `province`、`type`），但建议提供完整列
3) 导入过慢：调大批量写入大小、关闭 debug、使用 SSD 存储
4) 数据时间跨度：默认仅导入 2024 年及以后，如需更早数据，调整 `MIN_YEAR`
5) 容器内路径：生产环境使用绝对路径并通过卷挂载到容器内的 `DB_PATH`
