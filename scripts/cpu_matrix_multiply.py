#!/usr/bin/env python3
"""
CPU Intensive Matrix Multiplication
Heavy linear algebra operations for auto scaling tests
"""

import time
import math
import json
import random

class CPUMatrixMultiplier:
    def __init__(self):
        self.name = "CPU Matrix Multiplier"

    def create_random_matrix(self, size):
        """Create a random matrix of given size"""
        return [[random.uniform(-100, 100) for _ in range(size)] for _ in range(size)]

    def matrix_multiply(self, a, b):
        """CPU intensive matrix multiplication (intentionally inefficient)"""
        size = len(a)
        result = [[0 for _ in range(size)] for _ in range(size)]
        
        for i in range(size):
            for j in range(size):
                for k in range(size):
                    result[i][j] += a[i][k] * b[k][j]
                    # Add extra CPU work
                    _ = math.sin(a[i][k]) * math.cos(b[k][j])
        
        return result

    def calculate_determinant(self, matrix):
        """CPU intensive determinant calculation"""
        size = len(matrix)
        if size == 1:
            return matrix[0][0]
        if size == 2:
            return matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
        
        det = 0
        for col in range(size):
            # Create submatrix (CPU intensive)
            submatrix = []
            for row in range(1, size):
                subrow = []
                for subcol in range(size):
                    if subcol != col:
                        subrow.append(matrix[row][subcol])
                submatrix.append(subrow)
            
            # Recursive calculation with extra CPU work
            sub_det = self.calculate_determinant(submatrix)
            det += ((-1) ** col) * matrix[0][col] * sub_det
            
            # Extra CPU burn
            for _ in range(100):
                _ = math.sqrt(abs(det)) if det != 0 else 0
        
        return det

    def matrix_operations(self, matrix_size, iterations, prime_count):
        """Perform CPU intensive matrix operations"""
        print(f"🔥 Starting matrix operations: {matrix_size}x{matrix_size}, {iterations} iterations")
        print(f"📊 Using prime_count from previous task: {prime_count}")
        
        start_time = time.time()
        total_operations = 0
        determinants = []
        
        for iteration in range(iterations):
            print(f"⚡ Matrix iteration {iteration + 1}/{iterations}")
            
            # Create matrices with CPU intensive random generation
            matrix_a = self.create_random_matrix(matrix_size)
            matrix_b = self.create_random_matrix(matrix_size)
            
            # Scale matrices based on prime count (dependency usage)
            scale_factor = math.sqrt(prime_count) / 100.0
            for i in range(matrix_size):
                for j in range(matrix_size):
                    matrix_a[i][j] *= scale_factor
                    matrix_b[i][j] *= scale_factor
            
            # CPU intensive matrix multiplication
            result_matrix = self.matrix_multiply(matrix_a, matrix_b)
            total_operations += matrix_size ** 3
            
            # CPU intensive determinant calculation
            det_a = self.calculate_determinant(matrix_a)
            det_b = self.calculate_determinant(matrix_b)
            det_result = self.calculate_determinant(result_matrix)
            
            determinants.extend([det_a, det_b, det_result])
            
            # Extra CPU burn with complex calculations
            for i in range(matrix_size):
                for j in range(matrix_size):
                    # Trigonometric CPU burn
                    _ = math.sin(result_matrix[i][j]) + math.cos(result_matrix[i][j])
                    _ = math.pow(abs(result_matrix[i][j]), 0.5)
            
            elapsed = time.time() - start_time
            print(f"🔥 CPU BURN: Iteration {iteration + 1} completed in {elapsed:.2f}s")
            
            # Intentional CPU intensive sleep simulation
            cpu_burn_cycles = 10000
            for _ in range(cpu_burn_cycles):
                _ = math.factorial(10) % 997
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Final CPU intensive calculations
        avg_determinant = sum(determinants) / len(determinants) if determinants else 0
        max_determinant = max(determinants) if determinants else 0
        min_determinant = min(determinants) if determinants else 0
        
        # Complex statistical calculations for CPU burn
        variance = sum((d - avg_determinant) ** 2 for d in determinants) / len(determinants) if determinants else 0
        std_dev = math.sqrt(variance)
        
        result = {
            "operation": "matrix_multiplication",
            "matrix_size": matrix_size,
            "iterations": iterations,
            "total_operations": total_operations,
            "determinant": avg_determinant,
            "max_determinant": max_determinant,
            "min_determinant": min_determinant,
            "std_deviation": std_dev,
            "execution_time": duration,
            "cpu_intensity": "VERY_HIGH",
            "operations_per_second": total_operations / duration if duration > 0 else 0,
            "prime_dependency": prime_count,
            "status": "success"
        }
        
        print(f"✅ Matrix operations completed: {total_operations} ops in {duration:.2f}s")
        print(f"🔥 CPU Usage: VERY HIGH - {total_operations/duration:.1f} ops/sec")
        
        return result

    def run(self, context=None):
        """Main execution method called by the engine"""
        try:
            # Get parameters from context
            matrix_size = context.get("matrix_size", 500) if context else 500
            iterations = context.get("iterations", 10) if context else 10
            prime_count = context.get("prime_count", 1000) if context else 1000
            

            
            # Execute CPU intensive matrix operations
            result = self.matrix_operations(matrix_size, iterations, prime_count)
            
            # Return result as JSON string
            return json.dumps(result)
            
        except Exception as e:
            error_result = {
                "operation": "matrix_multiplication",
                "status": "failed", 
                "error_message": str(e),
                "cpu_intensity": "VERY_HIGH"
            }
            return json.dumps(error_result)

def module():
    """Engine required module function"""
    return CPUMatrixMultiplier() 