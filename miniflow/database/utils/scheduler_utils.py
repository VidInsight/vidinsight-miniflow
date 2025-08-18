"""
Dynamic Value Processor Module

Bu modül JSON sözlüklerindeki farklı değer tiplerini işler:
1. Dynamic value (via name): {{ node_name.node_variable}}
2. Dynamic value (via id): {{node_id.node_variable}} (id ND ile başlar)
3. Environment value: {${variable_name}}
4. Static value: sayısal değerler
"""

import re
import os
import json
from typing import Dict, Any, Optional, List


# Pattern tanımlamaları
DYNAMIC_NAME_PATTERN = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
DYNAMIC_ID_PATTERN = r'\{\{\s*(ND[a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
ENV_PATTERN = r'\{\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}'


def match_pattern(pattern: str, value: str) -> Optional[str]:
    """Verilen pattern ile value'yu kontrol eder"""
    if not isinstance(value, str):
        return None
    
    match = re.match(pattern, value.strip())
    return match.group(1) if match else None


def is_dynamic_name(value: str) -> bool:
    """Dynamic name pattern kontrolü"""
    return match_pattern(DYNAMIC_NAME_PATTERN, value) is not None


def is_dynamic_id(value: str) -> bool:
    """Dynamic ID pattern kontrolü"""
    return match_pattern(DYNAMIC_ID_PATTERN, value) is not None


def is_environment(value: str) -> bool:
    """Environment variable pattern kontrolü"""
    return match_pattern(ENV_PATTERN, value) is not None


def is_static(value: Any) -> bool:
    """Static value kontrolü"""
    return not isinstance(value, str) or (
        isinstance(value, str) and 
        not any([is_dynamic_name(value), is_dynamic_id(value), is_environment(value)])
    )


def extract_dynamic_name(value: str) -> Optional[tuple]:
    """Dynamic name'den node ve variable çıkarır"""
    matched = match_pattern(DYNAMIC_NAME_PATTERN, value)
    if matched:
        parts = matched.split('.')
        return (parts[0], parts[1]) if len(parts) == 2 else None
    return None


def extract_dynamic_id(value: str) -> Optional[tuple]:
    """Dynamic ID'den node ve variable çıkarır"""
    matched = match_pattern(DYNAMIC_ID_PATTERN, value)
    if matched:
        parts = matched.split('.')
        return (parts[0], parts[1]) if len(parts) == 2 else None
    return None


def extract_environment(value: str) -> Optional[str]:
    """Environment variable adını çıkarır"""
    return match_pattern(ENV_PATTERN, value)


def get_value_type(value: Any) -> str:
    """Değerin tipini belirler"""
    if not isinstance(value, str):
        return "static"
    
    if is_dynamic_id(value):
        return "dynamic_id"
    elif is_dynamic_name(value):
        return "dynamic_name"
    elif is_environment(value):
        return "environment"
    else:
        return "static"


def categorize_variables(data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Tüm değişkenleri kategorilere ayıran ana fonksiyon
    
    Returns:
        {
            "dynamic_variable_by_id": [{"dynamic_id": "ND123", "variable_name": "var_name", "target_variable": "output"}],
            "dynamic_variable_by_name": [{"node_name": "user", "variable_name": "var_name", "target_variable": "name"}],
            "environment_variables": [{"variable_name": "var_name", "env_variable": "API_KEY"}],
            "static_variables": [{"variable_name": "var_name", "value": "static_value"}]
        }
    """
    result = {
        "dynamic_variable_by_id": [],
        "dynamic_variable_by_name": [],
        "environment_variables": [],
        "static_variables": []
    }
    
    for var_name, value in data.items():
        value_type = get_value_type(value)
        
        if value_type == "dynamic_id":
            node_id, node_variable = extract_dynamic_id(value)
            result["dynamic_variable_by_id"].append({
                "dynamic_id": node_id,
                "variable_name": var_name,
                "target_variable": node_variable
            })
        
        elif value_type == "dynamic_name":
            node_name, node_variable = extract_dynamic_name(value)
            result["dynamic_variable_by_name"].append({
                "node_name": node_name,
                "variable_name": var_name,
                "target_variable": node_variable
            })
        
        elif value_type == "environment":
            env_var = extract_environment(value)
            result["environment_variables"].append({
                "variable_name": var_name,
                "env_variable": env_var
            })
        
        else:  # static
            result["static_variables"].append({
                "variable_name": var_name,
                "value": value
            })
    
    return result


def main():
    """Test fonksiyonu"""
    test_data = {
        "var1": "{{ node_name.node_variable}}",
        "var2": "{{ND123.node_variable}}",
        "var3": "{${API_KEY}}",
        "var4": 10.0,
        "var5": "{{ user.name }}",
        "var6": "{{ND456.output}}",
        "var7": "{${DATABASE_URL}}",
        "var8": "normal_string",
        "var9": True
    }
    
    print("=== DYNAMIC VALUE PROCESSOR ===\n")
    
    print("=== KATEGORİZE EDİLMİŞ DEĞİŞKENLER ===")
    result = categorize_variables(test_data)
    print("Çıktı formatı:")
    for category, items in result.items():
        print(f"\n{category}:")
        for i, item in enumerate(items, 1):
            print(f"  {i:2d}. {item}")


if __name__ == "__main__":
    main()