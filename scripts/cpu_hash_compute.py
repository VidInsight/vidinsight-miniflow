#!/usr/bin/env python3
"""
CPU Intensive Hash Computation
Cryptographic operations and hash chains for auto scaling tests
"""

import time
import math
import json
import hashlib
import hmac

class CPUHashComputer:
    def __init__(self):
        self.name = "CPU Hash Computer"

    def cpu_intensive_hash(self, data, rounds):
        """Perform CPU intensive hash computations"""
        hash_result = data.encode('utf-8')
        
        for round_num in range(rounds):
            # Multiple hash algorithms for CPU burn
            hash_result = hashlib.sha256(hash_result).digest()
            hash_result = hashlib.sha512(hash_result).digest()
            hash_result = hashlib.md5(hash_result).digest()
            
            # Add extra CPU work every 1000 rounds
            if round_num % 1000 == 0:
                # Complex mathematical operations
                for _ in range(500):
                    _ = math.sin(round_num) * math.cos(round_num)
                    _ = math.pow(round_num % 100, 2)
                    _ = math.factorial(min(round_num % 10, 10))
                
                # HMAC operations for extra CPU load
                key = f"key_{round_num}".encode()
                hmac_result = hmac.new(key, hash_result, hashlib.sha256).digest()
                hash_result = hmac_result
        
        return hash_result.hex()

    def generate_hash_chain(self, base_data, chain_length):
        """Generate a chain of hashes with CPU intensive operations"""
        print(f"🔥 Generating hash chain of length {chain_length}")
        
        hash_chain = []
        current_hash = base_data
        
        for i in range(chain_length):
            # CPU intensive hash computation
            new_hash = self.cpu_intensive_hash(current_hash, 1000)
            hash_chain.append(new_hash)
            current_hash = new_hash
            
            # Extra CPU burn operations
            for _ in range(2000):
                _ = math.sqrt(i + 1)
                _ = math.log(i + 1)
                _ = pow(i, 2) % 997
            
            if i % 10 == 0:
                print(f"⚡ Generated {i + 1}/{chain_length} hashes")
        
        return hash_chain

    def verify_hash_chain(self, hash_chain):
        """CPU intensive hash chain verification"""
        print("🔥 Verifying hash chain integrity...")
        
        verification_results = []
        
        for i in range(1, len(hash_chain)):
            # Verify each hash in the chain
            expected_hash = self.cpu_intensive_hash(hash_chain[i-1], 1000)
            is_valid = (expected_hash == hash_chain[i])
            
            verification_results.append({
                "index": i,
                "valid": is_valid,
                "hash": hash_chain[i][:16] + "..."  # Truncate for display
            })
            
            # Extra CPU work during verification
            for _ in range(1000):
                _ = math.sin(i) + math.cos(i)
                _ = math.factorial(min(i % 8, 8))
        
        valid_count = sum(1 for r in verification_results if r["valid"])
        return verification_results, valid_count

    def hash_operations(self, hash_rounds, fibonacci_result):
        """Perform CPU intensive hash operations"""
        print(f"🔥 Starting hash computations: {hash_rounds} rounds")
        print(f"📊 Using fibonacci_result from previous task: {fibonacci_result}")
        
        start_time = time.time()
        
        # Create base data incorporating fibonacci result (dependency usage)
        base_data = f"fibonacci_{fibonacci_result}_hash_computation"
        print(f"⚡ Base data: {base_data[:50]}...")
        
        # Phase 1: Single intensive hash computation
        print("🔥 Phase 1: Single hash computation")
        single_hash_start = time.time()
        single_hash_result = self.cpu_intensive_hash(base_data, hash_rounds)
        single_hash_time = time.time() - single_hash_start
        
        # Phase 2: Hash chain generation
        print("🔥 Phase 2: Hash chain generation")
        chain_start = time.time()
        chain_length = min(50, max(10, int(abs(fibonacci_result) % 100)))
        hash_chain = self.generate_hash_chain(base_data, chain_length)
        chain_time = time.time() - chain_start
        
        # Phase 3: Hash chain verification
        print("🔥 Phase 3: Hash chain verification")
        verify_start = time.time()
        verification_results, valid_count = self.verify_hash_chain(hash_chain)
        verify_time = time.time() - verify_start
        
        # Phase 4: Complex hash combinations
        print("🔥 Phase 4: Complex hash combinations")
        combo_start = time.time()
        
        hash_combinations = []
        for i in range(min(20, len(hash_chain))):
            # Combine multiple hashes with CPU intensive operations
            combo_data = f"{hash_chain[i]}{single_hash_result}{i}"
            combo_hash = self.cpu_intensive_hash(combo_data, 500)
            hash_combinations.append(combo_hash)
            
            # Extra CPU burn for each combination
            for _ in range(1500):
                _ = math.pow(i + 1, 3) % 1009
                _ = math.sin(i) * math.cos(i)
        
        combo_time = time.time() - combo_start
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Final hash aggregation with CPU intensive operations
        final_hash_data = "".join(hash_combinations[:5])  # Use first 5 combinations
        final_hash = self.cpu_intensive_hash(final_hash_data, 2000)
        
        # Calculate hash statistics with CPU burn
        avg_hash_length = sum(len(h) for h in hash_chain) / len(hash_chain) if hash_chain else 0
        unique_hashes = len(set(hash_chain))
        
        # Extra statistical calculations
        hash_entropy = 0
        for hash_val in hash_chain[:10]:  # Calculate entropy for first 10 hashes
            for char in hash_val:
                # Simple entropy calculation with CPU burn
                char_freq = hash_val.count(char) / len(hash_val)
                if char_freq > 0:
                    hash_entropy -= char_freq * math.log2(char_freq)
            
            # Extra CPU work
            for _ in range(100):
                _ = math.sqrt(len(hash_val))
        
        result = {
            "operation": "hash_computation",
            "hash_rounds": hash_rounds,
            "chain_length": chain_length,
            "single_hash": single_hash_result[:32] + "...",  # Truncate for display
            "final_hash": final_hash,
            "chain_valid_count": valid_count,
            "chain_total_count": len(hash_chain),
            "chain_validity_rate": valid_count / len(hash_chain) if hash_chain else 0,
            "unique_hashes": unique_hashes,
            "avg_hash_length": avg_hash_length,
            "hash_entropy": hash_entropy,
            "execution_time": total_duration,
            "phase_times": {
                "single_hash": single_hash_time,
                "chain_generation": chain_time,
                "chain_verification": verify_time,
                "hash_combinations": combo_time
            },
            "cpu_intensity": "MAXIMUM",
            "fibonacci_dependency": fibonacci_result,
            "hashes_per_second": (hash_rounds + chain_length * 1000 + valid_count * 1000) / total_duration if total_duration > 0 else 0,
            "status": "success"
        }
        
        print(f"✅ Hash operations completed: {hash_rounds + chain_length * 1000} ops in {total_duration:.2f}s")
        print(f"🔥 CPU Usage: MAXIMUM - {result['hashes_per_second']:.1f} hashes/sec")
        
        return result

    def run(self, context=None):
        """Main execution method called by the engine"""
        try:
            # Get parameters from context
            hash_rounds = context.get("hash_rounds", 1000000) if context else 1000000
            fibonacci_result = context.get("fibonacci_result", 123456789.0) if context else 123456789.0
            
            print(f"🚀 CPU Hash Computer Starting")
            print(f"📊 Parameters: rounds={hash_rounds}, fibonacci_result={fibonacci_result}")
            
            # Execute CPU intensive hash operations
            result = self.hash_operations(hash_rounds, fibonacci_result)
            
            # Return result as JSON string
            return json.dumps(result)
            
        except Exception as e:
            error_result = {
                "operation": "hash_computation",
                "status": "failed",
                "error_message": str(e),
                "cpu_intensity": "MAXIMUM"
            }
            return json.dumps(error_result)

def module():
    """Engine required module function"""
    return CPUHashComputer() 