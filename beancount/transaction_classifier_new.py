"""
Transaction Classifier using Beancount Smart Importer
Classifies bank transactions into categories using machine learning.
"""

import pandas as pd
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

# Beancount and smart_importer imports
try:
    from smart_importer import PredictPostings, apply_hooks
    from beancount.core.data import Transaction, Posting, Amount, Directive
    from beancount.core.amount import Amount as BeanAmount
    from beancount.core import data
    from beancount.parser import parser
    from decimal import Decimal
    import beancount.core.data as bc_data
    SMART_IMPORTER_AVAILABLE = True
except ImportError as e:
    print(f"Smart importer not available: {e}")
    SMART_IMPORTER_AVAILABLE = False


class TransactionClassifier:
    """Classifier for bank transactions using beancount smart_importer."""
    
    def __init__(self):
        self.setup_logging()
        self.account_mapping = self._setup_account_mapping()
        self.category_rules = self._setup_category_rules()
        
    def setup_logging(self):
        """Set up logging for the classifier."""
        self.logger = logging.getLogger(self.__class__.__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _setup_account_mapping(self) -> Dict[str, str]:
        """Set up account mapping for different transaction types."""
        return {
            # Income categories
            'salary': 'Income:Salary',
            'bonus': 'Income:Bonus',
            'interest': 'Income:Interest',
            'dividend': 'Income:Dividend',
            'refund': 'Income:Refund',
            
            # Expense categories
            'food': 'Expenses:Food:Restaurant',
            'groceries': 'Expenses:Food:Groceries',
            'transport': 'Expenses:Transport',
            'fuel': 'Expenses:Transport:Fuel',
            'utilities': 'Expenses:Utilities',
            'shopping': 'Expenses:Shopping',
            'entertainment': 'Expenses:Entertainment',
            'medical': 'Expenses:Medical',
            'education': 'Expenses:Education',
            'insurance': 'Expenses:Insurance',
            'rent': 'Expenses:Housing:Rent',
            'maintenance': 'Expenses:Housing:Maintenance',
            'phone': 'Expenses:Utilities:Phone',
            'internet': 'Expenses:Utilities:Internet',
            'electricity': 'Expenses:Utilities:Electricity',
            
            # Investment categories
            'investment': 'Assets:Investment',
            'mutual_fund': 'Assets:Investment:MutualFund',
            'stocks': 'Assets:Investment:Stocks',
            'fixed_deposit': 'Assets:Investment:FixedDeposit',
            
            # Transfer categories
            'transfer': 'Assets:Transfer',
            'atm': 'Expenses:Bank:ATM',
            'bank_charges': 'Expenses:Bank:Charges',
            
            # Default
            'unknown': 'Expenses:Unknown'
        }
    
    def _setup_category_rules(self) -> List[Dict[str, Any]]:
        """Set up rules for categorizing transactions based on description patterns."""
        return [
            # Food & Dining
            {'patterns': ['restaurant', 'hotel', 'cafe', 'food', 'zomato', 'swiggy', 'dominos', 'pizza', 'mcdonald'], 'category': 'food'},
            {'patterns': ['grocery', 'supermarket', 'mart', 'store', 'big bazaar', 'reliance', 'dmart'], 'category': 'groceries'},
            
            # Transport
            {'patterns': ['uber', 'ola', 'taxi', 'transport', 'bus', 'metro', 'railway', 'petrol', 'diesel', 'fuel'], 'category': 'transport'},
            {'patterns': ['petrol pump', 'fuel', 'gas station', 'hp petrol', 'bharat petroleum'], 'category': 'fuel'},
            
            # Utilities
            {'patterns': ['electricity', 'power', 'mseb', 'bescom', 'kseb'], 'category': 'electricity'},
            {'patterns': ['mobile', 'phone', 'airtel', 'vodafone', 'jio', 'bsnl'], 'category': 'phone'},
            {'patterns': ['internet', 'broadband', 'wifi', 'fiber'], 'category': 'internet'},
            {'patterns': ['water', 'gas cylinder', 'utility'], 'category': 'utilities'},
            
            # Shopping
            {'patterns': ['amazon', 'flipkart', 'myntra', 'shopping', 'mall', 'brand factory'], 'category': 'shopping'},
            
            # Entertainment
            {'patterns': ['movie', 'cinema', 'netflix', 'spotify', 'entertainment', 'game', 'book'], 'category': 'entertainment'},
            
            # Medical
            {'patterns': ['hospital', 'medical', 'pharmacy', 'doctor', 'clinic', 'medicine', 'apollo'], 'category': 'medical'},
            
            # Banking
            {'patterns': ['atm', 'withdrawal', 'cash'], 'category': 'atm'},
            {'patterns': ['bank charges', 'service charge', 'annual fee', 'maintenance'], 'category': 'bank_charges'},
            
            # Income
            {'patterns': ['salary', 'pay', 'income', 'wages'], 'category': 'salary'},
            {'patterns': ['interest', 'fd interest', 'saving interest'], 'category': 'interest'},
            {'patterns': ['dividend', 'mutual fund'], 'category': 'dividend'},
            {'patterns': ['refund', 'cashback', 'return'], 'category': 'refund'},
            
            # Investment
            {'patterns': ['mutual fund', 'sip', 'investment', 'mf'], 'category': 'mutual_fund'},
            {'patterns': ['stock', 'equity', 'share', 'zerodha', 'groww'], 'category': 'stocks'},
            {'patterns': ['fixed deposit', 'fd', 'recurring deposit', 'rd'], 'category': 'fixed_deposit'},
            
            # Housing
            {'patterns': ['rent', 'house rent', 'flat rent'], 'category': 'rent'},
            {'patterns': ['maintenance', 'society', 'housing'], 'category': 'maintenance'},
        ]
    
    def classify_transactions(self, transactions_df: pd.DataFrame) -> pd.DataFrame:
        """Add classification column to transactions DataFrame."""
        self.logger.info(f"Classifying {len(transactions_df)} transactions")
        
        # Create a copy to avoid modifying the original
        df = transactions_df.copy()
        
        # Add classification column
        df['Category'] = df.apply(self._classify_single_transaction, axis=1)
        
        # Add account mapping
        df['Account'] = df['Category'].map(self.account_mapping).fillna(self.account_mapping['unknown'])
        
        # Log classification summary
        self._log_classification_summary(df)
        
        return df
    
    def _classify_single_transaction(self, row: pd.Series) -> str:
        """Classify a single transaction based on its description and amount."""
        description = str(row.get('Description', '')).lower()
        credit = str(row.get('Credit', ''))
        debit = str(row.get('Debit', ''))
        
        # Determine if it's income (credit) or expense (debit)
        is_income = bool(credit and credit != '0.00')
        is_expense = bool(debit and debit != '0.00')
        
        # Apply rule-based classification
        for rule in self.category_rules:
            if any(pattern in description for pattern in rule['patterns']):
                category = rule['category']
                
                # Adjust category based on transaction type
                if is_income and category in ['food', 'groceries', 'transport', 'shopping', 'entertainment']:
                    # If it's income but matches expense patterns, it might be a refund
                    if any(refund_word in description for refund_word in ['refund', 'return', 'cashback']):
                        return 'refund'
                
                return category
        
        # Default classification based on transaction type
        if is_income:
            return 'salary'  # Default income category
        elif is_expense:
            return 'unknown'  # Default expense category
        else:
            return 'unknown'
    
    def _log_classification_summary(self, df: pd.DataFrame):
        """Log a summary of the classification results."""
        category_counts = df['Category'].value_counts()
        self.logger.info("Classification Summary:")
        for category, count in category_counts.items():
            percentage = (count / len(df)) * 100
            self.logger.info(f"  {category}: {count} transactions ({percentage:.1f}%)")
    
    def generate_beancount_entries(self, transactions_df: pd.DataFrame, account_name: str = "Assets:Bank:Checking") -> List[str]:
        """Generate beancount entries from classified transactions."""
        entries = []
        
        for _, row in transactions_df.iterrows():
            date_str = row['Date']
            description = row['Description']
            credit = row.get('Credit', '')
            debit = row.get('Debit', '')
            account = row['Account']
            
            # Parse date
            try:
                date_obj = datetime.strptime(date_str, '%d-%m-%Y')
                beancount_date = date_obj.strftime('%Y-%m-%d')
            except:
                continue
            
            # Determine amount and direction
            if credit and credit != '0.00':
                amount = credit
                # For credits (income), bank account increases, income account decreases
                entry = f'{beancount_date} * "{description}"\n'
                entry += f'  {account_name}  {amount} INR\n'
                entry += f'  {account}  -{amount} INR\n'
            elif debit and debit != '0.00':
                amount = debit
                # For debits (expenses), bank account decreases, expense account increases
                entry = f'{beancount_date} * "{description}"\n'
                entry += f'  {account}  {amount} INR\n'
                entry += f'  {account_name}  -{amount} INR\n'
            else:
                continue
            
            entries.append(entry)
        
        return entries
    
    def save_beancount_file(self, transactions_df: pd.DataFrame, output_file: str, account_name: str = "Assets:Bank:Checking"):
        """Save transactions as a beancount file."""
        entries = self.generate_beancount_entries(transactions_df, account_name)
        
        with open(output_file, 'w') as f:
            # Write header
            f.write(f"; Beancount file generated from transactions\n")
            f.write(f"; Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Write account opening
            f.write(f"1900-01-01 open {account_name} INR\n")
            for account in set(transactions_df['Account']):
                f.write(f"1900-01-01 open {account} INR\n")
            f.write("\n")
            
            # Write transactions
            for entry in entries:
                f.write(entry)
                f.write("\n")
        
        self.logger.info(f"Saved {len(entries)} beancount entries to {output_file}")
    
    def smart_classify_with_ml(self, transactions_df: pd.DataFrame) -> pd.DataFrame:
        """Use smart_importer ML classification if available."""
        if not SMART_IMPORTER_AVAILABLE:
            self.logger.warning("Smart importer not available, using rule-based classification")
            return self.classify_transactions(transactions_df)
        
        self.logger.info("Using smart_importer ML classification")
        
        # Convert transactions to beancount format for ML processing
        # This is a simplified implementation
        # In practice, you'd need training data and a trained model
        
        # For now, fall back to rule-based classification
        # TODO: Implement proper ML classification with training data
        return self.classify_transactions(transactions_df)
