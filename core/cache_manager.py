#!/usr/bin/env python3
"""
智能缓存管理器 - 提升重复文件处理速度
"""

import os
import json
import time
import hashlib
import sqlite3
from typing import Optional, Dict, Any, Tuple
from pathlib import Path


class CacheManager:
    """OCR结果缓存管理器"""
    
    def __init__(self, cache_dir: str = "cache", max_cache_size: int = 1000, 
                 max_cache_days: int = 30):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录
            max_cache_size: 最大缓存条目数
            max_cache_days: 缓存有效期(天)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.db_path = self.cache_dir / "ocr_cache.db"
        self.max_cache_size = max_cache_size
        self.max_cache_days = max_cache_days
        
        # 统计信息
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'cache_writes': 0,
            'cache_errors': 0
        }
        
        # 初始化数据库
        self._init_database()
    
    def _init_database(self):
        """初始化缓存数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS ocr_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_hash TEXT UNIQUE NOT NULL,
                        file_size INTEGER NOT NULL,
                        file_mtime REAL NOT NULL,
                        ocr_results TEXT NOT NULL,
                        processing_time REAL NOT NULL,
                        strategy_used TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        accessed_at REAL NOT NULL,
                        access_count INTEGER DEFAULT 1
                    )
                ''')
                
                # 创建索引
                conn.execute('CREATE INDEX IF NOT EXISTS idx_file_hash ON ocr_cache(file_hash)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_accessed_at ON ocr_cache(accessed_at)')
                
                conn.commit()
                print("缓存数据库初始化完成")
                
        except Exception as e:
            print(f"缓存数据库初始化失败: {e}")
    
    def _calculate_file_hash(self, file_path: str) -> Optional[str]:
        """计算文件哈希值"""
        try:
            file_size = os.path.getsize(file_path)
            
            # 对于大文件，使用快速哈希策略
            if file_size > 10 * 1024 * 1024:  # 10MB
                return self._fast_hash(file_path, file_size)
            else:
                return self._full_hash(file_path)
                
        except Exception as e:
            print(f"计算文件哈希失败: {e}")
            return None
    
    def _fast_hash(self, file_path: str, file_size: int) -> str:
        """大文件快速哈希：文件头+尾+大小"""
        try:
            hasher = hashlib.md5()
            
            with open(file_path, 'rb') as f:
                # 读取文件头 (前8KB)
                head = f.read(8192)
                hasher.update(head)
                
                # 读取文件尾 (后8KB)
                if file_size > 16384:
                    f.seek(-8192, 2)
                    tail = f.read(8192)
                    hasher.update(tail)
                
                # 添加文件大小
                hasher.update(str(file_size).encode())
            
            return hasher.hexdigest()
            
        except Exception as e:
            print(f"快速哈希计算失败: {e}")
            return None
    
    def _full_hash(self, file_path: str) -> str:
        """小文件完整哈希"""
        try:
            hasher = hashlib.md5()
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            
            return hasher.hexdigest()
            
        except Exception as e:
            print(f"完整哈希计算失败: {e}")
            return None
    
    def get_cached_result(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取缓存的OCR结果"""
        self.stats['total_requests'] += 1
        
        try:
            # 计算文件哈希
            file_hash = self._calculate_file_hash(file_path)
            if not file_hash:
                self.stats['cache_errors'] += 1
                return None
            
            # 获取文件信息
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            file_mtime = file_stat.st_mtime
            
            # 查询缓存
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT ocr_results, processing_time, strategy_used, created_at
                    FROM ocr_cache 
                    WHERE file_hash = ? AND file_size = ? AND file_mtime = ?
                ''', (file_hash, file_size, file_mtime))
                
                row = cursor.fetchone()
                
                if row:
                    # 检查缓存是否过期
                    created_at = row[3]
                    if time.time() - created_at > self.max_cache_days * 24 * 3600:
                        # 缓存过期，删除
                        conn.execute('DELETE FROM ocr_cache WHERE file_hash = ?', (file_hash,))
                        conn.commit()
                        self.stats['cache_misses'] += 1
                        return None
                    
                    # 更新访问时间和次数
                    conn.execute('''
                        UPDATE ocr_cache 
                        SET accessed_at = ?, access_count = access_count + 1
                        WHERE file_hash = ?
                    ''', (time.time(), file_hash))
                    conn.commit()
                    
                    # 解析结果
                    ocr_results = json.loads(row[0])
                    processing_time = row[1]
                    strategy_used = row[2]
                    
                    self.stats['cache_hits'] += 1
                    
                    print(f"✅ 缓存命中: {os.path.basename(file_path)} (策略: {strategy_used}, 原耗时: {processing_time:.2f}秒)")
                    
                    return {
                        'ocr_results': ocr_results,
                        'processing_time': processing_time,
                        'strategy_used': strategy_used,
                        'from_cache': True
                    }
                else:
                    self.stats['cache_misses'] += 1
                    return None
                    
        except Exception as e:
            print(f"缓存查询失败: {e}")
            self.stats['cache_errors'] += 1
            return None
    
    def save_result(self, file_path: str, ocr_results: list, 
                   processing_time: float, strategy_used: str):
        """保存OCR结果到缓存"""
        try:
            # 计算文件哈希
            file_hash = self._calculate_file_hash(file_path)
            if not file_hash:
                return
            
            # 获取文件信息
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            file_mtime = file_stat.st_mtime
            
            # 序列化结果
            results_json = json.dumps(ocr_results, ensure_ascii=False)
            current_time = time.time()
            
            # 保存到数据库
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO ocr_cache 
                    (file_hash, file_size, file_mtime, ocr_results, processing_time, 
                     strategy_used, created_at, accessed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (file_hash, file_size, file_mtime, results_json, processing_time,
                      strategy_used, current_time, current_time))
                
                conn.commit()
            
            self.stats['cache_writes'] += 1
            
            # 清理过期缓存
            self._cleanup_cache()
            
        except Exception as e:
            print(f"缓存保存失败: {e}")
            self.stats['cache_errors'] += 1
    
    def _cleanup_cache(self):
        """清理过期和过多的缓存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                current_time = time.time()
                expire_time = current_time - self.max_cache_days * 24 * 3600
                
                # 删除过期缓存
                conn.execute('DELETE FROM ocr_cache WHERE created_at < ?', (expire_time,))
                
                # 检查缓存数量
                cursor = conn.execute('SELECT COUNT(*) FROM ocr_cache')
                cache_count = cursor.fetchone()[0]
                
                if cache_count > self.max_cache_size:
                    # 删除最少使用的缓存
                    excess_count = cache_count - self.max_cache_size
                    conn.execute('''
                        DELETE FROM ocr_cache 
                        WHERE id IN (
                            SELECT id FROM ocr_cache 
                            ORDER BY accessed_at ASC 
                            LIMIT ?
                        )
                    ''', (excess_count,))
                
                conn.commit()
                
        except Exception as e:
            print(f"缓存清理失败: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT COUNT(*) FROM ocr_cache')
                cache_count = cursor.fetchone()[0]
                
                cursor = conn.execute('SELECT SUM(LENGTH(ocr_results)) FROM ocr_cache')
                cache_size = cursor.fetchone()[0] or 0
        except:
            cache_count = 0
            cache_size = 0
        
        total_requests = self.stats['total_requests']
        cache_hits = self.stats['cache_hits']
        
        hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_requests': total_requests,
            'cache_hits': cache_hits,
            'cache_misses': self.stats['cache_misses'],
            'cache_writes': self.stats['cache_writes'],
            'cache_errors': self.stats['cache_errors'],
            'hit_rate': f"{hit_rate:.1f}%",
            'cache_count': cache_count,
            'cache_size_mb': f"{cache_size / 1024 / 1024:.2f}MB"
        }
    
    def clear_cache(self):
        """清空所有缓存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM ocr_cache')
                conn.commit()
            
            print("缓存已清空")
            
        except Exception as e:
            print(f"清空缓存失败: {e}")
