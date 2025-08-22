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

    # The webserver main function expects command line arguments.
    # We will construct them from our config.
    sys.argv = [
        sys.argv[0], # script name
        '--journal_input', CONFIG['journal'],
        '--default_output', os.path.join(root_dir, 'pending_transactions.beancount'),
        '--ignored_journal', os.path.join(root_dir, 'ignored_transactions.beancount'),
        '--port', str(CONFIG.get('port', 8080)),
        '--host', CONFIG.get('host', 'localhost'),
    ]
    
    # Add data sources as a JSON string
    data_sources_json = json.dumps(CONFIG.get('data_sources', []))
    sys.argv.extend(['--data_sources', data_sources_json])

    print(f"\nOpen http://{CONFIG.get('host', 'localhost')}:{CONFIG.get('port', 8080)} in your browser")
    
    # Run the web server, which will parse sys.argv
    main()
