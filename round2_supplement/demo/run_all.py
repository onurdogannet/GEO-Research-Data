#!/usr/bin/env python3
"""Regenerate only the new, disclosed fictional demonstration."""
import build_inputs
import run_demo

if __name__ == '__main__':
    build_inputs.main()
    run_demo.main()
