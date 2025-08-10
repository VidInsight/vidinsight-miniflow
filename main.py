#!/usr/bin/env python3
"""
MINIFLOW STARTUP SCRIPT
======================

Bu script, Miniflow sisteminin tüm bileşenlerini başlatmak için kullanılır:
- Database Engine (SQLite/MySQL/PostgreSQL)
- Parallelism Engine (Task execution engine)
- Scheduler (Input/Output monitors)
- REST API Server (FastAPI)

KULLANIM:
========

1. Development Mode (SQLite + Scheduler Aktif):
   python main.py

2. Production Mode (PostgreSQL + Custom Config):
   python main.py --db-type postgresql --db-name prod_db --host db.company.com --username miniflow_user --password secret

3. API Only Mode (Scheduler Kapalı):
   python main.py --no-scheduler

4. Custom Port:
   python main.py --port 9000

DESTEKLENEN DATABASE TÜRLER:
============================
- sqlite (development için ideal)
- postgresql (production için önerilen)
- mysql (web uygulamaları için)

ENVIRONMENT VARIABLES:
=====================
- MINIFLOW_DB_TYPE: Database türü (sqlite, postgresql, mysql)
- MINIFLOW_DB_NAME: Database adı
- MINIFLOW_DB_HOST: Database host
- MINIFLOW_DB_PORT: Database port
- MINIFLOW_DB_USER: Database kullanıcı adı
- MINIFLOW_DB_PASS: Database şifresi
- MINIFLOW_API_HOST: API server host (default: 127.0.0.1)
- MINIFLOW_API_PORT: API server port (default: 8000)
- MINIFLOW_ENABLE_SCHEDULER: Scheduler aktif/pasif (true/false)
"""

import os
import sys
import argparse
import logging
import signal
import time
from pathlib import Path
from typing import Optional

# Miniflow imports
try:
    from miniflow.main import MiniflowCore
    from miniflow.utils import setup_logging
    from miniflow.exceptions import MiniflowException
except ImportError as e:
    print(f"❌ Miniflow modülleri yüklenemedi: {e}")
    print("✅ Lütfen miniflow paketinin doğru kurulduğundan emin olun")
    sys.exit(1)

# Global variables
core_instance: Optional[MiniflowCore] = None
shutdown_requested = False

def signal_handler(signum, frame):
    """Graceful shutdown handler for SIGINT and SIGTERM"""
    global shutdown_requested, core_instance
    
    print(f"\n🛑 Shutdown signal alındı ({signal.Signals(signum).name})")
    shutdown_requested = True
    
    if core_instance:
        print("🔄 Miniflow Core durduruluyor...")
        try:
            core_instance.stop()
            print("✅ Miniflow Core başarıyla durduruldu")
        except Exception as e:
            print(f"❌ Shutdown sırasında hata: {e}")
    
    print("👋 Hoşçakalın!")
    sys.exit(0)

def parse_arguments():
    """Command line arguments parser"""
    parser = argparse.ArgumentParser(
        description="Miniflow - Minimalist Workflow Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Database configuration
    db_group = parser.add_argument_group('Database Configuration')
    db_group.add_argument(
        '--db-type', 
        choices=['sqlite', 'postgresql', 'mysql'],
        default=os.getenv('MINIFLOW_DB_TYPE', 'sqlite'),
        help='Database türü (default: sqlite)'
    )
    db_group.add_argument(
        '--db-name',
        default=os.getenv('MINIFLOW_DB_NAME', 'miniflow_dev'),
        help='Database adı (default: miniflow_dev)'
    )
    db_group.add_argument(
        '--host',
        default=os.getenv('MINIFLOW_DB_HOST', 'localhost'),
        help='Database host (MySQL/PostgreSQL için)'
    )
    db_group.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('MINIFLOW_DB_PORT', '0')),
        help='Database port (MySQL: 3306, PostgreSQL: 5432)'
    )
    db_group.add_argument(
        '--username',
        default=os.getenv('MINIFLOW_DB_USER', ''),
        help='Database kullanıcı adı'
    )
    db_group.add_argument(
        '--password',
        default=os.getenv('MINIFLOW_DB_PASS', ''),
        help='Database şifresi'
    )
    
    # API Server configuration
    api_group = parser.add_argument_group('API Server Configuration')
    api_group.add_argument(
        '--api-host',
        default=os.getenv('MINIFLOW_API_HOST', '127.0.0.1'),
        help='API server host (default: 127.0.0.1)'
    )
    api_group.add_argument(
        '--api-port',
        type=int,
        default=int(os.getenv('MINIFLOW_API_PORT', '8000')),
        help='API server port (default: 8000)'
    )
    api_group.add_argument(
        '--reload',
        action='store_true',
        help='Development mode - auto reload on file changes'
    )
    
    # System configuration
    system_group = parser.add_argument_group('System Configuration')
    system_group.add_argument(
        '--no-scheduler',
        action='store_true',
        help='Scheduler\'ı devre dışı bırak (sadece API çalışır)'
    )
    system_group.add_argument(
        '--health-check',
        action='store_true',
        help='Sistem sağlık kontrolü yap ve çık'
    )
    system_group.add_argument(
        '--version',
        action='store_true',
        help='Sürüm bilgisini göster ve çık'
    )
    system_group.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Detaylı log çıktısı'
    )
    
    return parser.parse_args()

def setup_database_params(args):
    """Database parametrelerini hazırla"""
    db_params = {
        'db_name': args.db_name
    }
    
    # Network database için gerekli parametreler
    if args.db_type in ['postgresql', 'mysql']:
        if not args.username:
            if args.db_type == 'postgresql':
                args.username = 'postgres'
            else:  # mysql
                args.username = 'root'
        
        if not args.password:
            args.password = 'password'
            
        if args.port == 0:
            if args.db_type == 'postgresql':
                args.port = 5432
            else:  # mysql
                args.port = 3306
        
        db_params.update({
            'host': args.host,
            'port': args.port,
            'username': args.username,
            'password': args.password
        })
    
    return db_params

def print_startup_banner(args):
    """Startup banner göster"""
    print("=" * 60)
    print("🚀 MINIFLOW WORKFLOW ENGINE BAŞLATILIYOR")
    print("=" * 60)
    print(f"📊 Database: {args.db_type.upper()}")
    print(f"🗄️  Database Name: {args.db_name}")
    
    if args.db_type != 'sqlite':
        print(f"🌐 Host: {args.host}:{args.port}")
        print(f"👤 User: {args.username}")
    
    print(f"🌍 API Server: http://{args.api_host}:{args.api_port}")
    print(f"📚 API Docs: http://{args.api_host}:{args.api_port}/docs")
    print(f"💚 Health Check: http://{args.api_host}:{args.api_port}/health")
    
    scheduler_status = "❌ DISABLED" if args.no_scheduler else "✅ ENABLED"
    print(f"⏰ Scheduler: {scheduler_status}")
    
    print("=" * 60)

def initialize_miniflow(args):
    """Miniflow Core'u initialize et"""
    global core_instance
    
    print("🔧 Miniflow Core initialize ediliyor...")
    
    try:
        # Database parametrelerini hazırla
        db_params = setup_database_params(args)
        
        # Scheduler durumunu belirle
        enable_scheduler = not args.no_scheduler
        
        # MiniflowCore instance oluştur
        core_instance = MiniflowCore(
            db_type=args.db_type,
            enable_scheduler=enable_scheduler,
            **db_params
        )
        
        print("✅ Miniflow Core başarıyla oluşturuldu")
        return True
        
    except Exception as e:
        print(f"❌ Miniflow Core initialization hatası: {e}")
        return False

def start_miniflow_services():
    """Miniflow servislerini başlat"""
    global core_instance
    
    if not core_instance:
        print("❌ Core instance bulunamadı")
        return False
    
    print("🚀 Miniflow servisleri başlatılıyor...")
    
    try:
        # Core servisleri başlat (Database, Engine, Scheduler)
        core_instance.start()
        print("✅ Miniflow servisleri başarıyla başlatıldı")
        
        # Health check yapalım
        health = core_instance.health_check()
        if health.get('status') == 'healthy':
            print("💚 Sistem sağlığı: HEALTHY")
        else:
            print(f"⚠️  Sistem sağlığı: {health.get('status', 'UNKNOWN')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Miniflow servisleri başlatılamadı: {e}")
        return False

def run_health_check():
    """Sistem sağlık kontrolü"""
    print("🔍 Sistem sağlık kontrolü yapılıyor...")
    
    try:
        # Temporary core instance for health check
        temp_core = MiniflowCore(db_type="sqlite", db_name="health_check_temp", enable_scheduler=False)
        temp_core.start()
        
        health = temp_core.health_check()
        
        print("\n📊 SAĞLIK RAPORU:")
        print("=" * 40)
        print(f"Durum: {health.get('status', 'UNKNOWN').upper()}")
        print(f"Zaman: {health.get('timestamp', 'N/A')}")
        
        components = health.get('components', {})
        for component, status in components.items():
            if isinstance(status, dict):
                print(f"  {component}:")
                for sub_comp, sub_status in status.items():
                    emoji = "✅" if sub_status == "healthy" else "❌"
                    print(f"    {sub_comp}: {emoji} {sub_status}")
            else:
                emoji = "✅" if status == "healthy" else "❌"
                print(f"  {component}: {emoji} {status}")
        
        temp_core.stop()
        
        if health.get('status') == 'healthy':
            print("\n💚 Sistem sağlıklı ve kullanıma hazır!")
            return True
        else:
            print(f"\n❌ Sistem durumu: {health.get('status')}")
            return False
            
    except Exception as e:
        print(f"❌ Sağlık kontrolü hatası: {e}")
        return False

def main():
    """Ana fonksiyon"""
    global core_instance
    
    # Logging setup
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse arguments
    args = parse_arguments()
    
    # Verbose logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging aktif")
    
    # Version check
    if args.version:
        try:
            from miniflow.app.config.settings import Settings
            print(f"Miniflow v{Settings.PROJECT_VERSION}")
        except:
            print("Miniflow v0.1.0")
        return 0
    
    # Health check only
    if args.health_check:
        success = run_health_check()
        return 0 if success else 1
    
    # Normal startup
    try:
        # Banner göster
        print_startup_banner(args)
        
        # Miniflow initialize et
        if not initialize_miniflow(args):
            return 1
        
        # Servisleri başlat
        if not start_miniflow_services():
            return 1
        
        print("\n🎉 Miniflow başarıyla başlatıldı!")
        print("🔗 API endpoint'leri kullanmaya hazır")
        print("🛑 Durdurmak için Ctrl+C tuşlayın")
        
        # Set core instance for FastAPI dependencies
        print("🔗 Core instance FastAPI dependencies'e set ediliyor...")
        from miniflow.app.dependencies import set_core_instance
        set_core_instance(core_instance)
        
        # API Server'ı başlat (blocking)
        print(f"\n🌐 API Server başlatılıyor ({args.api_host}:{args.api_port})...")
        core_instance.start_api_server(
            host=args.api_host,
            port=args.api_port,
            reload=args.reload
        )
        
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        logger.error(f"❌ Beklenmeyen hata: {e}")
        if core_instance:
            try:
                core_instance.stop()
            except:
                pass
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
