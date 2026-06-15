#!/usr/bin/env python3
"""
AIRL Training Data Generator — entrypoint
Run as: python generate.py [options]
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from airl_generator.generator import main

if __name__ == "__main__":
    main()
