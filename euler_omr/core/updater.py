import requests
from PySide6.QtCore import QObject, Signal, QThreadPool
from euler_omr.constants import ORG_DOMAIN, APP_VERSION
from euler_omr.workers.base_worker import BaseWorker

class CheckUpdateWorker(BaseWorker):
    def run(self):
        try:
            url = f"https://api.github.com/repos/MustafaMahmoud-ILE/EulerOMR/releases/latest"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            latest_version = data.get("tag_name", "").lstrip("v")
            release_notes = data.get("body", "No release notes provided.")
            
            # Find the exe asset
            download_url = None
            for asset in data.get("assets", []):
                if asset.get("name", "").endswith(".exe"):
                    download_url = asset.get("browser_download_url")
                    break
                    
            if latest_version and download_url:
                # Compare versions (simple string compare works for semantic versioning assuming same parts length)
                # For robust comparison:
                def v_to_tuple(v):
                    return tuple(map(int, v.split('.')))
                
            def safe_emit(signal, *args):
                try:
                    signal.emit(*args)
                except (RuntimeError, ReferenceError):
                    pass

            if latest_version and download_url:
                try:
                    current = v_to_tuple(APP_VERSION)
                    latest = v_to_tuple(latest_version)
                    if latest > current:
                        safe_emit(self.signals.result, {
                            "version": latest_version,
                            "release_notes": release_notes,
                            "download_url": download_url
                        })
                        safe_emit(self.signals.finished)
                        return
                except Exception:
                    pass 
                    
            safe_emit(self.signals.result, None)
            safe_emit(self.signals.finished)
        except Exception as e:
            try:
                self.signals.error.emit(str(e))
            except (RuntimeError, ReferenceError):
                pass

class Updater(QObject):
    update_available = Signal(dict)
    
    def check_for_updates(self):
        worker = CheckUpdateWorker()
        worker.signals.result.connect(self._on_check_result)
        QThreadPool.globalInstance().start(worker)
        
    def _on_check_result(self, result):
        if result:
            self.update_available.emit(result)
