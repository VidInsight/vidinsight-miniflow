#!/usr/bin/env python3
"""
CPU Intensive Fibonacci Calculator
Recursive computation with heavy CPU load for auto scaling tests
"""

import time
import math
import json

class CPUFibonacciCalculator:
    def __init__(self):
        self.name = "CPU Fibonacci Calculator"

    def fibonacci_recursive(self, n):
        """Intentionally inefficient recursive Fibonacci for CPU load"""
        if n <= 1:
            return n
        
        # Add extra CPU work during recursion
        for _ in range(100):
            _ = math.sin(n) * math.cos(n)
            _ = math.sqrt(abs(n)) if n > 0 else 0
        
        return self.fibonacci_recursive(n-1) + self.fibonacci_recursive(n-2)

    def fibonacci_iterative_heavy(self, n):
        """CPU intensive iterative Fibonacci with extra computations"""
        if n <= 1:
            return n
        
        a, b = 0, 1
        fibonacci_sequence = [a, b]
        
        for i in range(2, n + 1):
            # Basic Fibonacci
            c = a + b
            fibonacci_sequence.append(c)
            a, b = b, c
            
            # Add CPU intensive calculations
            for _ in range(500):  # CPU burn
                _ = math.factorial(min(i, 10)) % 997
                _ = pow(i, 3) % 1009
                _ = math.sin(i) + math.cos(i)
            
            # Complex mathematical operations
            if i % 5 == 0:
                # More intensive operations every 5 iterations
                for _ in range(1000):
                    _ = math.sqrt(c) if c > 0 else 0
                    _ = math.log(c + 1)
                    _ = math.exp(min(c/1000000, 10))  # Prevent overflow
        
        return fibonacci_sequence

    def calculate_fibonacci_stats(self, fibonacci_sequence):
        """CPU intensive statistical calculations on Fibonacci sequence"""
        print("🔥 Calculating intensive Fibonacci statistics...")
        
        # Basic statistics with CPU burn
        total_sum = 0
        for num in fibonacci_sequence:
            total_sum += num
            # Extra CPU work for each number
            for _ in range(50):
                _ = math.sqrt(num) if num > 0 else 0
                _ = math.sin(num / 1000000) if num > 0 else 0
        
        # More complex statistics
        mean = total_sum / len(fibonacci_sequence) if fibonacci_sequence else 0
        
        # Variance calculation with extra CPU work
        variance = 0
        for num in fibonacci_sequence:
            diff = num - mean
            variance += diff * diff
            # CPU burn during variance calculation
            for _ in range(20):
                _ = math.pow(diff, 2)
                _ = math.cos(diff / 1000) if diff != 0 else 0
        
        variance = variance / len(fibonacci_sequence) if fibonacci_sequence else 0
        std_dev = math.sqrt(variance)
        
        # Golden ratio approximations with CPU intensive calculations
        golden_ratios = []
        for i in range(1, min(len(fibonacci_sequence) - 1, 20)):
            if fibonacci_sequence[i] != 0:
                ratio = fibonacci_sequence[i + 1] / fibonacci_sequence[i]
                golden_ratios.append(ratio)
                
                # Extra CPU work for each ratio
                for _ in range(100):
                    _ = math.sin(ratio) * math.cos(ratio)
                    _ = math.pow(ratio, 2)
        
        avg_golden_ratio = sum(golden_ratios) / len(golden_ratios) if golden_ratios else 0
        
        return {
            "sum": total_sum,
            "mean": mean,
            "variance": variance,
            "std_deviation": std_dev,
            "golden_ratio_approximation": avg_golden_ratio,
            "sequence_length": len(fibonacci_sequence)
        }

    def fibonacci_operations(self, fibonacci_n, matrix_result, iterations):
        """Perform CPU intensive Fibonacci operations"""
        print(f"🔥 Starting Fibonacci calculations: F({fibonacci_n}), {iterations} iterations")
        print(f"📊 Using matrix_result from previous task: {matrix_result}")
        
        start_time = time.time()
        
        # Adjust Fibonacci number based on matrix result (dependency usage)
        adjusted_n = max(20, min(fibonacci_n + int(abs(matrix_result) % 10), 40))
        print(f"⚡ Adjusted Fibonacci number: {adjusted_n} (based on matrix result)")
        
        all_results = []
        fibonacci_sums = []
        
        for iteration in range(iterations):
            print(f"🔥 Fibonacci iteration {iteration + 1}/{iterations}")
            
            # Calculate Fibonacci sequence (CPU intensive)
            fib_sequence = self.fibonacci_iterative_heavy(adjusted_n)
            
            # Calculate statistics (more CPU intensive)
            stats = self.calculate_fibonacci_stats(fib_sequence)
            
            all_results.append({
                "iteration": iteration + 1,
                "fibonacci_number": adjusted_n,
                "last_fibonacci": fib_sequence[-1] if fib_sequence else 0,
                "statistics": stats
            })
            
            fibonacci_sums.append(stats["sum"])
            
            # Extra CPU burn between iterations
            for _ in range(5000):
                _ = math.factorial(10) % 997
                _ = math.sin(iteration) * math.cos(iteration)
            
            elapsed = time.time() - start_time
            print(f"⚡ CPU BURN: Iteration {iteration + 1} completed in {elapsed:.2f}s")
            
            # Recursive Fibonacci for small numbers (extra CPU load)
            if adjusted_n <= 30:
                recursive_result = self.fibonacci_recursive(min(adjusted_n, 25))
                print(f"🔥 Recursive F({min(adjusted_n, 25)}) = {recursive_result}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Final aggregated statistics with CPU burn
        total_fibonacci_sum = sum(fibonacci_sums)
        avg_fibonacci_sum = total_fibonacci_sum / len(fibonacci_sums) if fibonacci_sums else 0
        
        # Complex final calculations
        final_golden_ratio = sum(r["statistics"]["golden_ratio_approximation"] for r in all_results) / len(all_results) if all_results else 0
        
        result = {
            "operation": "fibonacci_calculation",
            "fibonacci_n": adjusted_n,
            "iterations": iterations,
            "fibonacci_result": all_results[-1]["last_fibonacci"] if all_results else 0,
            "fibonacci_sum": total_fibonacci_sum,
            "avg_fibonacci_sum": avg_fibonacci_sum,
            "golden_ratio_avg": final_golden_ratio,
            "execution_time": duration,
            "cpu_intensity": "EXTREME",
            "matrix_dependency": matrix_result,
            "calculations_per_second": (adjusted_n * iterations) / duration if duration > 0 else 0,
            "status": "success"
        }
        
        print(f"✅ Fibonacci operations completed: F({adjusted_n}) in {duration:.2f}s")
        print(f"🔥 CPU Usage: EXTREME - {(adjusted_n * iterations)/duration:.1f} calc/sec")
        
        return result

    def run(self, context=None):
        """Main execution method called by the engine"""
        try:
            # Get parameters from context
            fibonacci_n = context.get("fibonacci_n", 35) if context else 35
            matrix_result = context.get("matrix_result", 1000.0) if context else 1000.0
            iterations = context.get("iterations", 5) if context else 5
            

            
            # Execute CPU intensive Fibonacci operations
            result = self.fibonacci_operations(fibonacci_n, matrix_result, iterations)
            
            # Return result as JSON string
            return json.dumps(result)
            
        except Exception as e:
            error_result = {
                "operation": "fibonacci_calculation",
                "status": "failed",
                "error_message": str(e),
                "cpu_intensity": "EXTREME"
            }
            return json.dumps(error_result)

def module():
    """Engine required module function"""
    return CPUFibonacciCalculator() 