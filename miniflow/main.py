#!/usr/bin/env python3

import argparse
import sys
import threading
import time
import signal
from pathlib import Path
from typing import Optional, Dict, Any

# Miniflow components
from . import workflow_manager
from . import scheduler
# NEW: Database Manager Integration (will be lazy loaded)
# Legacy support
from .database import init_database, list_workflows


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
        
        # Signal handler'ları ayarla (Ctrl+C için)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Database initialization - Legacy for now (Database Manager disabled due to circular imports)
        try:
            init_database(self.db_path)
            print(f"✅ Database başarıyla başlatıldı: {self.db_path}")
            
            # Database Manager placeholder (will be enabled later)
            self.db_manager = None
            self.workflow_service = None
            self.orchestration_service = None
            
        except Exception as e:
            print(f"❌ Database başlatma hatası: {e}")
            sys.exit(1)
    
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
        if self.scheduler_instance is not None:
            print("⚠️ Scheduler zaten çalışıyor")
            return True
        
        try:
            # Batch processing ile scheduler oluştur (batch_size=25)
            self.scheduler_instance = scheduler.create_scheduler(self.db_path, batch_size=25)
            self.running = True
            
            if background:
                self.scheduler_thread = threading.Thread(
                    target=self._run_scheduler_loop,
                    daemon=True
                )
                self.scheduler_thread.start()
                print("🚀 Scheduler background'da başlatıldı")
                
                # Background mode'da kısa bir süre bekleyip kontrolü et
                time.sleep(2)
                return self.running and self.scheduler_instance is not None
            else:
                print("🚀 Scheduler başlatılıyor...")
                self._run_scheduler_loop()
                return True
                
        except Exception as e:
            print(f"❌ Scheduler başlatma hatası: {e}")
            self.running = False
            return False
    
    def _run_scheduler_loop(self):
        """Scheduler ana döngüsü"""
        try:
            # Scheduler'ı başlat
            if self.scheduler_instance and not self.scheduler_instance.is_running():
                success = self.scheduler_instance.start()
                if not success:
                    print("❌ Scheduler başlatılamadı")
                    return
                
                # Scheduler'ın tam başlaması için kısa bir süre bekle
                time.sleep(1)
                
                # Başlatma durumunu kontrol et
                if self.scheduler_instance.is_running():
                    print("✅ Scheduler başarıyla başlatıldı")
                else:
                    print("⚠️ Scheduler başlatıldı ama henüz tam aktif değil")
            
            # Scheduler çalışırken bekle
            while self.running and self.scheduler_instance and self.scheduler_instance.is_running():
                time.sleep(1)  # 1 saniye bekle
                
        except Exception as e:
            print(f"❌ Scheduler döngüsü hatası: {e}")
        finally:
            print("🛑 Scheduler durduruldu")
    
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
        try:
            if not Path(filepath).exists():
                raise FileNotFoundError(f"Workflow dosyası bulunamadı: {filepath}")
            
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
                
                return {
                    'workflow_id': workflow_id,
                    'info': load_result,
                    'status': 'loaded'
                }
            else:
                raise Exception(f"Workflow yükleme başarısız: {load_result}")
            
        except Exception as e:
            print(f"❌ Workflow yükleme hatası: {e}")
            raise
    
    def trigger_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Workflow'u tetikle
        
        Args:
            workflow_id: Tetiklenecek workflow ID'si
            
        Returns:
            Execution bilgileri
        """
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
                
                return {
                    'execution_id': execution_id,
                    'info': trigger_result,
                    'status': 'triggered'
                }
            else:
                raise Exception(f"Workflow tetikleme başarısız: {trigger_result}")
            
        except Exception as e:
            print(f"❌ Workflow tetikleme hatası: {e}")
            raise
    
    def show_status(self):
        """System durumunu göster"""
        print("\n📊 Miniflow System Durumu")
        print("=" * 50)
        
        # Database Manager durumu
        try:
            if hasattr(self, 'db_manager') and self.db_manager:
                health_status = "✅ Sağlıklı" if self.db_manager.is_healthy() else "❌ Sorunlu"
                print(f"💾 Database Manager: {health_status}")
                
                # Workflow istatistikleri - Database Manager ile
                try:
                    workflows = self.workflow_service.workflow_repo.get_all()
                    active_workflows = self.workflow_service.workflow_repo.get_active_workflows()
                    print(f"📋 Toplam Workflow: {len(workflows)}")
                    print(f"🟢 Aktif Workflow: {len(active_workflows)}")
                    
                    if workflows:
                        print("\n📝 Workflows (Database Manager):")
                        for wf in workflows[:5]:  # İlk 5'ini göster
                            print(f"   • {wf.id}: {wf.name} ({wf.status})")
                        if len(workflows) > 5:
                            print(f"   ... ve {len(workflows) - 5} tane daha")
                except Exception as e:
                    print(f"⚠️ Workflow bilgileri alınamadı: {e}")
            else:
                print("⚠️ Database Manager: Başlatılmamış")
        except Exception as e:
            print(f"❌ Database Manager kontrolü başarısız: {e}")
        
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
            if self.scheduler_instance:
                try:
                    # Basit durum kontrolü - monitor'ları ayrı ayrı kontrol et
                    queue_running = self.scheduler_instance.queue_monitor.is_running()
                    result_running = self.scheduler_instance.result_monitor.is_running()
                    queue_status = "✅" if queue_running else "❌"
                    result_status = "✅" if result_running else "❌"
                    print(f"   Queue Monitor: {queue_status}")
                    print(f"   Result Monitor: {result_status}")
                except:
                    print("   (Durum bilgisi alınamadı)")
        else:
            print("🛑 Scheduler: Pasif")
        
        # Legacy workflow kontrolü (fallback)
        if not hasattr(self, 'db_manager') or not self.db_manager:
            try:
                workflows_result = list_workflows(self.db_path)
                if workflows_result.success:
                    workflows = workflows_result.data
                    print(f"📋 Toplam Workflow (Legacy): {len(workflows)}")
                    
                    if workflows:
                        print("\n📝 Workflows (Legacy):")
                        for wf in workflows[:5]:  # İlk 5'ini göster
                            print(f"   • {wf['id']}: {wf['name']}")
                        if len(workflows) > 5:
                            print(f"   ... ve {len(workflows) - 5} tane daha")
                else:
                    print(f"❌ Workflow bilgileri alınamadı: {workflows_result.error}")
            
            except Exception as e:
                print(f"❌ Workflow bilgileri alınamadı: {e}")
        
        print()
    
    def interactive_mode(self):
        """İnteraktif mod - kullanıcı komutlarını dinle"""
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
                
                if cmd == 'quit' or cmd == 'exit':
                    print("👋 Çıkılıyor...")
                    break
                
                elif cmd == 'load':
                    if len(parts) < 2:
                        print("❌ Kullanım: load <filepath>")
                        continue
                    try:
                        self.load_workflow(parts[1])
                    except Exception as e:
                        print(f"❌ Hata: {e}")
                
                elif cmd == 'trigger':
                    if len(parts) < 2:
                        print("❌ Kullanım: trigger <workflow_id>")
                        continue
                    try:
                        workflow_id = parts[1]  # UUID string olarak al
                        self.trigger_workflow(workflow_id)
                    except Exception as e:
                        print(f"❌ Hata: {e}")
                
                elif cmd == 'status':
                    self.show_status()
                
                elif cmd == 'start':
                    if not self.running:
                        self.start_scheduler(background=True)
                    else:
                        print("⚠️ Scheduler zaten çalışıyor")
                
                elif cmd == 'stop':
                    if self.running:
                        self.stop()
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
    """Ana entry point"""
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
    
    # Uygulamayı başlat
    app = MiniflowApp()
    
    try:
        if args.command == 'start':
            app.start_scheduler(background=args.background)
            
            # Her iki modda da beklemeye geç (background'da da main process yaşamalı)
            try:
                while app.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Durduruldu")
        
        elif args.command == 'load':
            if not args.argument:
                print("❌ Workflow dosya yolu gerekli")
                sys.exit(1)
            app.load_workflow(args.argument)
        
        elif args.command == 'trigger':
            if not args.argument:
                print("❌ Workflow ID gerekli")
                sys.exit(1)
            try:
                workflow_id = args.argument  # UUID string olarak al
                app.trigger_workflow(workflow_id)
            except Exception as e:
                print(f"❌ Hata: {e}")
                sys.exit(1)
        
        elif args.command == 'status':
            app.show_status()
        
        elif args.command == 'interactive':
            app.start_scheduler(background=True)
            app.interactive_mode()
        

    
    except Exception as e:
        print(f"❌ Uygulama hatası: {e}")
        sys.exit(1)
    
    finally:
        app.stop()


if __name__ == '__main__':
    main()
