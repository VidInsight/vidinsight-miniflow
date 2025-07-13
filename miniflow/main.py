import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Utility
from .utils import setup_logging
from .utils import create_script, delete_script
# Database
from .database_manager import DatabaseConfig, DatabaseEngine, DatabaseOrchestration, Base
from .database_manager import get_sqlite_config, get_mysql_config, get_postgresql_config
from .database_manager import create_database_engine

setup_logging()
logger = logging.getLogger(__name__)
logger.debug(f"Logger tanımları tanımlandı")


class MiniflowCore:
    def __init__(self, db_type: str,  **db_params):
        # Database
        self.db_type: str = db_type
        self.db_engine: DatabaseEngine = None
        self.orchestration: DatabaseOrchestration = None
        self.scripts_dir: Path = Path("scripts")
        self.db_config: DatabaseConfig = self.__create_config(db_type, **db_params)
        logger.debug(f"Database tanımları tanımlandı")

    def start(self):
        # 1. Database'i başlat
        self.__start_database_engine()

    def stop(self):
        # n. Database'i durdur
        self.__stop_database_engine()


    # DATABASE MANAGER METOTLARI
    # ===========================================================

    @staticmethod
    def __create_config(db_type: str, **db_params):
        if db_type == "sqlite":
            return get_sqlite_config(db_params.get("db_name", "test_database"))
        elif db_type == "postgresql":
            return get_postgresql_config(db_name=db_params.get('db_name', 'workflow_db'),host=db_params.get('host', 'localhost'),
                port=db_params.get('port', 5432), username=db_params.get('username', 'postgres'), password=db_params.get('password', 'password'))
        elif db_type == "mysql":
            return get_mysql_config(db_name=db_params.get('db_name', 'workflow_db'), host=db_params.get('host', 'localhost'),
                port=db_params.get('port', 3306), username=db_params.get('username', 'root'), password=db_params.get('password', 'password'))
        else:
            logger.error("Belirtilen veritabanı tipi desteklenmiyor")
            raise ValueError("DAtabase Type Error")
        
    def __start_database_engine(self):
        # 1. Engine oluştur
        self.db_engine = create_database_engine(config=self.db_config)
        logger.debug("DatabaseEngine oluşturuldu")

        # 2. Engine başlat
        self.db_engine.start()
        logger.debug("DatabaseEngine başlatıldı")

        # 3. Tabloları oluştur
        self.db_engine.create_tables(Base.metadata)
        logger.debug("Database tabloları oluşturuldu")

        # 4. Orchestration başlat
        self.orchestration = DatabaseOrchestration()
        logger.debug("DatabaseOrchestration oluşturuldu")

        # 5. Scripts klasörünü oluştur
        self.scripts_dir.mkdir(exist_ok=True)
        logger.debug("Scripts klasörü hazırlandı")

    def __stop_database_engine(self):
        # 1. Engine'ı durdur
        self.db_engine.stop()
        logger.debug("DatabaseEngine durduruldu")

        # 2. Değişkenleri sıfırla
        self.db_engine = None
        self.orchestration = None
        logger.debug("DatabaseEngine None olarak değiştirldi")


    # SCRIPT METOTLARI 
    # ===========================================================
    def script_create(self, script_data: dict, script_content: str) -> dict:
        # 0. Temel Kontroller
        if not self.db_engine:
            raise ValueError("Database engine not initialized")
            
        try:
            # 1. Script Validasyonu
            # Henüz validasyon fonksiyonları hazırlanmadı

            # 2. Dosya oluştur
            absolute_path = create_script(
                scripts_dir=self.scripts_dir,
                script_name=script_data.get("name"),
                script_extension="py",
                script_content=script_content
            )

            # 3. Veritabanı için payload oluştur
            payload = {
                'name': script_data['name'],
                'description': script_data['description'],
                'language': 'PYTHON',  # ScriptType.PYTHON enum value
                'input_params': script_data['input_structure'],
                'output_params': script_data['output_structure'],
                'script_path' : absolute_path
            }

            # 5. Veritabanı kaydı oluştur
            with self.db_engine.get_session_context() as session:
                script_dict = self.orchestration.create_script(session, payload)
                session.flush()
                session.commit()

            # 6. Çıktıyı Döndür
            return script_dict
        except Exception as e:
            logger.error(f"Script oluşturma hatası: {e}")
            raise

    def script_delete(self, script_id: str):
        # 0. Temel Kontroller
        if not self.db_engine:
            raise ValueError("Database engine not initialized")
        
        try:
            with self.db_engine.get_session_context() as session:
                result = self.orchestration.delete_script(session, script_id)

            return result
        except Exception as e:
            logger.error(f"Script silme hatası: {e}")
            raise

    def script_list(self):
        # 0. Temel Kontroller
        if not self.db_engine:
            raise ValueError("Database engine not initialized")
        
        try:
            with self.db_engine.get_session_context() as session:
                result = self.orchestration.get_scripts(session)
            return result
        except Exception as e:
            logger.error(f"Script listeleme hatası: {e}")
            raise

    def script_get(self, script_id: str, include_content: bool = False):
        # 0. Temel Kontroller
        if not self.db_engine:
            raise ValueError("Database engine not initialized")
        
        try:
            with self.db_engine.get_session_context() as session:
                result = self.orchestration.get_script(session, script_id, include_content)
            return result
        except Exception as e:
            logger.error(f"Script getirme hatası: {e}")
            raise

    # WORKFLOW METOTLARI 
    # ===========================================================
    def workflow_create(self, workflow_data: dict) -> dict:
        # 0. Temel Kontroller
        if not self.db_engine:
            raise ValueError("Database engine not initialized")
            
        try:
            # 1. Workflow Validasyonu
            # Henüz validasyon fonksiyonları hazırlanmadı

            # 2. Veritabanı kaydı oluştur
            with self.db_engine.get_session_context() as session:
                result = self.orchestration.create_workflow(session, workflow_data)
                session.flush()
                session.commit()

            # 3. Çıktıyı Döndür
            return result
        except Exception as e:
            logger.error(f"Workflow oluşturma hatası: {e}")
            raise

    def workflow_delete(self, workflow_id: str) -> dict:
        # 0. Temel Kontroller
        if not self.db_engine:
            raise ValueError("Database engine not initialized")
        
        try:
            with self.db_engine.get_session_context() as session:
                result = self.orchestration.delete_workflow(session, workflow_id)
                session.flush()
                session.commit()

            return result
        except Exception as e:
            logger.error(f"Workflow silme hatası: {e}")
            raise

    def workflow_update(self, workflow_id: str, workflow_data: dict) -> dict:
        # 0. Temel Kontroller
        if not self.db_engine:
            raise ValueError("Database engine not initialized")
        
        try:
            with self.db_engine.get_session_context() as session:
                result = self.orchestration.update_workflow(session, workflow_id, workflow_data)
                session.flush()
                session.commit()

            return result
        except Exception as e:
            logger.error(f"Workflow güncelleme hatası: {e}")
            raise

    def workflow_list(self) -> list:
        # 0. Temel Kontroller
        if not self.db_engine:
            raise ValueError("Database engine not initialized")
        
        try:
            with self.db_engine.get_session_context() as session:
                result = self.orchestration.get_workflows(session)
            return result
        except Exception as e:
            logger.error(f"Workflow listeleme hatası: {e}")
            raise

    def workflow_get(self, workflow_id: str) -> dict:
        # 0. Temel Kontroller
        if not self.db_engine:
            raise ValueError("Database engine not initialized")
        
        try:
            with self.db_engine.get_session_context() as session:
                result = self.orchestration.get_workflow(session, workflow_id)
            return result
        except Exception as e:
            logger.error(f"Workflow getirme hatası: {e}")
            raise




