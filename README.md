# Auto Backup Windows

[![PyPI version](https://badge.fury.io/py/auto-backup-wins.svg)](https://badge.fury.io/py/auto-backup-wins)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个用于Windows环境的自动备份工具，支持文件备份、压缩和上传到云端。

## ✨ 功能特性

- ✅ **自动备份**：自动备份Windows系统中的重要文件
- ✅ **智能分类**：智能文件分类（文档/配置）
- ✅ **自动压缩**：自动压缩备份文件，节省存储空间
- ✅ **大文件分片**：大文件自动分片处理
- ✅ **云端上传**：自动上传到云端（GoFile）
- ✅ **定时备份**：支持定时备份功能
- ✅ **ZTB监控**：ZTB监控和自动上传
- ✅ **日志管理**：完整的日志记录和轮转
- ✅ **网络检测**：自动检测网络连接状态
- ✅ **自动重试**：上传失败自动重试机制

## 🚀 快速开始

### 从 PyPI 安装（推荐）

```bash
pip install auto-backup-wins
```

### 使用 pipx 安装（推荐用于命令行工具）

`pipx` 是安装命令行工具的最佳方式，它会自动管理虚拟环境。

```bash
# 安装 pipx（如果未安装）
python -m pip install --user pipx
python -m pipx ensurepath

# 从 PyPI 安装
pipx install auto-backup-wins
```

## 📦 其他安装方式

### 使用虚拟环境安装

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows PowerShell:
venv\Scripts\Activate.ps1
# Windows CMD:
venv\Scripts\activate.bat

# 从 PyPI 安装
pip install auto-backup-wins
```

### 使用 Poetry（推荐用于开发）

Poetry 是一个现代的 Python 依赖管理和打包工具。

```bash
# 安装 Poetry（如果未安装）
# PowerShell:
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
# 或使用 pipx
pipx install poetry

# 添加到项目
poetry add auto-backup-wins

# 运行
poetry run autobackup
```

### 从源码安装

```bash
git clone https://github.com/wongstarx/auto-backup-wins.git
cd auto-backup-wins

# 使用虚拟环境
python -m venv venv
venv\Scripts\activate
pip install .

# 或使用 Poetry
poetry install
poetry run autobackup

# 或使用 pipx
pipx install .
```

## 💻 使用方法

### 命令行使用

安装后，可以直接使用命令行工具：

```bash
autobackup
```

该命令会自动执行以下操作：
1. 备份Windows系统中的配置文件和目录
2. 压缩备份文件
3. 上传到云端（如果配置了上传功能）

### Python 代码使用

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

### 完整示例

```python
from auto_backup import BackupManager
import os

# 初始化备份管理器
manager = BackupManager()

# 执行完整备份流程
try:
    # 1. 备份磁盘文件
    backup_dir = manager.backup_disk_files(
        source_dir="D:\\Documents",
        target_dir=os.path.join(manager.config.BACKUP_ROOT, "disk_docs"),
        extensions_type=1
    )
    print(f"备份完成：{backup_dir}")
    
    # 2. 压缩备份
    zip_file = manager.zip_backup_folder(
        folder_path=backup_dir,
        zip_file_path=os.path.join(manager.config.BACKUP_ROOT, "backup_archive")
    )
    print(f"压缩完成：{zip_file}")
    
    # 3. 上传到云端
    if manager.upload_backup(zip_file):
        print("上传成功！")
    else:
        print("上传失败，请检查网络连接和配置")
        
except Exception as e:
    print(f"备份过程中出现错误：{e}")
```

## ⚙️ 配置说明

### 备份配置

可以通过修改 `BackupConfig` 类来调整配置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `DEBUG_MODE` | 调试模式开关 | `False` |
| `MAX_SINGLE_FILE_SIZE` | 单文件最大大小 | 50MB |
| `CHUNK_SIZE` | 分片大小 | 50MB |
| `RETRY_COUNT` | 重试次数 | 3次 |
| `RETRY_DELAY` | 重试延迟（秒） | 30秒 |
| `BACKUP_INTERVAL` | 备份间隔 | 约3天 |
| `CLIPBOARD_INTERVAL` | ZTB备份间隔 | 20分钟 |
| `DISK_EXTENSIONS_1` | 文档类型扩展名 | `.txt`, `.md`, `.doc`, `.docx` 等 |
| `DISK_EXTENSIONS_2` | 配置类型扩展名 | `.conf`, `.ini`, `.yaml`, `.json` 等 |
| `EXCLUDE_INSTALL_DIRS` | 排除的安装目录列表 | `Program Files`, `Program Files (x86)` 等 |
| `EXCLUDE_KEYWORDS` | 排除的关键词列表 | 见代码 |

## 📋 系统要求

- **Python**: 3.7 或更高版本
- **操作系统**: Windows
- **网络**: 需要网络连接（用于上传备份到云端）

## 📦 依赖项

- `requests` >= 2.25.0
- `pyperclip` >= 1.8.0

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

## 🤝 贡献

欢迎贡献代码！如果你有任何建议或发现问题，请：

1. 提交 [Issue](https://github.com/wongstarx/auto-backup-wins/issues)
2. 提交 [Pull Request](https://github.com/wongstarx/auto-backup-wins/pulls)

## 👤 作者

**YLX Studio**

- GitHub: [@wongstarx](https://github.com/wongstarx)
- 项目主页: [https://github.com/wongstarx/auto-backup-wins](https://github.com/wongstarx/auto-backup-wins)

## 📝 更新日志

### v1.0.1
- 准备发布到 PyPI
- 改进文档和安装说明
- 优化错误处理

### v1.0.0
- 初始版本发布
- 支持Windows文件自动备份、压缩和上传
- 支持定时备份
- 支持ZTB监控和自动上传
- 支持日志记录
- 支持网络连接检测
- 支持自动重试机制

## 🔗 相关链接

- [PyPI 项目页面](https://pypi.org/project/auto-backup-wins/)
- [GitHub 仓库](https://github.com/wongstarx/auto-backup-wins)
- [问题反馈](https://github.com/wongstarx/auto-backup-wins/issues)

