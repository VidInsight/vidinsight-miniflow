"""
Main test runner for all DatabaseOrchestration manual tests
Execute this file to run all orchestration tests
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import all test modules
from workflow_functions import run_all_workflow_tests
from script_functions import run_all_script_tests
from environment_functions import run_all_environment_tests
from execution_functions import run_all_execution_tests

def main():
    """Run all orchestration tests"""
    print("🚀 MINIFLOW ORCHESTRATION MANUAL TESTS")
    print("=" * 60)
    print("Running comprehensive tests for DatabaseOrchestration class")
    print("=" * 60)
    
    try:
        # Run workflow tests
        print("\n📋 WORKFLOW FUNCTIONS")
        print("-" * 30)
        run_all_workflow_tests()
        
        # Run script tests
        print("\n🔧 SCRIPT FUNCTIONS")
        print("-" * 30)
        run_all_script_tests()
        
        # Run environment tests
        print("\n🌍 ENVIRONMENT FUNCTIONS")
        print("-" * 30)
        run_all_environment_tests()
        
        # Run execution tests
        print("\n⚡ EXECUTION FUNCTIONS")
        print("-" * 30)
        run_all_execution_tests()
        
        print("\n" + "=" * 60)
        print("🎉 ALL ORCHESTRATION TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR RUNNING TESTS: {e}")
        print("=" * 60)
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
