#!/usr/bin/env python3
"""
CPU Intensive Final Aggregation
Complex statistical analysis and data aggregation for auto scaling tests
"""

import time
import math
import json
import sys
import statistics

class CPUFinalAggregator:
    def __init__(self):
        self.name = "CPU Final Aggregator"

    def cpu_intensive_statistical_analysis(self, data_points):
        """Perform CPU intensive statistical calculations"""
        if not data_points:
            return {}
        
        print("🔥 Performing intensive statistical analysis...")
        
        # Basic statistics with CPU burn
        total_sum = 0
        for value in data_points:
            total_sum += value
            # Extra CPU work for each value
            for _ in range(200):
                _ = math.sin(value / 1000) * math.cos(value / 1000)
                _ = math.sqrt(abs(value)) if value >= 0 else math.sqrt(abs(value))
        
        mean = total_sum / len(data_points)
        
        # Variance and standard deviation with CPU burn
        variance_sum = 0
        for value in data_points:
            diff = value - mean
            variance_sum += diff * diff
            
            # CPU intensive operations during variance calculation
            for _ in range(100):
                _ = math.pow(diff, 2)
                _ = math.exp(min(abs(diff) / 1000000, 10))  # Prevent overflow
        
        variance = variance_sum / len(data_points)
        std_dev = math.sqrt(variance)
        
        # Advanced statistical measures with CPU burn
        sorted_data = sorted(data_points)
        median = statistics.median(sorted_data)
        
        # Quartiles with CPU intensive calculations
        q1 = statistics.quantiles(sorted_data, n=4)[0] if len(sorted_data) >= 4 else sorted_data[0]
        q3 = statistics.quantiles(sorted_data, n=4)[2] if len(sorted_data) >= 4 else sorted_data[-1]
        iqr = q3 - q1
        
        # Skewness calculation (CPU intensive)
        skewness = 0
        for value in data_points:
            normalized = (value - mean) / std_dev if std_dev > 0 else 0
            skewness += normalized ** 3
            
            # Extra CPU work
            for _ in range(50):
                _ = math.pow(normalized, 3)
                _ = math.sin(normalized) if abs(normalized) < 100 else 0
        
        skewness = skewness / len(data_points) if data_points else 0
        
        # Kurtosis calculation (very CPU intensive)
        kurtosis = 0
        for value in data_points:
            normalized = (value - mean) / std_dev if std_dev > 0 else 0
            kurtosis += normalized ** 4
            
            # Extra CPU work
            for _ in range(75):
                _ = math.pow(normalized, 4)
                _ = math.cos(normalized) if abs(normalized) < 100 else 0
        
        kurtosis = (kurtosis / len(data_points)) - 3 if data_points else 0  # Excess kurtosis
        
        return {
            "count": len(data_points),
            "sum": total_sum,
            "mean": mean,
            "median": median,
            "variance": variance,
            "std_deviation": std_dev,
            "min": min(data_points),
            "max": max(data_points),
            "range": max(data_points) - min(data_points),
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "skewness": skewness,
            "kurtosis": kurtosis
        }

    def cpu_intensive_correlation_analysis(self, dataset1, dataset2):
        """Calculate correlation with CPU intensive operations"""
        if len(dataset1) != len(dataset2) or not dataset1:
            return 0
        
        print("🔥 Calculating intensive correlation analysis...")
        
        # Means with CPU burn
        mean1 = sum(dataset1) / len(dataset1)
        mean2 = sum(dataset2) / len(dataset2)
        
        # Covariance calculation with CPU intensive operations
        covariance = 0
        sum_sq1 = 0
        sum_sq2 = 0
        
        for i in range(len(dataset1)):
            diff1 = dataset1[i] - mean1
            diff2 = dataset2[i] - mean2
            
            covariance += diff1 * diff2
            sum_sq1 += diff1 * diff1
            sum_sq2 += diff2 * diff2
            
            # Extra CPU work for each calculation
            for _ in range(300):
                _ = math.sin(diff1) * math.cos(diff2)
                _ = math.pow(diff1, 2) + math.pow(diff2, 2)
                _ = math.sqrt(abs(diff1 * diff2)) if diff1 * diff2 >= 0 else 0
        
        # Correlation coefficient
        denominator = math.sqrt(sum_sq1 * sum_sq2)
        correlation = covariance / denominator if denominator > 0 else 0
        
        return correlation

    def generate_synthetic_datasets(self, base_values):
        """Generate synthetic datasets for analysis with CPU burn"""
        print("🔥 Generating synthetic datasets...")
        
        datasets = {}
        
        # Dataset 1: Logarithmic transformations
        log_dataset = []
        for value in base_values:
            log_val = math.log(abs(value) + 1)  # Add 1 to avoid log(0)
            log_dataset.append(log_val)
            
            # CPU burn during transformation
            for _ in range(100):
                _ = math.log(abs(value) + 1)
                _ = math.exp(min(log_val, 10))
        
        datasets["logarithmic"] = log_dataset
        
        # Dataset 2: Trigonometric transformations
        trig_dataset = []
        for value in base_values:
            trig_val = math.sin(value / 1000) + math.cos(value / 1000)
            trig_dataset.append(trig_val)
            
            # CPU burn during transformation
            for _ in range(150):
                _ = math.sin(value / 1000) * math.cos(value / 1000)
                _ = math.tan(value / 10000) if abs(value / 10000) < 1.5 else 0
        
        datasets["trigonometric"] = trig_dataset
        
        # Dataset 3: Polynomial transformations
        poly_dataset = []
        for value in base_values:
            poly_val = value**2 + 2*value + 1
            poly_dataset.append(poly_val)
            
            # CPU burn during transformation
            for _ in range(200):
                _ = math.pow(value, 2) + 2*value + 1
                _ = math.sqrt(abs(poly_val)) if poly_val >= 0 else 0
        
        datasets["polynomial"] = poly_dataset
        
        return datasets

    def aggregate_all_results(self, prime_count, matrix_ops, fibonacci_sum, hash_result):
        """Perform final CPU intensive aggregation of all results"""
        print(f"🔥 Final aggregation of all computational results")
        print(f"📊 Inputs: prime_count={prime_count}, matrix_ops={matrix_ops}")
        print(f"📊 fibonacci_sum={fibonacci_sum}, hash_result={hash_result}")
        
        start_time = time.time()
        
        # Create comprehensive dataset from all results
        all_values = [
            float(prime_count),
            float(matrix_ops),
            float(fibonacci_sum),
            len(hash_result) if isinstance(hash_result, str) else float(hash_result)
        ]
        
        # Expand dataset with derived values (CPU intensive)
        expanded_values = []
        for value in all_values:
            expanded_values.append(value)
            expanded_values.append(value * 2)
            expanded_values.append(value / 2 if value != 0 else 0)
            expanded_values.append(math.sqrt(abs(value)))
            expanded_values.append(value ** 1.5 if value >= 0 else -(abs(value) ** 1.5))
            
            # CPU burn for each expansion
            for _ in range(500):
                _ = math.sin(value) + math.cos(value)
                _ = math.factorial(min(int(abs(value)) % 10, 10))
        
        # Statistical analysis of main dataset
        main_stats = self.cpu_intensive_statistical_analysis(all_values)
        expanded_stats = self.cpu_intensive_statistical_analysis(expanded_values)
        
        # Generate synthetic datasets for correlation analysis
        synthetic_datasets = self.generate_synthetic_datasets(expanded_values)
        
        # Correlation matrix (very CPU intensive)
        correlations = {}
        dataset_names = list(synthetic_datasets.keys())
        
        for i, name1 in enumerate(dataset_names):
            for j, name2 in enumerate(dataset_names):
                if i <= j:  # Only calculate upper triangle
                    corr_key = f"{name1}_vs_{name2}"
                    correlation = self.cpu_intensive_correlation_analysis(
                        synthetic_datasets[name1], 
                        synthetic_datasets[name2]
                    )
                    correlations[corr_key] = correlation
        
        # Complex aggregation calculations with CPU burn
        print("🔥 Performing complex aggregation calculations...")
        
        # Weighted averages with CPU intensive weights
        weights = []
        for value in all_values:
            weight = math.sin(value / 1000) ** 2 + math.cos(value / 1000) ** 2
            weights.append(weight)
            
            # CPU burn for weight calculation
            for _ in range(300):
                _ = math.pow(weight, 2)
                _ = math.exp(min(weight, 10))
        
        weighted_sum = sum(v * w for v, w in zip(all_values, weights))
        total_weight = sum(weights)
        weighted_average = weighted_sum / total_weight if total_weight > 0 else 0
        
        # Geometric and harmonic means with CPU burn
        geometric_mean = math.pow(math.prod([abs(v) for v in all_values if v != 0]), 1/len(all_values)) if all_values else 0
        harmonic_mean = len(all_values) / sum(1/v for v in all_values if v != 0) if all_values else 0
        
        # Final CPU intensive calculations
        for _ in range(10000):
            _ = math.sin(geometric_mean) * math.cos(harmonic_mean)
            _ = math.sqrt(weighted_average)
            _ = math.factorial(10) % 997
        
        end_time = time.time()
        duration = end_time - start_time
        
        result = {
            "operation": "final_aggregation",
            "input_data": {
                "prime_count": prime_count,
                "matrix_operations": matrix_ops,
                "fibonacci_sum": fibonacci_sum,
                "hash_result_length": len(hash_result) if isinstance(hash_result, str) else hash_result
            },
            "main_statistics": main_stats,
            "expanded_statistics": expanded_stats,
            "correlations": correlations,
            "aggregated_metrics": {
                "weighted_average": weighted_average,
                "geometric_mean": geometric_mean,
                "harmonic_mean": harmonic_mean,
                "total_computational_score": sum(all_values),
                "normalized_score": sum(all_values) / len(all_values) if all_values else 0
            },
            "synthetic_datasets_count": len(synthetic_datasets),
            "total_data_points": len(expanded_values),
            "execution_time": duration,
            "cpu_intensity": "ULTIMATE",
            "calculations_per_second": len(expanded_values) * 1000 / duration if duration > 0 else 0,
            "status": "success"
        }
        
        print(f"✅ Final aggregation completed: {len(expanded_values)} points in {duration:.2f}s")
        print(f"🔥 CPU Usage: ULTIMATE - {result['calculations_per_second']:.1f} calc/sec")
        print(f"🎯 Total Computational Score: {result['aggregated_metrics']['total_computational_score']:.2f}")
        
        return result

    def run(self, context=None):
        """Main execution method called by the engine"""
        try:
            # Get parameters from all previous tasks
            prime_count = context.get("prime_count", 9592) if context else 9592
            matrix_ops = context.get("matrix_ops", 1250000000) if context else 1250000000
            fibonacci_sum = context.get("fibonacci_sum", 123456789.0) if context else 123456789.0
            hash_result = context.get("hash_result", "default_hash_result_string") if context else "default_hash_result_string"
            
            print(f"🚀 CPU Final Aggregator Starting")
            print(f"📊 Aggregating results from all previous CPU intensive tasks")
            
            # Execute final CPU intensive aggregation
            result = self.aggregate_all_results(prime_count, matrix_ops, fibonacci_sum, hash_result)
            
            # Return result as JSON string
            return json.dumps(result)
            
        except Exception as e:
            error_result = {
                "operation": "final_aggregation",
                "status": "failed",
                "error_message": str(e),
                "cpu_intensity": "ULTIMATE"
            }
            return json.dumps(error_result)

def module():
    """Engine required module function"""
    return CPUFinalAggregator() 