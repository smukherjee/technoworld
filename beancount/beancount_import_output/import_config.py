
import os
from beancount_import.webserver import main

# Configuration for beancount-import web interface
CONFIG = {
    'data_sources': [],  # Empty for now - transactions already processed
    'journal': '/Users/sujoymukherjee/code/technoworld/beancount/beancount_import_output/base_journal.beancount',
    'output_dir': '/Users/sujoymukherjee/code/technoworld/beancount/beancount_import_output',
    'port': 8080,
    'host': 'localhost',
}

if __name__ == '__main__':
    main(CONFIG)
