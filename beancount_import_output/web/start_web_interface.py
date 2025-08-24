#!/usr/bin/env python3
"""
Startup script for beancount-import web interface.
Run this script to launch the web-based transaction review interface.
"""

import sys
import os
import json
import importlib.util
from beancount_import.webserver import main

if __name__ == '__main__':
    # The script is in 'beancount_import_output/web', so the root is one level up.
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    config_file = os.path.join(root_dir, 'import_config.py')

    print(f"Starting beancount-import web interface...")
    print(f"Root directory: {root_dir}")
    print(f"Config file: {config_file}")
    
    if not os.path.exists(config_file):
        print(f"Error: Config file not found at {config_file}")
        sys.exit(1)

    # Load the configuration from the file
    spec = importlib.util.spec_from_file_location("config", config_file)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    CONFIG = config_module.CONFIG

    # Prepare keyword arguments and call main() programmatically to avoid
    # command-line parsing edge cases when running from this helper script.
    kwargs = {
        'journal_input': CONFIG['journal'],
        'ignored_journal': os.path.join(root_dir, 'ignored_transactions.beancount'),
        'default_output': os.path.join(root_dir, 'pending_transactions.beancount'),
        'transaction_output_map': os.path.join(root_dir, 'transaction_output_map.json'),
        'port': int(CONFIG.get('port', 8080)),
        'address': CONFIG.get('host', '127.0.0.1'),
        'data_sources': CONFIG.get('data_sources', []),
    }

    print(f"\nOpen http://{kwargs['address']}:{kwargs['port']} in your browser")
    # Run the web server programmatically; the `main` function will call
    # parse_arguments with the provided kwargs as defaults.
    main([], **kwargs)
