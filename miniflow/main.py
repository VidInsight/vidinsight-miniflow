#!/usr/bin/env python3
"""
Miniflow Main Application Module

Bu modül Miniflow uygulamasının ana entry point'ini içerir:
- MiniflowCore: Core component management ve business logic
- MiniflowCLI: Command-line interface handling
- Main function: Application entry point
"""

import argparse
import sys
import threading
import time
import signal
from pathlib import Path
from typing import Optional, Dict, Any

# ------------------------------------------------------------
# Logger Setup - İlk başta çağır/çalıştır
# ------------------------------------------------------------
from .logger_config import setup_logging
setup_logging()

import logging
logger = logging.getLogger("miniflow.main")

# ------------------------------------------------------------
# Miniflow Components Import
# ------------------------------------------------------------
from . import workflow_manager
from .parallelism_engine import Manager
from .scheduler.input_monitor import MiniflowInputMonitor
from .scheduler.output_monitor import MiniflowOutputMonitor
from .database import init_database, list_workflows, get_workflow
from .database.functions.workflow_orchestration import get_execution_status_summary


class MiniflowCore:
    """
    Amaç: Miniflow core business logic ve component management
    Döner: Core operations için MiniflowCore instance'ı
    
    Bu sınıf sadece core işlemleri yönetir:
    - Component lifecycle management
    - Database operations
    - Workflow operations
    """
    
    def __init__(self, db_path: str = "miniflow.db"):
        """
        Amaç: MiniflowCore instance'ını başlatır
        Döner: Yok (constructor)
        """
        logger.debug("MiniflowCore kuruluyor . . .")
        
        # ------------------------------------------------------------
        # Core Parametreler
        # ------------------------------------------------------------
        self.db_path = db_path
        self.running = False
        
        # ------------------------------------------------------------
        # Component References - Direct Management
        # ------------------------------------------------------------
        self.manager: Optional[Manager] = None
        self.input_monitor: Optional[MiniflowInputMonitor] = None
        self.output_monitor: Optional[MiniflowOutputMonitor] = None
        self.scheduler_thread: Optional[threading.Thread] = None
        
        # ------------------------------------------------------------
        # Signal Handlers Setup
        # ------------------------------------------------------------
        self.__setup_signal_handlers()
        
        # ------------------------------------------------------------
        # Database Initialization
        # ------------------------------------------------------------
        self.__init_database()
        
        logger.debug("MiniflowCore başarıyla kuruldu")
    
    def __setup_signal_handlers(self):
        """
        Amaç: Signal handler'ları ayarlar (Ctrl+C için)
        Döner: Yok
        """
        logger.debug("Signal handlers kuruluyor")
        signal.signal(signal.SIGINT, self.__signal_handler)
        signal.signal(signal.SIGTERM, self.__signal_handler)
    
    def __signal_handler(self, signum, frame):
        """
        Amaç: Signal handler - temiz çıkış sağlar
        Döner: Yok
        """
        logger.info("Çıkış sinyali alındı - sistem temizleniyor")
        self.stop_scheduler()
        sys.exit(0)
    
    def __init_database(self):
        """
        Amaç: Database'i başlatır ve bağlantı kontrolü yapar
        Döner: Yok
        """
        logger.info(f"Database başlatılıyor - path: {self.db_path}")
        
        try:
            init_database(self.db_path)
            logger.info(f"Database başarıyla başlatıldı: {self.db_path}")
        except Exception as e:
            logger.error(f"Database başlatma hatası: {e}")
            raise
    
    def start_scheduler(self, background: bool = True) -> bool:
        """
        Amaç: Scheduler bileşenlerini başlatır
        Döner: Başarı durumu (bool)
        """
        logger.info(f"Scheduler başlatılıyor - background: {background}")
        
        if self.running:
            logger.warning("Scheduler zaten çalışıyor")
            return True
        
        try:
            # ------------------------------------------------------------
            # 1. Manager Başlatma
            # ------------------------------------------------------------
            if not self.__start_manager():
                return False
            
            # ------------------------------------------------------------
            # 2. Input Monitor Başlatma
            # ------------------------------------------------------------
            if not self.__start_input_monitor():
                self.__cleanup_on_error()
                return False
            
            # ------------------------------------------------------------
            # 3. Output Monitor Başlatma
            # ------------------------------------------------------------
            if not self.__start_output_monitor():
                self.__cleanup_on_error()
                return False
            
            # ------------------------------------------------------------
            # 4. Scheduler Loop Başlatma
            # ------------------------------------------------------------
            self.running = True
            logger.info("Scheduler bileşenleri başarıyla başlatıldı")
            
            if background:
                return self.__start_background_loop()
            else:
                return self.__start_foreground_loop()
                
        except Exception as e:
            logger.error(f"Scheduler başlatma hatası: {e}")
            self.stop_scheduler()
            return False
    
    def __start_manager(self) -> bool:
        """
        Amaç: Parallelism Engine Manager'ı başlatır
        Döner: Başarı durumu (bool)
        """
        logger.debug("Parallelism engine manager başlatılıyor")
        self.manager = Manager()
        self.manager.start()
        return True
    
    def __start_input_monitor(self) -> bool:
        """
        Amaç: Input Monitor'u başlatır
        Döner: Başarı durumu (bool)
        """
        logger.debug("Input monitor başlatılıyor")
        self.input_monitor = MiniflowInputMonitor(
            db_path=self.db_path,
            polling_interval=0.1,  # Fast polling
            manager=self.manager,
            batch_size=25,
            worker_threads=4
        )
        
        if not self.input_monitor.start():
            logger.error("Input monitor başlatılamadı")
            return False
        
        return True
    
    def __start_output_monitor(self) -> bool:
        """
        Amaç: Output Monitor'u başlatır
        Döner: Başarı durumu (bool)
        """
        logger.debug("Output monitor başlatılıyor")
        self.output_monitor = MiniflowOutputMonitor(
            db_path=self.db_path,
            polling_interval=0.5,  # Medium polling
            manager=self.manager,
            batch_size=25,
            worker_threads=4
        )
        
        if not self.output_monitor.start():
            logger.error("Output monitor başlatılamadı")
            return False
        
        return True
    
    def __start_background_loop(self) -> bool:
        """
        Amaç: Background thread'de scheduler loop'u başlatır
        Döner: Başarı durumu (bool)
        """
        self.scheduler_thread = threading.Thread(
            target=self.__scheduler_loop,
            daemon=True
        )
        self.scheduler_thread.start()
        logger.info("Scheduler background'da başlatıldı")
        
        # Background mode'da kısa süre bekleyip kontrol et
        time.sleep(2)
        return self.running
    
    def __start_foreground_loop(self) -> bool:
        """
        Amaç: Foreground'da scheduler loop'u başlatır
        Döner: Başarı durumu (bool)
        """
        logger.info("Scheduler foreground'da başlatılıyor")
        self.__scheduler_loop()
        return True
    
    def __scheduler_loop(self):
        """
        Amaç: Scheduler ana döngüsü - component'leri monitor eder
        Döner: Yok
        """
        logger.info("Scheduler ana döngüsü başlatıldı")
        
        try:
            # Başlatma kontrolü
            if self.is_running():
                logger.info("Scheduler başarıyla başlatıldı")
            else:
                logger.warning("Scheduler bileşenleri henüz tam aktif değil")
            
            # Ana bekleme döngüsü
            logger.debug("Scheduler bekleme döngüsüne giriliyor")
            while self.running and self.is_running():
                time.sleep(1)  # 1 saniye bekle
                
        except Exception as e:
            logger.error(f"Scheduler döngü hatası: {e}")
        finally:
            logger.info("Scheduler döngüsü sonlandırıldı")
    
    def __cleanup_on_error(self):
        """
        Amaç: Başlatma hatası durumunda cleanup yapar
        Döner: Yok
        """
        logger.debug("Başlatma hatası - cleanup yapılıyor")
        
        if self.input_monitor:
            self.input_monitor.stop()
            
        if self.manager:
            self.manager.shutdown()
    
    def stop_scheduler(self):
        """
        Amaç: Scheduler bileşenlerini güvenli şekilde durdurur
        Döner: Yok
        """
        logger.info("Scheduler bileşenleri durduruluyor")
        self.running = False
        
        # ------------------------------------------------------------
        # Sequential Shutdown - Output Monitor Önce
        # ------------------------------------------------------------
        if self.output_monitor:
            try:
                logger.debug("Output monitor durduruluyor")
                self.output_monitor.stop()
                self.output_monitor = None
            except Exception as e:
                logger.warning(f"Output monitor durdurma hatası: {e}")
        
        # ------------------------------------------------------------
        # Input Monitor Sonra
        # ------------------------------------------------------------
        if self.input_monitor:
            try:
                logger.debug("Input monitor durduruluyor")
                self.input_monitor.stop()
                self.input_monitor = None
            except Exception as e:
                logger.warning(f"Input monitor durdurma hatası: {e}")
        
        # ------------------------------------------------------------
        # Manager En Son
        # ------------------------------------------------------------
        if self.manager:
            try:
                logger.debug("Parallelism engine manager kapatılıyor")
                self.manager.shutdown()
                self.manager = None
            except Exception as e:
                logger.warning(f"Manager shutdown hatası: {e}")
        
        # ------------------------------------------------------------
        # Thread Cleanup
        # ------------------------------------------------------------
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
            self.scheduler_thread = None
        
        logger.info("Scheduler bileşenleri başarıyla durduruldu")
    
    def is_running(self) -> bool:
        """
        Amaç: Scheduler bileşenlerinin çalışma durumunu kontrol eder
        Döner: Çalışma durumu (bool)
        """
        return (self.running and 
                self.manager and 
                self.input_monitor and self.input_monitor.is_running() and
                self.output_monitor and self.output_monitor.is_running())
    
    def load_workflow(self, filepath: str) -> Dict[str, Any]:
        """
        Amaç: Workflow dosyasını database'e yükler
        Döner: Yüklenen workflow bilgileri (dict)
        """
        logger.info(f"Workflow yükleme başlatılıyor: {filepath}")
        
        # ------------------------------------------------------------
        # 1. Dosya Kontrolü
        # ------------------------------------------------------------
        if not Path(filepath).exists():
            error_msg = f"Workflow dosyası bulunamadı: {filepath}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        logger.debug(f"Workflow dosyası mevcut: {filepath}")
        
        # ------------------------------------------------------------
        # 2. Workflow Yükleme
        # ------------------------------------------------------------
        load_result = workflow_manager.load_workflow_from_file(self.db_path, filepath)
        
        if not load_result.get('success'):
            error_msg = f"Workflow yükleme başarısız: {load_result}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # ------------------------------------------------------------
        # 3. Sonuç Döndürme
        # ------------------------------------------------------------
        workflow_id = load_result.get('workflow_id')
        workflow_name = load_result.get('workflow_name', 'N/A')
        
        logger.info(f"Workflow başarıyla yüklendi - ID: {workflow_id}, İsim: {workflow_name}")
        
        return {
            'workflow_id': workflow_id,
            'info': load_result,
            'status': 'loaded'
        }
    
    def trigger_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Amaç: Workflow'u tetikler ve execution başlatır
        Döner: Execution bilgileri (dict)
        """
        logger.info(f"Workflow tetikleme başlatılıyor - workflow_id: {workflow_id}")
        
        # ------------------------------------------------------------
        # 1. Workflow Tetikleme
        # ------------------------------------------------------------
        trigger_result = workflow_manager.trigger_workflow_manually(self.db_path, workflow_id)
        
        if not trigger_result.get('success'):
            error_msg = f"Workflow tetikleme başarısız: {trigger_result}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # ------------------------------------------------------------
        # 2. Sonuç Döndürme
        # ------------------------------------------------------------
        execution_id = trigger_result.get('execution_id')
        
        logger.info(f"Workflow başarıyla tetiklendi - execution_id: {execution_id}")
        
        return {
            'execution_id': execution_id,
            'info': trigger_result,
            'status': 'triggered'
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Amaç: System durumunu toplar ve döndürür
        Döner: System durum bilgileri (dict)
        """
        logger.info("System durumu sorgulanıyor")
        
        # ------------------------------------------------------------
        # 1. Scheduler Component Status
        # ------------------------------------------------------------
        scheduler_active = self.running and self.is_running()
        
        component_status = {
            'input_monitor': "Aktif" if self.input_monitor and self.input_monitor.is_running() else "Pasif",
            'output_monitor': "Aktif" if self.output_monitor and self.output_monitor.is_running() else "Pasif",
            'execution_engine': "Aktif" if self.manager else "Pasif"
        }
        
        # ------------------------------------------------------------
        # 2. Workflow Bilgileri
        # ------------------------------------------------------------
        try:
            workflows_result = list_workflows(self.db_path)
            workflows = workflows_result.data if workflows_result.success else []
        except Exception as e:
            logger.error(f"Workflow bilgileri alınamadı: {e}")
            workflows = []
        
        # ------------------------------------------------------------
        # 3. Status Döndürme
        # ------------------------------------------------------------
        return {
            'scheduler_active': scheduler_active,
            'components': component_status,
            'workflows': workflows,
            'db_path': self.db_path
        }


class MiniflowCLI:
    """
    Amaç: Command-line interface handling
    Döner: CLI operations için MiniflowCLI instance'ı
    
    Bu sınıf sadece CLI işlemleri yönetir:
    - Argument parsing
    - User interaction
    - Output formatting
    """
    
    def __init__(self):
        """
        Amaç: MiniflowCLI instance'ını başlatır
        Döner: Yok (constructor)
        """
        logger.debug("MiniflowCLI kuruluyor . . .")
        self.core = MiniflowCore()
        logger.debug("MiniflowCLI başarıyla kuruldu")
    
    def handle_start_command(self, background: bool = False):
        """
        Amaç: Start komutunu işler
        Döner: Yok
        """
        logger.info(f"Start komutu - background: {background}")
        
        print("🚀 Scheduler başlatılıyor...")
        success = self.core.start_scheduler(background=background)
        
        if success:
            print("✅ Scheduler başarıyla başlatıldı")
            
            # Foreground mode'da bekleme döngüsü
            if not background:
                try:
                    while self.core.running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n🛑 Durduruldu")
        else:
            print("❌ Scheduler başlatılamadı")
            sys.exit(1)
    
    def handle_load_command(self, filepath: str):
        """
        Amaç: Load komutunu işler
        Döner: Yok
        """
        logger.info(f"Load komutu - dosya: {filepath}")
        
        try:
            print(f"📂 Workflow yükleniyor: {filepath}")
            result = self.core.load_workflow(filepath)
            
            workflow_info = result['info']
            print(f"✅ Workflow başarıyla yüklendi:")
            print(f"   ID: {result['workflow_id']}")
            print(f"   İsim: {workflow_info.get('workflow_name', 'N/A')}")
            print(f"   Nodes: {workflow_info.get('nodes_created', 0)}, Edges: {workflow_info.get('edges_created', 0)}")
            
        except Exception as e:
            print(f"❌ Workflow yükleme hatası: {e}")
            logger.error(f"Load komutu hatası: {e}")
            sys.exit(1)
    
    def handle_trigger_command(self, workflow_id: str):
        """
        Amaç: Trigger komutunu işler
        Döner: Yok
        """
        logger.info(f"Trigger komutu - workflow_id: {workflow_id}")
        
        try:
            print(f"🔥 Workflow tetikleniyor: {workflow_id}")
            result = self.core.trigger_workflow(workflow_id)
            
            trigger_info = result['info']
            print(f"✅ Workflow başarıyla tetiklendi:")
            print(f"   Execution ID: {result['execution_id']}")
            print(f"   Oluşturulan tasklar: {trigger_info.get('created_tasks', 0)}")
            print(f"   Hazır tasklar: {trigger_info.get('ready_tasks', 0)}")
            
        except Exception as e:
            print(f"❌ Workflow tetikleme hatası: {e}")
            logger.error(f"Trigger komutu hatası: {e}")
            sys.exit(1)
    
    def handle_status_command(self):
        """
        Amaç: Status komutunu işler
        Döner: Yok
        """
        logger.info("Status komutu")
        
        try:
            status = self.core.get_system_status()
            
            print("\n📊 Miniflow System Durumu")
            print("=" * 50)
            
            # Scheduler durumu
            if status['scheduler_active']:
                print("🚀 Scheduler: Aktif")
                components = status['components']
                print(f"   Input Monitor: {components['input_monitor']}")
                print(f"   Output Monitor: {components['output_monitor']}")
                print(f"   Execution Engine: {components['execution_engine']}")
            else:
                print("🛑 Scheduler: Pasif")
            
            # Workflow bilgileri
            workflows = status['workflows']
            print(f"📋 Toplam Workflow: {len(workflows)}")
            
            if workflows:
                print("\n📝 Workflows:")
                for wf in workflows[:5]:  # İlk 5'ini göster
                    print(f"   • {wf['id']}: {wf['name']}")
                if len(workflows) > 5:
                    print(f"   ... ve {len(workflows) - 5} tane daha")
            
            print()
            
        except Exception as e:
            print(f"❌ Status bilgileri alınamadı: {e}")
            logger.error(f"Status komutu hatası: {e}")
    
    def handle_interactive_command(self):
        """
        Amaç: Interactive komutunu işler
        Döner: Yok
        """
        logger.info("Interactive komutu")
        
        # Background'da scheduler başlat
        self.core.start_scheduler(background=True)
        
        print("\n🎯 Miniflow İnteraktif Mod")
        print("Komutlar: load <file>, trigger <id>, status, start, stop, quit")
        print("=" * 50)
        
        while True:
            try:
                command = input("\nminiflow> ").strip().lower()
                
                if not command:
                    continue
                
                parts = command.split()
                cmd = parts[0]
                
                logger.debug(f"İnteraktif komut alındı: {cmd}")
                
                if cmd in ['quit', 'exit']:
                    print("👋 Çıkılıyor...")
                    break
                
                elif cmd == 'load':
                    if len(parts) < 2:
                        print("❌ Kullanım: load <filepath>")
                        continue
                    try:
                        self.handle_load_command(parts[1])
                    except Exception as e:
                        print(f"❌ Hata: {e}")
                
                elif cmd == 'trigger':
                    if len(parts) < 2:
                        print("❌ Kullanım: trigger <workflow_id>")
                        continue
                    try:
                        self.handle_trigger_command(parts[1])
                    except Exception as e:
                        print(f"❌ Hata: {e}")
                
                elif cmd == 'status':
                    self.handle_status_command()
                
                elif cmd == 'start':
                    if not self.core.running:
                        self.core.start_scheduler(background=True)
                        print("🚀 Scheduler başlatıldı")
                    else:
                        print("⚠️ Scheduler zaten çalışıyor")
                
                elif cmd == 'stop':
                    if self.core.running:
                        self.core.stop_scheduler()
                        print("🛑 Scheduler durduruldu")
                    else:
                        print("⚠️ Scheduler zaten durdurulmuş")
                
                elif cmd == 'help':
                    print("Komutlar:")
                    print("  load <file>     - Workflow dosyasını yükle")
                    print("  trigger <id>    - Workflow'u tetikle")
                    print("  status          - System durumunu göster")
                    print("  start           - Scheduler'ı başlat")
                    print("  stop            - Scheduler'ı durdur")
                    print("  quit/exit       - Çıkış")
                
                else:
                    print(f"❌ Bilinmeyen komut: {cmd}")
                    print("Yardım için 'help' yazın")
            
            except KeyboardInterrupt:
                print("\n👋 Çıkılıyor...")
                break
            except Exception as e:
                print(f"❌ Beklenmeyen hata: {e}")


def main():
    """
    Amaç: Ana entry point - CLI argument'ları parse eder ve uygun handler'ı çağırır
    Döner: Yok
    """
    logger.info("Miniflow uygulaması başlatılıyor")
    
    # ------------------------------------------------------------
    # CLI Argument Parser Setup
    # ------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description='Miniflow - Workflow Management System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python -m miniflow start                    # Scheduler'ı başlat
  python -m miniflow load workflow.json       # Workflow yükle
  python -m miniflow trigger <workflow_id>    # Workflow tetikle
  python -m miniflow status                   # Durum göster
  python -m miniflow interactive              # İnteraktif mod
        """
    )
    
    parser.add_argument('command', 
                       choices=['start', 'load', 'trigger', 'status', 'interactive'],
                       help='Çalıştırılacak komut')
    
    parser.add_argument('argument', nargs='?',
                       help='Komuta ait argüman (dosya yolu veya workflow ID)')
    
    parser.add_argument('--background', action='store_true',
                       help='Scheduler\'ı background\'da çalıştır')
    
    args = parser.parse_args()
    
    logger.info(f"Komut alındı: {args.command} - argüman: {args.argument}")
    
    # ------------------------------------------------------------
    # CLI Handler Creation ve Command Dispatch
    # ------------------------------------------------------------
    cli = MiniflowCLI()
    
    try:
        if args.command == 'start':
            cli.handle_start_command(background=args.background)
        
        elif args.command == 'load':
            if not args.argument:
                print("❌ Workflow dosya yolu gerekli")
                sys.exit(1)
            cli.handle_load_command(args.argument)
        
        elif args.command == 'trigger':
            if not args.argument:
                print("❌ Workflow ID gerekli")
                sys.exit(1)
            cli.handle_trigger_command(args.argument)
        
        elif args.command == 'status':
            cli.handle_status_command()
        
        elif args.command == 'interactive':
            cli.handle_interactive_command()
    
    except Exception as e:
        print(f"❌ Uygulama hatası: {e}")
        logger.error(f"Uygulama hatası: {e}")
        sys.exit(1)
    
    finally:
        logger.info("Main fonksiyon sonlandırılıyor")
        cli.core.stop_scheduler()


if __name__ == '__main__':
    main()
