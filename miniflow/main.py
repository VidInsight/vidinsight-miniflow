#!/usr/bin/env python3
import argparse
import sys
import threading
import time
import signal
from pathlib import Path
from typing import Optional, Dict, Any

# Logger setup - ilk başta çağır/çalıştır
from .logger_config import setup_logging
setup_logging()

import logging
logger = logging.getLogger("miniflow.main")

# Miniflow components
from . import workflow_manager
from . import scheduler
from .database import init_database, list_workflows, get_workflow
from .database.functions.workflow_orchestration import get_execution_status_summary


class MiniflowApp:
    """
    Ana Miniflow uygulaması
    
    Workflow Manager ve Scheduler'ı koordine eder ve command-line interface sağlar.
    """
    
    def __init__(self):
        self.scheduler_instance: Optional[scheduler.WorkflowScheduler] = None
        self.scheduler_thread: Optional[threading.Thread] = None
        self.running = False
        self.db_path = "miniflow.db"
        self.setup_signal_handlers()
        
        logger.info(f"MiniflowApp başlatılıyor - database: {self.db_path}")
        
        # Database'i başlat
        try:
            init_database(self.db_path)
            print(f"✅ Database başarıyla başlatıldı: {self.db_path}")
            logger.info(f"Database başarıyla başlatıldı: {self.db_path}")
        except Exception as e:
            print(f"❌ Database başlatma hatası: {e}")
            logger.error(f"Database başlatma hatası: {e}")
            sys.exit(1)
    
    def setup_signal_handlers(self):
        """Signal handler'ları ayarla (Ctrl+C için)"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Signal handler - temiz çıkış"""
        print("\n🛑 Çıkış sinyali alındı, sistem temizleniyor...")
        self.stop()
        sys.exit(0)
    
    def start_scheduler(self, background: bool = True):
        """
        Scheduler'ı başlat
        
        Args:
            background: True ise background thread'de çalışır
            
        Returns:
            bool: Başarı durumu
        """
        logger.info(f"Scheduler başlatılıyor - background: {background}")
        
        if self.scheduler_instance is not None:
            print("⚠️ Scheduler zaten çalışıyor")
            logger.warning("Scheduler zaten çalışıyor")
            return True
        
        try:
            # Batch processing ile scheduler oluştur (batch_size=25)
            self.scheduler_instance = scheduler.create_scheduler(self.db_path, batch_size=25)
            logger.debug(f"Scheduler instance oluşturuldu - batch_size: 25")
            self.running = True
            
            if background:
                self.scheduler_thread = threading.Thread(
                    target=self._run_scheduler_loop,
                    daemon=True
                )
                self.scheduler_thread.start()
                print("🚀 Scheduler background'da başlatıldı")
                logger.info("Scheduler background'da başlatıldı")
                
                # Background mode'da kısa bir süre bekleyip kontrolü et
                time.sleep(2)
                return self.running and self.scheduler_instance is not None
            else:
                print("🚀 Scheduler başlatılıyor...")
                logger.info("Scheduler foreground'da başlatılıyor")
                self._run_scheduler_loop()
                return True
                
        except Exception as e:
            print(f"❌ Scheduler başlatma hatası: {e}")
            logger.error(f"Scheduler başlatma hatası: {e}")
            self.running = False
            return False
    
    def _run_scheduler_loop(self):
        """Scheduler ana döngüsü"""
        logger.info("Scheduler ana döngüsü başlatılıyor")
        
        try:
            # Scheduler'ı başlat
            if self.scheduler_instance and not self.scheduler_instance.is_running():
                logger.debug("Scheduler instance başlatılıyor")
                success = self.scheduler_instance.start()
                if not success:
                    print("❌ Scheduler başlatılamadı")
                    logger.error("Scheduler başlatılamadı")
                    return
                
                # Scheduler'ın tam başlaması için kısa bir süre bekle
                time.sleep(1)
                
                # Başlatma durumunu kontrol et
                if self.scheduler_instance.is_running():
                    print("✅ Scheduler başarıyla başlatıldı")
                    logger.info("Scheduler başarıyla başlatıldı")
                else:
                    print("⚠️ Scheduler başlatıldı ama henüz tam aktif değil")
                    logger.warning("Scheduler başlatıldı ama henüz tam aktif değil")
            
            # Scheduler çalışırken bekle
            logger.debug("Scheduler çalışırken bekleme döngüsüne giriliyor")
            while self.running and self.scheduler_instance and self.scheduler_instance.is_running():
                time.sleep(1)  # 1 saniye bekle
                
        except Exception as e:
            print(f"❌ Scheduler döngüsü hatası: {e}")
            logger.error(f"Scheduler döngüsü hatası: {e}")
        finally:
            print("🛑 Scheduler durduruldu")
            logger.info("Scheduler durduruldu")
    
    def stop(self):
        """Scheduler'ı durdur"""
        self.running = False
        if self.scheduler_instance:
            self.scheduler_instance.stop()
            self.scheduler_instance = None
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
            self.scheduler_thread = None
    
    def load_workflow(self, filepath: str) -> Dict[str, Any]:
        """
        Workflow dosyasını yükle
        
        Args:
            filepath: JSON workflow dosyası yolu
            
        Returns:
            Yüklenen workflow bilgileri
        """
        logger.info(f"Workflow yükleme başlatılıyor: {filepath}")
        
        try:
            if not Path(filepath).exists():
                logger.error(f"Workflow dosyası bulunamadı: {filepath}")
                raise FileNotFoundError(f"Workflow dosyası bulunamadı: {filepath}")
            
            logger.debug(f"Workflow dosyası mevcut: {filepath}")
            print(f"📂 Workflow yükleniyor: {filepath}")
            
            # Workflow'u yükle
            load_result = workflow_manager.load_workflow_from_file(self.db_path, filepath)
            
            if load_result.get('success'):
                workflow_id = load_result.get('workflow_id')
                workflow_name = load_result.get('workflow_name', 'N/A')
                nodes_created = load_result.get('nodes_created', 0)
                edges_created = load_result.get('edges_created', 0)
                
                print(f"✅ Workflow başarıyla yüklendi:")
                print(f"   ID: {workflow_id}")
                print(f"   İsim: {workflow_name}")
                print(f"   Nodes: {nodes_created}, Edges: {edges_created}")
                
                logger.info(f"Workflow başarıyla yüklendi - ID: {workflow_id}, İsim: {workflow_name}")
                logger.debug(f"Workflow detayları - Nodes: {nodes_created}, Edges: {edges_created}")
                
                return {
                    'workflow_id': workflow_id,
                    'info': load_result,
                    'status': 'loaded'
                }
            else:
                logger.error(f"Workflow yükleme başarısız: {load_result}")
                raise Exception(f"Workflow yükleme başarısız: {load_result}")
            
        except Exception as e:
            print(f"❌ Workflow yükleme hatası: {e}")
            logger.error(f"Workflow yükleme hatası: {e}")
            raise
    
    def trigger_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Workflow'u tetikle
        
        Args:
            workflow_id: Tetiklenecek workflow ID'si
            
        Returns:
            Execution bilgileri
        """
        logger.info(f"Workflow tetikleme başlatılıyor - workflow_id: {workflow_id}")
        
        try:
            print(f"🔥 Workflow tetikleniyor: {workflow_id}")
            
            # Workflow'u tetikle
            trigger_result = workflow_manager.trigger_workflow_manually(self.db_path, workflow_id)
            
            if trigger_result.get('success'):
                execution_id = trigger_result.get('execution_id')
                created_tasks = trigger_result.get('created_tasks', 0)
                ready_tasks_count = trigger_result.get('ready_tasks', 0)
                
                print(f"✅ Workflow başarıyla tetiklendi:")
                print(f"   Execution ID: {execution_id}")
                print(f"   Oluşturulan tasklar: {created_tasks}")
                print(f"   Hazır tasklar: {ready_tasks_count}")
                
                logger.info(f"Workflow başarıyla tetiklendi - execution_id: {execution_id}")
                logger.debug(f"Trigger sonuçları - tasks: {created_tasks}, ready: {ready_tasks_count}")
                
                return {
                    'execution_id': execution_id,
                    'info': trigger_result,
                    'status': 'triggered'
                }
            else:
                logger.error(f"Workflow tetikleme başarısız: {trigger_result}")
                raise Exception(f"Workflow tetikleme başarısız: {trigger_result}")
            
        except Exception as e:
            print(f"❌ Workflow tetikleme hatası: {e}")
            logger.error(f"Workflow tetikleme hatası: {e}")
            raise
    
    def show_status(self):
        """System durumunu göster"""
        logger.info("System durumu sorgulanıyor")
        
        print("\n📊 Miniflow System Durumu")
        print("=" * 50)
        
        # Scheduler durumu - hem local hem de system-wide kontrol
        scheduler_active = False
        
        # Local instance kontrolü
        if self.scheduler_instance and self.running and self.scheduler_instance.is_running():
            scheduler_active = True
        
        # System-wide process kontrolü (alternatif kontrol)
        import subprocess
        try:
            result = subprocess.run(['pgrep', '-f', 'miniflow.*start'], 
                                 capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                scheduler_active = True
        except:
            pass
        
        if scheduler_active:
            print("🚀 Scheduler: Aktif")
            logger.debug("Scheduler aktif durumda")
            if self.scheduler_instance:
                try:
                    status = self.scheduler_instance.get_status()
                    queue_status = "✅" if status.get('queue_monitor_running') else "❌"
                    result_status = "✅" if status.get('result_monitor_running') else "❌"
                    print(f"   Queue Monitor: {queue_status}")
                    print(f"   Result Monitor: {result_status}")
                    logger.debug(f"Scheduler detayları - Queue: {status.get('queue_monitor_running')}, Result: {status.get('result_monitor_running')}")
                except:
                    print("   (Durum bilgisi alınamadı)")
                    logger.warning("Scheduler durum bilgisi alınamadı")
        else:
            print("🛑 Scheduler: Pasif")
            logger.debug("Scheduler pasif durumda")
        
        # Workflow'lar
        try:
            workflows_result = list_workflows(self.db_path)
            if workflows_result.success:
                workflows = workflows_result.data
                print(f"📋 Toplam Workflow: {len(workflows)}")
                logger.debug(f"Toplam workflow sayısı: {len(workflows)}")
                
                if workflows:
                    print("\n📝 Workflows:")
                    for wf in workflows[:5]:  # İlk 5'ini göster
                        print(f"   • {wf['id']}: {wf['name']}")
                    if len(workflows) > 5:
                        print(f"   ... ve {len(workflows) - 5} tane daha")
            else:
                print(f"❌ Workflow bilgileri alınamadı: {workflows_result.error}")
                logger.error(f"Workflow bilgileri alınamadı: {workflows_result.error}")
        
        except Exception as e:
            print(f"❌ Workflow bilgileri alınamadı: {e}")
            logger.error(f"Workflow bilgileri alınamadı: {e}")
        
        print()
    
    def interactive_mode(self):
        """İnteraktif mod - kullanıcı komutlarını dinle"""
        logger.info("İnteraktif mod başlatılıyor")
        
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
                
                if cmd == 'quit' or cmd == 'exit':
                    print("👋 Çıkılıyor...")
                    logger.info("İnteraktif mod sonlandırılıyor")
                    break
                
                elif cmd == 'load':
                    if len(parts) < 2:
                        print("❌ Kullanım: load <filepath>")
                        continue
                    try:
                        logger.info(f"İnteraktif load komutu: {parts[1]}")
                        self.load_workflow(parts[1])
                    except Exception as e:
                        print(f"❌ Hata: {e}")
                
                elif cmd == 'trigger':
                    if len(parts) < 2:
                        print("❌ Kullanım: trigger <workflow_id>")
                        continue
                    try:
                        workflow_id = parts[1]  # UUID string olarak al
                        logger.info(f"İnteraktif trigger komutu: {workflow_id}")
                        self.trigger_workflow(workflow_id)
                    except Exception as e:
                        print(f"❌ Hata: {e}")
                
                elif cmd == 'status':
                    logger.debug("İnteraktif status komutu")
                    self.show_status()
                
                elif cmd == 'start':
                    if not self.running:
                        logger.info("İnteraktif start komutu")
                        self.start_scheduler(background=True)
                    else:
                        print("⚠️ Scheduler zaten çalışıyor")
                        logger.warning("İnteraktif start komutu - scheduler zaten çalışıyor")
                
                elif cmd == 'stop':
                    if self.running:
                        logger.info("İnteraktif stop komutu")
                        self.stop()
                        print("🛑 Scheduler durduruldu")
                    else:
                        print("⚠️ Scheduler zaten durdurulmuş")
                        logger.warning("İnteraktif stop komutu - scheduler zaten durdurulmuş")
                
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
                    logger.warning(f"İnteraktif mod - bilinmeyen komut: {cmd}")
            
            except KeyboardInterrupt:
                print("\n👋 Çıkılıyor...")
                break
            except Exception as e:
                print(f"❌ Beklenmeyen hata: {e}")


def main():
    """Ana entry point"""
    logger.info("Miniflow uygulaması başlatılıyor")
    
    parser = argparse.ArgumentParser(
        description='Miniflow - Workflow Management System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python -m miniflow start                    # Scheduler'ı başlat
  python -m miniflow load workflow.json       # Workflow yükle
  python -m miniflow trigger 1                # Workflow tetikle
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
    
    # Uygulamayı başlat
    app = MiniflowApp()
    
    try:
        if args.command == 'start':
            logger.info(f"Start komutu - background: {args.background}")
            app.start_scheduler(background=args.background)
            
            # Her iki modda da beklemeye geç (background'da da main process yaşamalı)
            try:
                while app.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Durduruldu")
                logger.info("Start komutu KeyboardInterrupt ile sonlandırıldı")
        
        elif args.command == 'load':
            if not args.argument:
                print("❌ Workflow dosya yolu gerekli")
                logger.error("Load komutu - dosya yolu argümanı eksik")
                sys.exit(1)
            logger.info(f"Load komutu - dosya: {args.argument}")
            app.load_workflow(args.argument)
        
        elif args.command == 'trigger':
            if not args.argument:
                print("❌ Workflow ID gerekli")
                logger.error("Trigger komutu - workflow ID argümanı eksik")
                sys.exit(1)
            try:
                workflow_id = args.argument  # UUID string olarak al
                logger.info(f"Trigger komutu - workflow_id: {workflow_id}")
                app.trigger_workflow(workflow_id)
            except Exception as e:
                print(f"❌ Hata: {e}")
                logger.error(f"Trigger komutu hatası: {e}")
                sys.exit(1)
        
        elif args.command == 'status':
            logger.info("Status komutu")
            app.show_status()
        
        elif args.command == 'interactive':
            logger.info("Interactive komutu")
            app.start_scheduler(background=True)
            app.interactive_mode()
        

    
    except Exception as e:
        print(f"❌ Uygulama hatası: {e}")
        logger.error(f"Uygulama hatası: {e}")
        sys.exit(1)
    
    finally:
        logger.info("Main fonksiyon sonlandırılıyor")
        app.stop()


if __name__ == '__main__':
    main()
