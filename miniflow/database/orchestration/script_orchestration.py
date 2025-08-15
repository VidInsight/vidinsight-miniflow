# orchestration/script_orchestration.py
import os
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, Union, List

from .base_orchestration import BaseOrchestration
from ..models import WorkflowStatus, ScriptTestStatus
from ...exceptions import ValidationError, BusinessLogicError, CRUDException, ResourceError, ErrorManager


class ScriptOrchestrator(BaseOrchestration):
    """Script operasyonları için orchestrator"""

    def __init__(self):
        super().__init__()

    def create(self, session: Session, path: str, script_data: Dict[str, Any]) -> Dict[str, Any]:
        """ Create Script """

        # Validate script name
        name = script_data.get('name', '').strip()
        if not name:
            raise ValidationError("Script name is required")
        
        # Check if name contains only valid characters
        if not name.replace('_', '').replace('-', '').isalnum():
            raise ValidationError("Script name must contain only alphanumeric characters, hyphens, and underscores")

        # Validate script name
        existing_script = self.script_crud.find_by_name(session, script_data.get('name'))
        if existing_script:
            raise ValidationError(f"Script with name '{script_data.get('name')}' already exists")
        
        # 3. Validation: Script Extension
        script_content = script_data.get('script_content', '')
        extension = script_data.get('language', self._detect_script_language(script_content))

        # 4. OPERATION: Create script file path
        script_path = os.path.join(path, f"{script_data.get('name')}.{extension}")
        
        # 5. VALIDATION: Check if file already exists
        if os.path.exists(script_path):
            raise ResourceError(f"Script file already exists at path: {script_path}")
        
        # 6. OPERATION: Write script content to file
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            f.close()
        except (OSError, IOError) as e:
            raise ResourceError(f"Failed to write script file: {str(e)}")

        # 7. OPERATION: Create script in database
        script = self.script_crud.create_script(session, **{
            'name': script_data.get('name'),
            'description': script_data.get('description', ''),
            'language': extension,
            'script_path': script_path,
            'input_params': script_data.get('input_params', {}),
            'output_params': script_data.get('output_params', {})
        })

        # 8. RETURN: API Format
        return script.to_dict()

    def update(self, session: Session, path: str, script_id: str, script_data: Dict[str, Any]) -> Dict[str, Any]:
        """Script güncelleme"""
        # 1. VALIDATION: Old script
        old_script = self.script_crud.find_by_id(session, script_id)
        if not old_script:
            raise BusinessLogicError(f"Script not found: {script_id}")
        
        # 2. VALIDATION: New script name
        if 'name' in script_data and script_data['name'] != old_script.name:
            existing_script = self.script_crud.find_by_name(session, script_data['name'])
            if existing_script and existing_script.id != script_id:
                raise ValidationError(f"Script with name '{script_data['name']}' already exists")
            
            # Validate new name
            name = script_data['name']
            if not name or not name.replace('_', '').replace('-', '').isalnum():
                raise ValidationError("Script name must contain only alphanumeric characters, hyphens, and underscores")

            # Rename script file
            old_extension = old_script.language.value if hasattr(old_script.language, 'value') else old_script.language
            old_script_path = os.path.join(path, f"{old_script.name}.{old_extension}")
            new_script_path = os.path.join(path, f"{script_data['name']}.{old_extension}")
            
            # Check if target file already exists (and it's not the current file)
            if os.path.exists(new_script_path) and new_script_path != old_script_path:
                raise ResourceError(f"Script file already exists at path: {new_script_path}")
            
            try:
                os.rename(old_script_path, new_script_path)
            except (OSError, IOError) as e:
                raise ResourceError(f"Failed to rename script file: {str(e)}")

            # Update script path
            script_data['script_path'] = new_script_path
            
        # 3. OPERATION: Update script content
        if 'script_content' in script_data:
            script_content = script_data['script_content']
            extension = script_data.get('language', self._detect_script_language(script_content))
            old_extension = old_script.language.value if hasattr(old_script.language, 'value') else old_script.language
            
            if extension != old_extension:
                script_data['language'] = extension

                old_script_path = os.path.join(path, f"{old_script.name}.{old_extension}")
                new_script_path = os.path.join(path, f"{script_data.get('name', old_script.name)}.{extension}")
                
                # Check if target file already exists (and it's not the current file)
                if os.path.exists(new_script_path) and new_script_path != old_script_path:
                    raise ResourceError(f"Script file already exists at path: {new_script_path}")
                
                try:
                    os.rename(old_script_path, new_script_path)
                except (OSError, IOError) as e:
                    raise ResourceError(f"Failed to rename script file: {str(e)}")

                script_data['script_path'] = new_script_path
            else:
                # Use current script path if no language change
                current_script_path = script_data.get('script_path', old_script.script_path)

            try:
                script_file_path = script_data.get('script_path', old_script.script_path)
                with open(script_file_path, 'w', encoding='utf-8') as f:
                    f.write(script_content)
                f.close()
            except (OSError, IOError) as e:
                raise ResourceError(f"Failed to update script file: {str(e)}")

        # 4. OPERATION: Update script in database
        updated_script = self.script_crud.update_script(session, script_id, **script_data)
        
        # 5. RETURN: API Format
        return updated_script.to_dict()

    def delete(self, session: Session, script_id: str, force: bool = False) -> Dict[str, Any]:
        """Script silme"""
        # 1. VALIDATION: Script
        script = self.script_crud.find_by_id(session, script_id)
        if not script:
            raise BusinessLogicError(f"Script not found: {script_id}")

        # 2. VALIDATION: Script usage
        nodes_using_script = self.node_crud.get_by_script(session, script_id)
        workflows = set()

        for node in nodes_using_script:
            if node.workflow_id not in workflows:
                workflows.add(node.workflow_id)

        if not force:
            if nodes_using_script:
                raise BusinessLogicError(f"Cannot delete script - it is being used by {len(nodes_using_script)} node(s). Use force=True to override.")

        # 3. OPERATION: Delete script file
        if script.script_path and os.path.exists(script.script_path):
            try:
                os.remove(script.script_path)
            except (OSError, IOError) as e:
                raise ResourceError(f"Failed to delete script file: {str(e)}")

        # 4. OPERATION: Delete script in database
        deleted_script = self.script_crud.delete_script(session, script_id)

        # 5. OPERATION: Change workflow status to draft
        for workflow_id in workflows:
            workflow = self.workflow_crud.find_by_id(session, workflow_id)
            if workflow:
                self.workflow_crud.set_status(session, workflow_id, WorkflowStatus.DRAFT)

        # 6. RETURN: API Format
        result = deleted_script.to_dict()
        result['affected_nodes'] = len(nodes_using_script)
        result['affected_workflows'] = len(workflows)
        return result

    def search(self, session: Session, search_criteria: Dict[str, Any], skip: int = 0, limit: int = 100, order_by_field: str = None) -> Dict[str, Any]:
        """Script arama"""
        # 1. OPERATION: Search scripts
        scripts = self.script_crud.filter(session, search_criteria, skip=skip, limit=limit, order_by_field=order_by_field)
        
        # Get total count for pagination
        total_count = self.script_crud.count_filtered(session, search_criteria)
        
        # 2. RETURN: API Format
        return {
            'data': [script.to_dict() for script in scripts],
            'total_count': total_count,
            'skip': skip,
            'limit': limit,
            'has_more': (skip + limit) < total_count
        }

    def get(self, session: Session, script_id: str, include_content: bool = False) -> Dict[str, Any]:
        """Script detayını getir"""
        # 1. OPERATION: Get script
        script = self.script_crud.find_by_id(session, script_id)
        if not script:
            raise BusinessLogicError(f"Script not found: {script_id}")
        
        # 2. OPERATION: Convert to dict
        script_dict = script.to_dict()
        
        # 3. OPERATION: Add script content if requested
        if include_content:
            if not script.script_path:
                raise ResourceError("Script file path is missing")
            
            if not os.path.exists(script.script_path):
                raise ResourceError(f"Script file not found: {script.script_path}")
            
            try:
                with open(script.script_path, 'r', encoding='utf-8') as f:
                    script_dict['script_content'] = f.read()
            except (OSError, IOError) as e:
                raise ResourceError(f"Failed to read script file: {str(e)}")
        
        # 4. RETURN: API Format
        return script_dict

    def count(self, session: Session) -> int:
        """Script sayısını getir"""
        return self.script_crud.count(session)
    
    def exists(self, session: Session, script_id: str) -> bool:
        """Script var mı kontrolü"""
        return self.script_crud.exists(session, script_id)

    def _detect_script_language(self, content: str) -> str:
        """
        Programlama dilini tespit eder
        """
        content_lower = content.lower().strip()
        
        if content_lower.startswith('#!/usr/bin/env python') or 'import ' in content_lower or 'def ' in content_lower:
            return 'py'
        elif content_lower.startswith('#!/bin/bash') or content_lower.startswith('#!/bin/sh'):
            return 'sh'
        else:
            return 'py'

    def get_by_language(self, session: Session, language: str) -> List[Dict[str, Any]]:
        """Scriptları dil bazında getir"""
        scripts = self.script_crud.get_by_language(session, language)
        return [script.to_dict() for script in scripts]

    def get_untested_scripts(self, session: Session) -> List[Dict[str, Any]]:
        """Test edilmemiş scriptleri getir"""
        scripts = self.script_crud.get_by_test_status(session, ScriptTestStatus.UNTESTED)
        return [script.to_dict() for script in scripts]

    def get_failed_scripts(self, session: Session) -> List[Dict[str, Any]]:
        """Test başarısız scriptleri getir"""
        scripts = self.script_crud.get_by_test_status(session, ScriptTestStatus.FAILED)
        return [script.to_dict() for script in scripts]

    def get_passed_scripts(self, session: Session) -> List[Dict[str, Any]]:
        """Test başarılı scriptleri getir"""
        scripts = self.script_crud.get_by_test_status(session, ScriptTestStatus.PASSED)
        return [script.to_dict() for script in scripts]
    
    def get_all_scripts(self, session: Session) -> List[Dict[str, Any]]:
        """Tüm scriptleri getir"""
        scripts = self.script_crud.get_all(session)
        return [script.to_dict() for script in scripts]