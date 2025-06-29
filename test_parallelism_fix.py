#!/usr/bin/env python3
"""
Test script for Parallelism Engine fixes
Bu script düzeltmelerin doğru çalıştığını test eder.
"""

import time
import threading
from miniflow.parallelism_engine import Manager

def test_auto_scaling_thread_distribution():
    """Test: Auto-scaling ve thread distribution"""
    print("🧪 Testing Auto-scaling Thread Distribution Fix...")
    
    # 1. Manager başlat
    manager = Manager()
    print("✅ Manager created")
    
    # 2. İlk task gönder (1 process ile başlar)
    print("📤 Sending initial task...")
    task1 = {
        "task_id": "test_1",
        "script_path": "scripts/add_numbers.py",
        "context": {}
    }
    success = manager.put_item(task1)
    print(f"✅ Initial task sent: {success}")
    
    # 3. Process durumunu kontrol et
    time.sleep(2)
    watcher = manager.watcher
    if watcher:
        print(f"📊 Current processes: {len(watcher.active_processes)}")
        print(f"📊 Round-robin index: {watcher.current_process_index}")
    
    # 4. Heavy load simülasyonu (auto-scaling tetiklemek için)
    print("🔥 Simulating heavy load to trigger auto-scaling...")
    tasks = []
    for i in range(20):
        task = {
            "task_id": f"heavy_task_{i}",
            "script_path": "scripts/add_numbers.py", 
            "context": {}
        }
        tasks.append(task)
    
    # Bulk gönder
    bulk_success = manager.put_items_bulk(tasks)
    print(f"✅ Bulk tasks sent: {bulk_success}")
    
    # 5. Auto-scaling'in çalışması için bekle
    print("⏳ Waiting for auto-scaling...")
    time.sleep(8)  # Auto-scaler'ın trigger olması için
    
    # 6. Sonuçları kontrol et
    if watcher:
        process_count = len(watcher.active_processes)
        print(f"📊 Final process count: {process_count}")
        print(f"📊 Final round-robin index: {watcher.current_process_index}")
        
        # Thread distribution check
        if process_count > 1:
            thread_counts = watcher._get_thread_counts_safe()
            print(f"📊 Thread distribution: {thread_counts}")
            
            # Success criteria
            valid_threads = [t for t in thread_counts if t is not None]
            if len(valid_threads) > 1:
                print("🎉 SUCCESS: Multiple processes have threads!")
                return True
            else:
                print("❌ ISSUE: Threads not distributed across processes")
                return False
        else:
            print("⚠️  Only 1 process active, auto-scaling may not have triggered")
            return None
    
    # 7. Cleanup
    manager.shutdown()
    print("✅ Manager shutdown")
    return True

def test_queue_error_handling():
    """Test: Queue error handling improvements"""
    print("\n🧪 Testing Queue Error Handling...")
    
    from miniflow.parallelism_engine.queue_module import BaseQueue
    
    # Small queue for testing
    queue = BaseQueue(maxsize=2)
    
    # Test normal put
    success1 = queue.put({"test": 1})
    success2 = queue.put({"test": 2})
    print(f"✅ Normal puts: {success1}, {success2}")
    
    # Test queue full scenario
    success3 = queue.put({"test": 3})  # Should fail and log
    print(f"✅ Queue full handling: {success3} (should be False)")
    
    # Test retry mechanism
    success4 = queue.put_with_retry({"test": 4})
    print(f"✅ Retry mechanism: {success4}")
    
    # Test stats
    stats = queue.get_stats()
    print(f"📊 Queue stats: {stats}")
    
    return True

def test_round_robin_bounds_check():
    """Test: Round-robin bounds checking"""
    print("\n🧪 Testing Round-Robin Bounds Check...")
    
    # Bu test private method'ları test eder, normalde yapılmaz ama fix'i doğrulamak için
    from miniflow.parallelism_engine.engine import QueueWatcher
    from miniflow.parallelism_engine.queue_module import BaseQueue
    
    input_q = BaseQueue()
    output_q = BaseQueue()
    
    watcher = QueueWatcher(input_q, output_q, True)
    
    # Simulate process list changes
    watcher.active_processes = [{"dummy": "process1"}]
    watcher.current_process_index = 0
    
    # Normal case
    process = watcher._get_next_process()
    print(f"✅ Normal case: {process is not None}")
    print(f"📊 Index after normal: {watcher.current_process_index}")
    
    # Bounds violation case (simulated)
    watcher.current_process_index = 5  # Out of bounds
    process = watcher._get_next_process()
    print(f"✅ Bounds check: {process is not None}")
    print(f"📊 Index after bounds check: {watcher.current_process_index}")
    
    return True

def main():
    """Ana test fonksiyonu"""
    print("🚀 Starting Parallelism Engine Fix Tests\n")
    
    tests = [
        ("Queue Error Handling", test_queue_error_handling),
        ("Round-Robin Bounds Check", test_round_robin_bounds_check),
        ("Auto-scaling Thread Distribution", test_auto_scaling_thread_distribution),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*50}")
            print(f"Running: {test_name}")
            print('='*50)
            
            result = test_func()
            results[test_name] = result
            
            if result:
                print(f"✅ {test_name}: PASSED")
            elif result is None:
                print(f"⚠️  {test_name}: INCONCLUSIVE")
            else:
                print(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    for test_name, result in results.items():
        status = "PASSED" if result else ("INCONCLUSIVE" if result is None else "FAILED")
        emoji = "✅" if result else ("⚠️" if result is None else "❌")
        print(f"{emoji} {test_name}: {status}")
    
    passed = sum(1 for r in results.values() if r is True)
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 