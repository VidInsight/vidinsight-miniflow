#!/usr/bin/env python3
"""
Miniflow module entry point

Bu dosya 'python -m miniflow' komutu ile modülün çalıştırılmasını sağlar.
"""

if __name__ == '__main__':
    # Import here to avoid circular imports
    from .main import main
    main() 