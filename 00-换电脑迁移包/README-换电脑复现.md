# 换电脑复现说明

这个目录是为“整项目拷到 U 盘，然后在另一台电脑恢复”准备的辅助迁移包。

## 1. 需要拷走什么

最稳妥的方式：直接复制整个 `英语单词微信小程序` 文件夹到 U 盘。

其中最关键的是：

- `backend/`：Django 后端代码、迁移文件、媒体文件、`.env`
- `front/`：微信小程序前端代码
- `1-需求分析/`、`3-架构设计/`：项目文档
- `00-换电脑迁移包/database/*.sql`：当前 MySQL 数据库导出
- `00-换电脑迁移包/env/backend.env.backup`：当前后端环境变量备份
- `00-换电脑迁移包/scripts/`：数据库导入/导出和后端启动脚本

注意：`backend/.env` 和 `env/backend.env.backup` 里包含 AI Key、数据库密码等敏感信息，只适合自己转移，不要上传公开仓库或发给别人。

## 2. 新电脑需要先安装

- Python，建议 3.11 到 3.13
- MySQL Server 8.0
- 微信开发者工具
- Node.js 可选。当前小程序代码主要是原生小程序，没有强制 npm 构建流程

如果使用 MySQL 命令行脚本，请把 MySQL 的 `bin` 目录加入 PATH，例如：

```powershell
C:\Program Files\MySQL\MySQL Server 8.0\bin
```

## 3. 后端环境恢复

在新电脑打开 PowerShell，进入项目根目录：

```powershell
cd 你的路径\英语单词微信小程序
```

建议创建虚拟环境：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

如果你继续用 Anaconda，也可以直接在对应环境里执行：

```powershell
pip install -r requirements.txt
```

## 4. 修改 `.env`

确认 `backend/.env` 存在。如果没有，可以从迁移包恢复：

```powershell
Copy-Item ..\00-换电脑迁移包\env\backend.env.backup .env
```

如果新电脑 MySQL 密码、库名或端口不同，在 `backend/.env` 里补充或修改：

```env
MYSQL_DB=wxappEnglishlearn
MYSQL_USER=root
MYSQL_PASSWORD=你的新电脑MySQL密码
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
```

当前项目代码如果 `.env` 里没有这些 MySQL 配置，会使用默认值：

```text
MYSQL_DB=wxappEnglishlearn
MYSQL_USER=root
MYSQL_PASSWORD=199977
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
```

## 5. 导入数据库

回到项目根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\00-换电脑迁移包\scripts\import_database.ps1 -CreateDatabase
```

脚本会读取 `backend/.env` 的 MySQL 配置，并自动使用 `00-换电脑迁移包/database` 里最新的 `.sql` 文件。

如果你想指定 SQL 文件：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\00-换电脑迁移包\scripts\import_database.ps1 -CreateDatabase -SqlFile ".\00-换电脑迁移包\database\你的文件.sql"
```

## 6. 检查并启动后端

```powershell
cd backend
python manage.py check
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

也可以从项目根目录使用脚本后台启动：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\00-换电脑迁移包\scripts\start_backend.ps1
```

后端地址：

```text
http://127.0.0.1:8000
```

## 7. 打开小程序

用微信开发者工具打开：

```text
front
```

如果前端配置了后端地址，确认它指向新电脑后端：

```text
http://127.0.0.1:8000/api/v1
```

## 8. 以后再次导出数据库

在旧电脑或当前电脑项目根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\00-换电脑迁移包\scripts\export_database.ps1
```

新的 SQL 会放到：

```text
00-换电脑迁移包/database/
```

