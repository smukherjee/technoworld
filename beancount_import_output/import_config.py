
import os
from beancount_import.webserver import main

# Configuration for beancount-import web interface
CONFIG = {
    'data_sources': [
        {
            'module': 'beancount_import.source.description_based_source',
            'class': 'Source',
            'config': {
                'account': 'Assets:Bank:ICICI:Checking',
                'currency': 'INR',
            }
        }
    ],
    'journal': 'beancount_import_output/base_journal.beancount',
    'output_dir': 'beancount_import_output',
    'port': 8080,
    'host': 'localhost',
}

if __name__ == '__main__':
    main(CONFIG)
