#!/usr/bin/env python3
"""
Auto Scaling Test Script
Triggers multiple CPU intensive workflows to test auto scaling behavior
"""

import time
import json
import subprocess
import threading
import psutil
import os
from datetime import datetime

def monitor_system_resources():
    """Monitor CPU, memory, and process count"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    process_count = len(psutil.pids())
    
    return {
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "memory_available_gb": memory.available / (1024**3),
        "process_count": process_count
    }

def trigger_workflow(workflow_name, workflow_count):
    """Trigger a single workflow execution"""
    try:
        print(f"🚀 Triggering workflow: {workflow_name} (#{workflow_count})")
        
        cmd = ["python", "-m", "miniflow", "trigger", workflow_name]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ Workflow {workflow_name} #{workflow_count} triggered successfully")
            return True
        else:
            print(f"❌ Workflow {workflow_name} #{workflow_count} failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Workflow {workflow_name} #{workflow_count} timed out")
        return False
    except Exception as e:
        print(f"💥 Error triggering workflow {workflow_name} #{workflow_count}: {e}")
        return False

def monitor_miniflow_processes():
    """Monitor miniflow-related processes"""
    miniflow_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
        try:
            if 'miniflow' in ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else '':
                miniflow_processes.append({
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "cpu_percent": proc.info['cpu_percent'],
                    "memory_percent": proc.info['memory_percent']
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return miniflow_processes

def run_auto_scaling_test():
    """Run comprehensive auto scaling test"""
    print("🎯 STARTING AUTO SCALING TEST")
    print("=" * 60)
    
    # Test configuration
    workflow_file = "cpu_intensive_workflow.json"
    num_workflows = 8  # Trigger 8 workflows to stress test
    monitoring_duration = 300  # Monitor for 5 minutes
    
    # Pre-test system state
    print("📊 PRE-TEST SYSTEM STATE:")
    initial_state = monitor_system_resources()
    print(f"CPU: {initial_state['cpu_percent']:.1f}%")
    print(f"Memory: {initial_state['memory_percent']:.1f}%")
    print(f"Processes: {initial_state['process_count']}")
    print()
    
    # Start system monitoring in background
    monitoring_data = []
    monitoring_active = True
    
    def system_monitor():
        while monitoring_active:
            data = monitor_system_resources()
            miniflow_procs = monitor_miniflow_processes()
            data['miniflow_processes'] = len(miniflow_procs)
            data['miniflow_cpu_total'] = sum(p['cpu_percent'] for p in miniflow_procs)
            monitoring_data.append(data)
            time.sleep(2)  # Monitor every 2 seconds
    
    monitor_thread = threading.Thread(target=system_monitor, daemon=True)
    monitor_thread.start()
    
    # Trigger workflows with staggered timing
    print(f"🚀 TRIGGERING {num_workflows} CPU INTENSIVE WORKFLOWS")
    print("Each workflow has 5 sequential CPU intensive tasks")
    print()
    
    workflow_threads = []
    workflow_results = []
    
    for i in range(num_workflows):
        # Stagger workflow triggers by 3 seconds
        if i > 0:
            print(f"⏱️  Waiting 3 seconds before next workflow...")
            time.sleep(3)
        
        # Trigger workflow in separate thread
        def trigger_workflow_thread(workflow_num):
            result = trigger_workflow(workflow_file, workflow_num)
            workflow_results.append({
                "workflow_num": workflow_num,
                "success": result,
                "timestamp": datetime.now().isoformat()
            })
        
        thread = threading.Thread(target=trigger_workflow_thread, args=(i+1,))
        thread.start()
        workflow_threads.append(thread)
        
        # Monitor system after each trigger
        current_state = monitor_system_resources()
        print(f"📊 After workflow {i+1}: CPU={current_state['cpu_percent']:.1f}%, "
              f"Memory={current_state['memory_percent']:.1f}%, "
              f"Processes={current_state['process_count']}")
    
    print()
    print("🔥 ALL WORKFLOWS TRIGGERED - MONITORING AUTO SCALING BEHAVIOR")
    print("=" * 60)
    
    # Monitor for scaling behavior
    start_time = time.time()
    max_cpu = 0
    max_memory = 0
    max_processes = 0
    scaling_events = []
    
    while time.time() - start_time < monitoring_duration:
        current_state = monitor_system_resources()
        miniflow_procs = monitor_miniflow_processes()
        
        # Track maximums
        max_cpu = max(max_cpu, current_state['cpu_percent'])
        max_memory = max(max_memory, current_state['memory_percent'])
        max_processes = max(max_processes, len(miniflow_procs))
        
        # Detect scaling events (significant process count changes)
        if len(monitoring_data) > 5:
            recent_proc_counts = [d['miniflow_processes'] for d in monitoring_data[-5:]]
            if max(recent_proc_counts) - min(recent_proc_counts) >= 2:
                scaling_events.append({
                    "timestamp": current_state['timestamp'],
                    "process_change": max(recent_proc_counts) - min(recent_proc_counts),
                    "current_processes": len(miniflow_procs),
                    "cpu_percent": current_state['cpu_percent']
                })
        
        # Print status every 30 seconds
        elapsed = time.time() - start_time
        if int(elapsed) % 30 == 0 and int(elapsed) > 0:
            print(f"⏱️  {int(elapsed)}s: CPU={current_state['cpu_percent']:.1f}%, "
                  f"Memory={current_state['memory_percent']:.1f}%, "
                  f"MiniFlow Processes={len(miniflow_procs)}")
        
        time.sleep(5)  # Check every 5 seconds
    
    # Stop monitoring
    monitoring_active = False
    
    # Wait for all workflow threads to complete
    print("\n⏳ Waiting for all workflows to complete...")
    for thread in workflow_threads:
        thread.join(timeout=60)  # Wait max 1 minute per thread
    
    # Final analysis
    print("\n" + "=" * 60)
    print("🎯 AUTO SCALING TEST RESULTS")
    print("=" * 60)
    
    # Workflow results
    successful_workflows = sum(1 for r in workflow_results if r['success'])
    print(f"📊 Workflow Execution Results:")
    print(f"   Total Triggered: {num_workflows}")
    print(f"   Successful: {successful_workflows}")
    print(f"   Failed: {num_workflows - successful_workflows}")
    print(f"   Success Rate: {successful_workflows/num_workflows*100:.1f}%")
    
    # System performance
    print(f"\n📊 System Performance:")
    print(f"   Peak CPU Usage: {max_cpu:.1f}%")
    print(f"   Peak Memory Usage: {max_memory:.1f}%")
    print(f"   Peak MiniFlow Processes: {max_processes}")
    
    # Auto scaling analysis
    print(f"\n🔄 Auto Scaling Analysis:")
    print(f"   Scaling Events Detected: {len(scaling_events)}")
    
    if scaling_events:
        print("   Scaling Timeline:")
        for event in scaling_events[:5]:  # Show first 5 events
            print(f"     {event['timestamp']}: "
                  f"Process change: +{event['process_change']}, "
                  f"Total processes: {event['current_processes']}, "
                  f"CPU: {event['cpu_percent']:.1f}%")
    
    # CPU load analysis
    if monitoring_data:
        avg_cpu = sum(d['cpu_percent'] for d in monitoring_data) / len(monitoring_data)
        cpu_above_50 = sum(1 for d in monitoring_data if d['cpu_percent'] > 50)
        cpu_above_80 = sum(1 for d in monitoring_data if d['cpu_percent'] > 80)
        
        print(f"\n🔥 CPU Load Analysis:")
        print(f"   Average CPU: {avg_cpu:.1f}%")
        print(f"   Time above 50%: {cpu_above_50/len(monitoring_data)*100:.1f}%")
        print(f"   Time above 80%: {cpu_above_80/len(monitoring_data)*100:.1f}%")
        
        # Auto scaling effectiveness
        if max_cpu > 70:
            print(f"✅ High CPU load achieved ({max_cpu:.1f}%) - Good for testing auto scaling")
        else:
            print(f"⚠️  Moderate CPU load ({max_cpu:.1f}%) - May need more intensive tasks")
    
    # Save detailed results
    test_results = {
        "test_config": {
            "workflow_file": workflow_file,
            "num_workflows": num_workflows,
            "monitoring_duration": monitoring_duration
        },
        "workflow_results": workflow_results,
        "system_performance": {
            "max_cpu": max_cpu,
            "max_memory": max_memory,
            "max_processes": max_processes
        },
        "scaling_events": scaling_events,
        "monitoring_data": monitoring_data[-10:]  # Last 10 data points
    }
    
    with open("auto_scaling_test_results.json", "w") as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: auto_scaling_test_results.json")
    print("🎯 AUTO SCALING TEST COMPLETED")

if __name__ == "__main__":
    try:
        run_auto_scaling_test()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc() 