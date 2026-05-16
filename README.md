# 百度网盘资源自动转存分享工具

自动从API获取百度网盘资源，转存到自己的网盘并创建分享链接，支持推送到Webhook。

## 功能特性

- 自动从API获取最新的百度网盘资源
- 自动验证提取码并转存文件
- 自动创建永久分享链接（随机密码）
- 支持本地缓存，减少API调用
- 支持推送到Webhook（如企业微信、钉钉等）
- 随机延迟，避免请求过快

## 环境要求

- Python 3.6+
- 依赖库：`requests`, `python-dotenv`

## 安装依赖

```bash
pip install requests python-dotenv
```

## 配置说明

创建 `.env` 文件，配置以下环境变量：

```env
# 百度网盘Cookie（必须）
COOKIE=your_baidu_pan_cookie

# 转存数量（可选，默认5）
COUNT=5

# 目标文件夹（可选，默认"转存资源"）
TARGET_FOLDER=转存资源

# Webhook地址（可选，用于推送结果）
WEBHOOK_URL=https://your-webhook-url

# 缓存过期时间（小时，可选，默认24）
CACHE_EXPIRE_HOURS=24
```

### 获取百度网盘Cookie

1. 打开浏览器，访问 [百度网盘](https://pan.baidu.com) 并登录
2. 按 F12 打开开发者工具
3. 在 `Application` -> `Cookies` -> `https://pan.baidu.com` 中找到以下Cookie：
   - `BAIDUID`
   - `BDUSS`
   - `BDUSS_BFESS`
   - `STOKEN`
4. 将所有Cookie复制出来，格式为：`BAIDUID=xxx; BDUSS=xxx; BDUSS_BFESS=xxx; STOKEN=xxx`

## 使用方法

### 直接运行

```bash
python baidu_fetch_share.py
```

### 命令行参数

脚本通过环境变量配置，无需命令行参数。

## GitHub Actions 定时运行

### 1. 创建 GitHub Repository

将代码上传到 GitHub 仓库。

### 2. 设置 Secrets

在仓库的 `Settings` -> `Secrets and variables` -> `Actions` 中添加以下 secrets：

| Secret Name | Description |
|-------------|-------------|
| `COOKIE` | 百度网盘Cookie（必须） |
| `GH_TOKEN` | GitHub Personal Access Token（需要有 `repo` 权限，用于提交缓存文件） |
| `COUNT` | 转存数量（可选） |
| `TARGET_FOLDER` | 目标文件夹（可选） |
| `WEBHOOK_URL` | Webhook地址（可选） |
| `CACHE_EXPIRE_HOURS` | 缓存过期时间（可选，单位小时） |

### 创建 GitHub Personal Access Token (GH_TOKEN)

1. 登录 GitHub，进入 **Settings > Developer settings > Personal access tokens**
2. 点击 **Generate new token**
3. 设置 token 名称（如 `baidu-pan-token`）
4. 勾选 `repo` 权限（包括 `repo:status`、`repo_deployment`、`public_repo`）
5. 点击 **Generate token** 并复制生成的 token
6. 在仓库 Secrets 中添加 `GH_TOKEN`，值为复制的 token

### 3. 创建 Workflow 文件

在 `.github/workflows/` 目录下创建 `auto-run.yml` 文件：

```yaml
name: 自动转存百度网盘资源

on:
  schedule:
    # 每30分钟运行一次
    - cron: '*/30 * * * *'
  # 手动触发
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.x'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install requests python-dotenv

    - name: Run script
      env:
        COOKIE: ${{ secrets.COOKIE }}
        COUNT: ${{ secrets.COUNT }}
        TARGET_FOLDER: ${{ secrets.TARGET_FOLDER }}
        WEBHOOK_URL: ${{ secrets.WEBHOOK_URL }}
      run: python baidu_fetch_share.py
```

### 4. 启用 Actions

在 GitHub 仓库的 `Actions` 选项卡中启用该 workflow。

### Cron 表达式说明

- `*/30 * * * *` - 每30分钟运行一次
- `0 * * * *` - 每小时运行一次
- `0 0 * * *` - 每天凌晨运行一次

### 工作流程说明

GitHub Actions 运行时的完整流程：

1. **脚本执行**：运行 `baidu_fetch_share.py`，生成 `api_cache.json` 缓存文件
2. **Git 配置**：配置 GitHub Actions Bot 的用户名和邮箱
3. **缓存提交**：检查缓存文件是否存在且有变更，如有则提交到仓库
4. **推送更新**：将提交推送到当前分支

提交消息格式为 `Update API cache`，只有当缓存文件有实际变更时才会提交。

## 注意事项

1. **Cookie有效期**：百度网盘Cookie会定期失效，需要定期更新
2. **频繁操作限制**：百度网盘对频繁操作有限制，建议设置合理的延迟
3. **容量限制**：确保目标网盘有足够的存储空间
4. **分享链接有效期**：默认创建永久分享链接

## 错误代码说明

| 错误代码 | 说明 |
|----------|------|
| -1 | 链接错误，链接失效或缺少提取码 |
| -4 | 转存失败，无效登录 |
| -6 | 转存失败，Cookie失效 |
| -7 | 转存失败，文件夹名有非法字符 |
| -8 | 转存失败，目录中已有同名文件 |
| -9 | 链接错误，提取码错误 |
| -10 | 转存失败，容量不足 |
| 0 | 转存成功 |

## License

MIT License
