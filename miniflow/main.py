#!/usr/bin/env python3
"""
Miniflow Main Application

Bu ana uygulama dosyası workflow_manager ve scheduler'ı birleştirir:
- Workflow yukleme ve tetikleme komutlari
- Scheduler'in background'da calismasi
- Unified command-line interface
- System durumu izleme

Kullanim:
    python -m miniflow --help
    python -m miniflow start                    # Scheduler'i baslat
    python -m miniflow load workflow.json  , python -m miniflow load chained_workflow.json  , math_workflow.json   # Workflow yukle
    python -m miniflow trigger workflow_id      # Workflow tetikle
    python -m miniflow status                   # System durumunu goster
    python -m miniflow interactive              # Interaktif mod
"""

import argparse
import sys
import threading
import time
import json
import signal
from pathlib import Path
from typing import Optional, Dict, Any

# Miniflow components
from . import workflow_manager
from . import scheduler
from .database import init_database, list_workflows, get_workflow
from .database.functions.workflow_orchestration import get_execution_status_summary
from .database.config import USE_SQLITE, POSTGRES_URL


class MiniflowApp:
    """
    Ana Miniflow uygulamasi

    Workflow Manager ve Scheduler'i koordine eder ve command-line interface saglar.
    """

    def __init__(self):
        self.scheduler_instance: Optional[scheduler.WorkflowScheduler] = None
        self.scheduler_thread: Optional[threading.Thread] = None
        self.running = False

        # DB baglantisini ayarla
        self.db_path = "miniflow.db" if USE_SQLITE else POSTGRES_URL

        self.setup_signal_handlers()

        try:
            init_database(self.db_path)
            print(f"✅ Database basariyla baslatildi: {self.db_path}")
        except Exception as e:
            print(f"❌ Database baslatma hatasi: {e}")
            sys.exit(1)

    def setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        print("\n🚩 Cikis sinyali alindi, sistem temizleniyor...")
        self.stop()
        sys.exit(0)

    def start_scheduler(self, background: bool = True):
        if self.scheduler_instance is not None:
            print("⚠️ Scheduler zaten calisiyor")
            return

        try:
            self.scheduler_instance = scheduler.create_scheduler(self.db_path)
            self.running = True

            if background:
                self.scheduler_thread = threading.Thread(
                    target=self._run_scheduler_loop,
                    daemon=True
                )
                self.scheduler_thread.start()
                print("🚀 Scheduler background'da baslatildi")
            else:
                print("🚀 Scheduler baslatiliyor...")
                self._run_scheduler_loop()

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"❌ Scheduler baslatma hatasi: {e}")
            raise

    def _run_scheduler_loop(self):
        try:
            if self.scheduler_instance and not self.scheduler_instance.is_running():
                success = self.scheduler_instance.start()
                if not success:
                    print("❌ Scheduler baslatilamadi")
                    status = self.scheduler_instance.get_status() if self.scheduler_instance else {}
                    print("🔍 Scheduler durumu:", status)
                    return
                time.sleep(1)

                if self.scheduler_instance.is_running():
                    print("✅ Scheduler basariyla baslatildi")
                else:
                    print("⚠️ Scheduler baslatildi ama henuz tam aktif degil")

            while self.running and self.scheduler_instance and self.scheduler_instance.is_running():
                time.sleep(1)

        except Exception as e:
            print(f"❌ Scheduler dongusu hatasi: {e}")
        finally:
            print("🚩 Scheduler durduruldu")

    def stop(self):
        self.running = False
        if self.scheduler_instance:
            self.scheduler_instance.stop()
            self.scheduler_instance = None

        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
            self.scheduler_thread = None

    def load_workflow(self, filepath: str) -> Dict[str, Any]:
        try:
            if not Path(filepath).exists():
                raise FileNotFoundError(f"Workflow dosyasi bulunamadi: {filepath}")

            print(f"📂 Workflow yukleniyor: {filepath}")
            load_result = workflow_manager.load_workflow_from_file(self.db_path, filepath)

            if load_result.get('success'):
                print(f"✅ Workflow basariyla yuklendi:")
                print(f"   ID: {load_result['workflow_id']}")
                print(f"   Isim: {load_result['workflow_name']}")
                print(f"   Nodes: {load_result['nodes_created']}, Edges: {load_result['edges_created']}")
                return load_result
            else:
                raise Exception(load_result.get('error', 'Bilinmeyen hata'))

        except Exception as e:
            print(f"❌ Workflow yukleme hatasi: {e}")
            raise

    def trigger_workflow(self, workflow_id: str) -> Dict[str, Any]:
        try:
            print(f"🔥 Workflow tetikleniyor: {workflow_id}")
            trigger_result = workflow_manager.trigger_workflow_manually(self.db_path, workflow_id)

            if trigger_result.get('success'):
                print(f"✅ Workflow basariyla tetiklendi:")
                print(f"   Execution ID: {trigger_result['execution_id']}")
                print(f"   Olusturulan tasklar: {trigger_result['created_tasks']}")
                print(f"   Hazir tasklar: {trigger_result['ready_tasks']}")
                return trigger_result
            else:
                raise Exception(trigger_result.get('error', 'Bilinmeyen hata'))

        except Exception as e:
            print(f"❌ Workflow tetikleme hatasi: {e}")
            raise

    def show_status(self):
        print("\n📊 Miniflow System Durumu")
        print("=" * 50)

        if self.scheduler_instance and self.running and self.scheduler_instance.is_running():
            print("🚀 Scheduler: Aktif")
            status = self.scheduler_instance.get_status()
            print(f"   Queue Monitor: {'✅' if status.get('queue_monitor_running') else '❌'}")
            print(f"   Result Monitor: {'✅' if status.get('result_monitor_running') else '❌'}")
        else:
            print("🚩 Scheduler: Pasif")

        try:
            workflows_result = list_workflows(self.db_path)
            if workflows_result.success:
                workflows = workflows_result.data
                print(f"📋 Toplam Workflow: {len(workflows)}")

                if workflows:
                    print("\n🗘️ Workflows:")
                    for wf in workflows[:5]:
                        print(f"   • {wf['id']}: {wf['name']}")
                    if len(workflows) > 5:
                        print(f"   ... ve {len(workflows) - 5} tane daha")
            else:
                print(f"❌ Workflow bilgileri alinamadi: {workflows_result.error}")
        except Exception as e:
            print(f"❌ Workflow bilgileri alinamadi: {e}")

    def interactive_mode(self):
        print("\n🎯 Miniflow Interaktif Mod")
        print("Komutlar: load <file>, trigger <id>, status, start, stop, quit")
        print("=" * 50)

        while True:
            try:
                command = input("\nminiflow> ").strip().lower()

                if not command:
                    continue

                parts = command.split()
                cmd = parts[0]

                if cmd in ('quit', 'exit'):
                    print("👋 Cikiliyor...")
                    break
                elif cmd == 'load' and len(parts) >= 2:
                    self.load_workflow(parts[1])
                elif cmd == 'trigger' and len(parts) >= 2:
                    self.trigger_workflow(parts[1])
                elif cmd == 'status':
                    self.show_status()
                elif cmd == 'start':
                    self.start_scheduler(background=True)
                elif cmd == 'stop':
                    self.stop()
                    print("🚩 Scheduler durduruldu")
                elif cmd == 'help':
                    print("Komutlar: load <file>, trigger <id>, status, start, stop, quit")
                else:
                    print(f"❌ Bilinmeyen komut: {cmd}")
            except KeyboardInterrupt:
                print("\n👋 Cikiliyor...")
                break
            except Exception as e:
                print(f"❌ Beklenmeyen hata: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Miniflow - Workflow Management System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ornekler:
  python -m miniflow start                    # Scheduler'i baslat
  python -m miniflow load workflow.json       # Workflow yukle
  python -m miniflow trigger 1                # Workflow tetikle
  python -m miniflow status                   # Durum goster
  python -m miniflow interactive              # Interaktif mod
        """
    )

    parser.add_argument('command', choices=['start', 'load', 'trigger', 'status', 'interactive'])
    parser.add_argument('argument', nargs='?', help='Komut argumani (dosya yolu veya workflow ID)')
    parser.add_argument('--background', action='store_true', help='Scheduler arka planda calissin')

    args = parser.parse_args()
    app = MiniflowApp()

    try:
        if args.command == 'start':
            app.start_scheduler(background=args.background)
            while app.running:
                time.sleep(1)
        elif args.command == 'load':
            if not args.argument:
                print("❌ Workflow dosya yolu gerekli")
                sys.exit(1)
            app.load_workflow(args.argument)
        elif args.command == 'trigger':
            if not args.argument:
                print("❌ Workflow ID gerekli")
                sys.exit(1)
            app.trigger_workflow(args.argument)
        elif args.command == 'status':
            app.show_status()
        elif args.command == 'interactive':
            app.start_scheduler(background=True)
            app.interactive_mode()
    except Exception as e:
        print(f"❌ Uygulama hatasi: {e}")
        sys.exit(1)
    finally:
        app.stop()


if __name__ == '__main__':
    main()
