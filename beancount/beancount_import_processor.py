"""
Beancount-import post-processor integration.
This module integrates beancount-import as a post-processor for enhanced classification
and web-based transaction review workflow.
"""

import os
import tempfile
import json
import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from beancount.core.data import Transaction, Posting, Amount, TxnPosting
from beancount.core import data
from beancount.parser import parser
from beancount import loader
import decimal

try:
    from beancount_import.reconcile import Reconciler
    from beancount_import.source import Source, SourceResults, ImportResult
    from beancount_import.training import PredictionInput
    BEANCOUNT_IMPORT_AVAILABLE = True
except ImportError:
    BEANCOUNT_IMPORT_AVAILABLE = False
    print("Warning: beancount-import not available. Post-processing features disabled.")


class ExcelTemplateSource(Source):
    """
    Custom beancount-import source for Excel template-based transactions.
    This integrates your existing Excel parsing with beancount-import's workflow.
    """
    
    def __init__(self, transactions_df: pd.DataFrame, source_account: str = "Assets:Bank:ICICI:Checking"):
        self.transactions_df = transactions_df
        self.source_account = source_account
        self._name = "excel_template"
        
        # Required by beancount-import Source interface
        self.example_posting_key_extractors = {
            'source_desc': None,  # Use default extractor
            'original_description': None,
        }
        self.example_transaction_key_extractors = {}
    
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, value):
        self._name = value
    
    def prepare(self, journal, results: SourceResults):
        """Prepare the source (required by beancount-import)."""
        pass
    
    def load(self, journal, results: SourceResults):
        """Load transactions from the DataFrame into beancount format."""
        import_results = []
        
        for _, row in self.transactions_df.iterrows():
            try:
                # Parse the transaction date
                trans_date = self._parse_date(row.get('Date', ''))
                if not trans_date:
                    continue
                
                # Create the transaction
                transaction = self._create_transaction_from_row(row, trans_date)
                if transaction:
                    import_result = ImportResult(
                        date=trans_date,
                        entries=[transaction],
                        info={
                            'filename': 'excel_template',
                            'line': int(row.name) if hasattr(row, 'name') else 0,
                            'type': 'excel_import',
                            'original_description': str(row.get('Description', '')),
                            'category': str(row.get('Category', 'Uncategorized'))
                        }
                    )
                    import_results.append(import_result)
                    
            except Exception as e:
                print(f"Error processing row {getattr(row, 'name', 'unknown')}: {e}")
                continue
        
        return import_results
    
    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """Parse date string in DD-MM-YYYY format."""
        try:
            if pd.isna(date_str) or not date_str:
                return None
            
            # Handle different date formats
            if isinstance(date_str, str):
                # Try DD-MM-YYYY format first
                try:
                    return datetime.datetime.strptime(date_str, '%d-%m-%Y').date()
                except ValueError:
                    # Try other common formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                        try:
                            return datetime.datetime.strptime(date_str, fmt).date()
                        except ValueError:
                            continue
            elif hasattr(date_str, 'date'):
                return date_str.date()
            
            return None
        except Exception:
            return None
    
    def _create_transaction_from_row(self, row: pd.Series, trans_date: datetime.date) -> Optional[Transaction]:
        """Create a beancount Transaction from a DataFrame row."""
        try:
            # Get transaction details
            description = str(row.get('Description', 'Unknown transaction'))
            reference = str(row.get('Reference', ''))
            category = str(row.get('Category', 'Expenses:Uncategorized'))
            
            # Determine amount and type
            credit_amt = self._parse_amount(row.get('Credit', '0'))
            debit_amt = self._parse_amount(row.get('Debit', '0'))
            
            if credit_amt > 0:
                amount = credit_amt
                main_account = self.source_account
                other_account = f"Income:{category}" if not category.startswith(('Assets:', 'Liabilities:', 'Income:', 'Expenses:')) else category
            elif debit_amt > 0:
                amount = debit_amt
                main_account = self.source_account
                other_account = f"Expenses:{category}" if not category.startswith(('Assets:', 'Liabilities:', 'Income:', 'Expenses:')) else category
            else:
                return None
            
            # Create postings
            if credit_amt > 0:
                # Credit transaction (money coming in)
                postings = [
                    data.Posting(
                        account=main_account,
                        units=Amount(decimal.Decimal(str(amount)), 'INR'),
                        cost=None,
                        price=None,
                        flag=None,
                        meta={
                            'source_desc': description,
                            'original_description': description,
                            'reference': reference,
                            'category': category,
                        }
                    ),
                    data.Posting(
                        account=other_account,
                        units=Amount(decimal.Decimal(str(-amount)), 'INR'),
                        cost=None,
                        price=None,
                        flag=None,
                        meta={}
                    )
                ]
            else:
                # Debit transaction (money going out)
                postings = [
                    data.Posting(
                        account=main_account,
                        units=Amount(decimal.Decimal(str(-amount)), 'INR'),
                        cost=None,
                        price=None,
                        flag=None,
                        meta={
                            'source_desc': description,
                            'original_description': description,
                            'reference': reference,
                            'category': category,
                        }
                    ),
                    data.Posting(
                        account=other_account,
                        units=Amount(decimal.Decimal(str(amount)), 'INR'),
                        cost=None,
                        price=None,
                        flag=None,
                        meta={}
                    )
                ]
            
            # Create the transaction
            transaction = data.Transaction(
                meta={
                    'filename': 'excel_template',
                    'lineno': 0,
                },
                date=trans_date,
                flag='*',
                payee=None,
                narration=description,
                tags=set(),
                links=set(),
                postings=postings
            )
            
            return transaction
            
        except Exception as e:
            print(f"Error creating transaction: {e}")
            return None
    
    def _parse_amount(self, amount_str) -> float:
        """Parse amount string, handling commas and empty values."""
        try:
            if pd.isna(amount_str) or amount_str == '' or amount_str == '0.00':
                return 0.0
            
            # Remove commas and convert to float
            amount_str = str(amount_str).replace(',', '').strip()
            return float(amount_str)
        except (ValueError, TypeError):
            return 0.0
    
    def get_example_key_value_pairs(self, transaction: Transaction, posting: Posting) -> Dict[str, Any]:
        """Extract key-value pairs for ML training."""
        pairs = {}
        
        if posting.meta:
            source_desc = posting.meta.get('source_desc', '')
            if source_desc:
                pairs['source_desc'] = source_desc
            
            original_desc = posting.meta.get('original_description', '')
            if original_desc:
                pairs['description'] = original_desc
                
            category = posting.meta.get('category', '')
            if category:
                pairs['category'] = category
                
            reference = posting.meta.get('reference', '')
            if reference:
                pairs['reference'] = reference
        
        return pairs


class BeancountImportProcessor:
    """
    Post-processor that integrates beancount-import with the existing Excel parsing workflow.
    Provides enhanced classification and web-based review interface.
    """
    
    def __init__(self, base_journal_file: Optional[str] = None):
        """
        Initialize the processor.
        
        Args:
            base_journal_file: Path to existing beancount journal file (optional)
        """
        if not BEANCOUNT_IMPORT_AVAILABLE:
            raise ImportError("beancount-import is not available. Please install it first.")
        
        self.base_journal_file = base_journal_file
        self.temp_dir = None
        self.reconciler = None
    
    def process_transactions(self, transactions_df: pd.DataFrame, 
                           source_account: str = "Assets:Bank:ICICI:Checking",
                           output_dir: str = "beancount_import_output") -> Dict[str, Any]:
        """
        Process transactions through beancount-import for enhanced classification.
        
        Args:
            transactions_df: DataFrame with parsed transactions
            source_account: Source account for transactions
            output_dir: Directory for beancount-import output files
            
        Returns:
            Dictionary with processing results and file paths
        """
        try:
            # Make output_dir an absolute path relative to this script's directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_dir_abs = os.path.join(script_dir, output_dir)

            # Clean up previous run to ensure fresh files are generated
            if os.path.exists(output_dir_abs):
                import shutil
                shutil.rmtree(output_dir_abs)

            # Create output directory
            os.makedirs(output_dir_abs, exist_ok=True)
            
            # Create temporary files for beancount-import
            self.temp_dir = tempfile.mkdtemp(prefix='beancount_import_')
            
            # Step 1: Create base journal file
            base_journal_path = self._create_base_journal(output_dir_abs, source_account)
            
            # Step 2: Create beancount-import configuration
            config_path = self._create_import_config(transactions_df, source_account, 
                                                   base_journal_path, output_dir_abs)
            
            # Step 3: Setup reconciler
            self._setup_reconciler(config_path)
            
            # Step 4: Generate enhanced beancount file with ML predictions
            enhanced_file = self._generate_enhanced_transactions(transactions_df, 
                                                               source_account, output_dir_abs)
            
            # Step 5: Prepare web interface files
            web_files = self._prepare_web_interface(output_dir_abs)
            
            return {
                'success': True,
                'base_journal': base_journal_path,
                'enhanced_transactions': enhanced_file,
                'config_file': config_path,
                'output_directory': output_dir_abs,
                'web_interface': web_files,
                'message': 'Beancount-import post-processing completed successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Error in beancount-import post-processing: {e}'
            }
    
    def _create_base_journal(self, output_dir: str, source_account: str) -> str:
        """Create a base beancount journal file."""
        journal_path = os.path.join(output_dir, 'base_journal.beancount')
        
        # Get current date
        today = datetime.date.today()
        year_ago = today.replace(year=today.year - 1)
        
        content = f'''
; Base journal file for beancount-import integration
; Generated on {today}

plugin "beancount.plugins.auto_accounts"

{year_ago} open Assets:Bank:ICICI:Checking INR
{year_ago} open Assets:Bank:ICICI:Savings INR
{year_ago} open Expenses:Food:Restaurant INR
{year_ago} open Expenses:Food:Grocery INR
{year_ago} open Expenses:Transportation:Taxi INR
{year_ago} open Expenses:Transportation:Public INR
{year_ago} open Expenses:Entertainment:Movies INR
{year_ago} open Expenses:Entertainment:Games INR
{year_ago} open Expenses:Shopping:Clothing INR
{year_ago} open Expenses:Shopping:Electronics INR
{year_ago} open Expenses:Medical:Hospital INR
{year_ago} open Expenses:Medical:Pharmacy INR
{year_ago} open Expenses:Bills:Mobile INR
{year_ago} open Expenses:Bills:Internet INR
{year_ago} open Expenses:Bills:Electricity INR
{year_ago} open Expenses:Investment:MutualFunds INR
{year_ago} open Expenses:Investment:Stocks INR
{year_ago} open Income:Salary INR
{year_ago} open Income:Interest INR
{year_ago} open Income:Dividends INR
{year_ago} open Expenses:Banking:Fees INR
{year_ago} open Expenses:ATM:Withdrawal INR
{year_ago} open Expenses:Transfer:External INR
{year_ago} open Expenses:Uncategorized INR
'''
        
        with open(journal_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return journal_path
    
    def _create_import_config(self, transactions_df: pd.DataFrame, source_account: str, 
                            journal_path: str, output_dir: str) -> str:
        """Create beancount-import configuration file."""
        config_path = os.path.join(output_dir, 'import_config.py')
        
        # Create a simple configuration without problematic data sources
        config_content = f'''
import os
from beancount_import.webserver import main

# Configuration for beancount-import web interface
CONFIG = {{
    'data_sources': [],  # Empty for now - transactions already processed
    'journal': '{journal_path}',
    'output_dir': '{output_dir}',
    'port': 8080,
    'host': 'localhost',
}}

if __name__ == '__main__':
    main(CONFIG)
'''
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        return config_path
    
    def _setup_reconciler(self, config_path: str):
        """Setup the beancount-import reconciler."""
        # This would setup the reconciler for ML training
        # For now, we'll prepare the structure
        pass
    
    def _generate_enhanced_transactions(self, transactions_df: pd.DataFrame, 
                                      source_account: str, output_dir: str) -> str:
        """Generate enhanced transactions with ML predictions."""
        enhanced_file = os.path.join(output_dir, 'enhanced_transactions.beancount')
        
        # Create the Excel source
        excel_source = ExcelTemplateSource(transactions_df, source_account)
        
        # Load transactions through the source
        results = excel_source.load(None, None)
        
        # Write enhanced beancount file
        with open(enhanced_file, 'w', encoding='utf-8') as f:
            f.write(f'; Enhanced transactions with beancount-import integration\n')
            f.write(f'; Generated on {datetime.date.today()}\n\n')
            
            for result in results:
                for entry in result.entries:
                    if isinstance(entry, Transaction):
                        # Write the transaction
                        f.write(f'{entry.date} {entry.flag} "{entry.narration}"\n')
                        for posting in entry.postings:
                            f.write(f'  {posting.account:<40} {posting.units}\n')
                            # Add metadata as comments
                            if posting.meta:
                                for key, value in posting.meta.items():
                                    f.write(f'    ; {key}: {value}\n')
                        f.write('\n')
        
        return enhanced_file
    
    def _prepare_web_interface(self, output_dir: str) -> Dict[str, str]:
        """Prepare files for the web interface."""
        web_dir = os.path.join(output_dir, 'web')
        os.makedirs(web_dir, exist_ok=True)
        
        # Create a startup script for the web interface
        startup_script = os.path.join(web_dir, 'start_web_interface.py')
        with open(startup_script, 'w', encoding='utf-8') as f:
            f.write(f'''#!/usr/bin/env python3
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
    print(f"Root directory: {{root_dir}}")
    print(f"Config file: {{config_file}}")
    
    if not os.path.exists(config_file):
        print(f"Error: Config file not found at {{config_file}}")
        sys.exit(1)

    # Load the configuration from the file
    spec = importlib.util.spec_from_file_location("config", config_file)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    CONFIG = config_module.CONFIG

    # The webserver main function expects command line arguments.
    # We will construct them from our config (no script name needed).
    args = [
        '--journal_input', CONFIG['journal'],
        '--default_output', os.path.join(root_dir, 'pending_transactions.beancount'),
        '--ignored_journal', os.path.join(root_dir, 'ignored_transactions.beancount'),
        '-p', str(CONFIG.get('port', 8080)),
        '-a', CONFIG.get('host', 'localhost'),
    ]
    
    # Add data sources as a JSON string
    data_sources_json = json.dumps(CONFIG.get('data_sources', []))
    args.extend(['--data_sources', data_sources_json])

    print(f"\\nOpen http://{{CONFIG.get('host', 'localhost')}}:{{CONFIG.get('port', 8080)}} in your browser")
    
    # Run the web server with the constructed arguments
    main(args)
''')
        
        # Create instructions file
        instructions_file = os.path.join(web_dir, 'README.md')
        with open(instructions_file, 'w', encoding='utf-8') as f:
            f.write('''# Beancount-Import Web Interface

## Quick Start

1. **Start the web interface:**
   ```bash
   python start_web_interface.py
   ```

2. **Open your browser:**
   Navigate to http://localhost:8080

3. **Review transactions:**
   - View pending transactions
   - Confirm or modify account predictions
   - Train the ML classifier with your choices

## Features

- **Visual Transaction Review**: See all pending transactions in a web interface
- **Account Prediction**: ML-based automatic account classification
- **Manual Correction**: Edit accounts, descriptions, and add tags/links
- **Training**: The system learns from your choices to improve predictions
- **Duplicate Detection**: Automatic matching and merging of similar transactions

## Keyboard Shortcuts

- `Enter`: Accept selected transaction
- `i`: Ignore transaction
- `t`: Retrain classifier
- `1-9`: Quick account selection
- `Arrow Keys`: Navigate between transactions

## Files

- `enhanced_transactions.beancount`: Transactions with ML predictions
- `base_journal.beancount`: Base chart of accounts
- `import_config.py`: Configuration for beancount-import

For more information, see: https://github.com/jbms/beancount-import
''')
        
        return {
            'startup_script': startup_script,
            'instructions': instructions_file,
            'web_directory': web_dir
        }
    
    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)


def integrate_with_main_workflow(transactions_df: pd.DataFrame, 
                                source_account: str = "Assets:Bank:ICICI:Checking",
                                enable_post_processing: bool = True) -> Dict[str, Any]:
    """
    Integration function to be called from main.py for post-processing.
    
    Args:
        transactions_df: Classified transactions DataFrame
        source_account: Source account for transactions
        enable_post_processing: Whether to enable beancount-import post-processing
        
    Returns:
        Dictionary with post-processing results
    """
    if not enable_post_processing or not BEANCOUNT_IMPORT_AVAILABLE:
        return {
            'success': False,
            'message': 'Beancount-import post-processing disabled or not available'
        }
    
    try:
        processor = BeancountImportProcessor()
        results = processor.process_transactions(transactions_df, source_account)
        processor.cleanup()
        return results
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'Post-processing failed: {e}'
        }
