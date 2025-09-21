"""进度监控器"""
import time
from config import Config

class ProgressMonitor:
    def __init__(self, config: Config):
        self.config = config
    
    def run_monitoring_loop(self, interval: int):
        """运行监控循环（简化版本）"""
        while True:
            print("📊 监控中...")
            time.sleep(interval)