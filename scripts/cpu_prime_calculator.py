#!/usr/bin/env python3
"""
CPU Intensive Prime Number Calculator
Designed to stress test auto scaling system
"""

import time
import math
import json

class CPUPrimeCalculator:
    def __init__(self):
        self.name = "CPU Prime Calculator"
    
    def is_prime(self, n):
        """CPU intensive prime check"""
        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False
        
        # Intentionally inefficient for CPU load
        for i in range(3, int(math.sqrt(n)) + 1, 2):
            if n % i == 0:
                return False
            # Add some extra computation to increase CPU load
            _ = math.sin(i) * math.cos(i)
        return True

    def calculate_primes(self, max_number, task_duration):
        """Calculate primes with heavy CPU usage"""
        print(f"🔥 Starting CPU intensive prime calculation up to {max_number}")
        start_time = time.time()
        
        primes = []
        prime_count = 0
        
        # Calculate primes with intentional CPU burn
        for num in range(2, max_number + 1):
            if self.is_prime(num):
                primes.append(num)
                prime_count += 1
                
                # Add extra CPU work every 100 primes
                if prime_count % 100 == 0:
                    # Intentional CPU burn - complex calculations
                    for _ in range(1000):
                        _ = math.factorial(10) / math.sqrt(num)
                        _ = pow(num, 3) % 997
                    
                    print(f"⚡ Found {prime_count} primes so far... (CPU burning)")
            
            # Periodic CPU intensive operations
            if num % 1000 == 0:
                # Matrix multiplication for CPU load
                matrix_a = [[i*j for j in range(20)] for i in range(20)]
                matrix_b = [[j*i for j in range(20)] for i in range(20)]
                result = [[sum(a*b for a, b in zip(row_a, col_b)) 
                          for col_b in zip(*matrix_b)] for row_a in matrix_a]
                
                elapsed = time.time() - start_time
                print(f"🔥 CPU BURN: Processed {num}/{max_number} numbers in {elapsed:.2f}s")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Calculate some statistics with more CPU work
        largest_prime = max(primes) if primes else 0
        prime_sum = sum(primes)
        
        # Extra CPU intensive final calculations
        prime_squares = [p*p for p in primes[-100:]]  # Last 100 primes squared
        geometric_mean = pow(math.prod(primes[-10:]), 1/10) if len(primes) >= 10 else 0
        
        result = {
            "operation": "prime_calculation",
            "max_number": max_number,
            "prime_count": prime_count,
            "largest_prime": largest_prime,
            "prime_sum": prime_sum,
            "execution_time": duration,
            "cpu_intensity": "HIGH",
            "primes_per_second": prime_count / duration if duration > 0 else 0,
            "geometric_mean_last_10": geometric_mean,
            "status": "success"
        }
        
        print(f"✅ Prime calculation completed: {prime_count} primes in {duration:.2f}s")
        print(f"🔥 CPU Usage: HIGH - {prime_count/duration:.1f} primes/sec")
        
        return result

    def run(self, context=None):
        """Main execution method called by the engine"""
        try:
            # Get parameters from context
            max_number = context.get("max_number", 100000) if context else 100000
            task_duration = context.get("task_duration", 15) if context else 15
            
            print(f"🚀 CPU Prime Calculator Starting")
            print(f"📊 Parameters: max_number={max_number}, duration={task_duration}s")
            
            # Execute CPU intensive prime calculation
            result = self.calculate_primes(max_number, task_duration)
            
            # Return result as JSON string
            return json.dumps(result)
            
        except Exception as e:
            error_result = {
                "operation": "prime_calculation", 
                "status": "failed",
                "error_message": str(e),
                "cpu_intensity": "HIGH"
            }
            return json.dumps(error_result)

def module():
    """Engine required module function"""
    return CPUPrimeCalculator() 