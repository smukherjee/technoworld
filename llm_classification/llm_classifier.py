"""
LLM-based Transaction Classifier
Classifies bank transactions using LLM and extracts payee information from UPI transactions
"""

import pandas as pd
import re
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import os

class LLMTransactionClassifier:
    def __init__(self):
        self.categories = {
            'food': ['restaurant', 'cafe', 'food', 'pizza', 'burger', 'swiggy', 'zomato', 'dominos', 'mcdonald'],
            'groceries': ['grocery', 'supermarket', 'mart', 'store', 'bigbazar', 'reliance', 'dmart'],
            'transport': ['uber', 'ola', 'taxi', 'metro', 'bus', 'fuel', 'petrol', 'diesel', 'transport'],
            'entertainment': ['movie', 'cinema', 'netflix', 'amazon prime', 'spotify', 'game', 'entertainment'],
            'shopping': ['amazon', 'flipkart', 'myntra', 'shopping', 'mall', 'store', 'purchase'],
            'medical': ['hospital', 'pharmacy', 'doctor', 'medical', 'health', 'clinic', 'medicine'],
            'bills': ['electricity', 'mobile', 'internet', 'phone', 'recharge', 'bill', 'utilities'],
            'atm': ['atm', 'withdrawal', 'cash'],
            'investment': ['mutual fund', 'sip', 'investment', 'stock', 'fd', 'fixed deposit'],
            'salary': ['salary', 'sal', 'pay', 'wages', 'income'],
            'transfer': ['transfer', 'neft', 'rtgs', 'imps'],
            'unknown': []
        }
        
    def extract_upi_info(self, description: str) -> Dict[str, str]:
        """
        Extract information from UPI transaction descriptions
        Common formats found:
        - Id/swiggyupi@axisb/Axis Bank
        - Swi/upiswiggy@icici/ICICI
        - BharatPe/bharatpe.900678/Federal
        - PIN/cmrlsteteynampe/Yes Bank
        """
        upi_info = {
            'payee': '',
            'transaction_type': '',
            'sender_bank': '',
            'reference_number': '',
            'transaction_id': '',
            'is_upi': False
        }
        
        # Check for UPI patterns
        upi_patterns = [
            r'Id/([^@/]+)@([^/]+)/(.+)',  # Id/swiggyupi@axisb/Axis Bank
            r'Swi/([^@/]+)@([^/]+)/(.+)', # Swi/upiswiggy@icici/ICICI
            r'([^/]+)/([^/]+\.[0-9]+)/(.+)', # BharatPe/bharatpe.900678/Federal
            r'PIN/([^@/]+)@?([^/]*)/(.+)', # PIN/cmrlsteteynampe/Yes Bank
            r'Razorpa/([^/]+)/(.+)',      # Razorpa/airtelpaymentsb/Airtel
            r'UPI/([^/]+)/([^/]+)/([^/]+)/([^/]+)/(.+)' # Standard UPI format
        ]
        
        for pattern in upi_patterns:
            match = re.search(pattern, description)
            if match:
                upi_info['is_upi'] = True
                groups = match.groups()
                
                if len(groups) >= 1:
                    # Extract payee (first group, usually the UPI ID or merchant)
                    payee = groups[0].strip()
                    # Clean up payee name
                    payee = re.sub(r'upi|@.*$', '', payee, flags=re.IGNORECASE)
                    payee = re.sub(r'[0-9\-\.]+$', '', payee)
                    payee = payee.strip('-.')
                    upi_info['payee'] = payee.strip()
                
                if len(groups) >= 2:
                    upi_info['transaction_type'] = groups[1].strip()
                
                if len(groups) >= 3:
                    upi_info['sender_bank'] = groups[2].strip()
                
                if len(groups) >= 4:
                    upi_info['reference_number'] = groups[3].strip()
                
                if len(groups) >= 5:
                    upi_info['transaction_id'] = groups[4].strip()
                
                break
        
        # Additional check for common UPI keywords if no pattern matched
        if not upi_info['is_upi']:
            upi_keywords = ['@paytm', '@ybl', '@okhdfcbank', '@okaxis', '@okicici', 
                           '@oksbi', '@phonepe', '@gpay', '@amazonpay', 'bharatpe', 
                           'paytm', 'phonepe', 'gpay', 'razorpay']
            
            description_lower = description.lower()
            for keyword in upi_keywords:
                if keyword in description_lower:
                    upi_info['is_upi'] = True
                    # Try to extract payee from the description
                    parts = description.split('/')
                    if len(parts) >= 2:
                        upi_info['payee'] = parts[1].split('@')[0] if '@' in parts[1] else parts[1]
                        upi_info['payee'] = re.sub(r'[0-9\-\.]+', '', upi_info['payee']).strip('-.')
                    break
                    
        return upi_info
    
    def classify_transaction(self, description: str, amount: float) -> Tuple[str, str, float]:
        """
        Classify transaction based on description and amount
        Returns: (category, account, confidence_score)
        """
        description_lower = description.lower()
        
        # Extract UPI information
        upi_info = self.extract_upi_info(description)
        
        # Rule-based classification with confidence scoring
        max_confidence = 0.0
        best_category = 'unknown'
        
        for category, keywords in self.categories.items():
            confidence = 0.0
            for keyword in keywords:
                if keyword in description_lower:
                    confidence += 0.8
                    break
            
            # Additional rules based on UPI payee
            if upi_info['is_upi'] and upi_info['payee']:
                payee_lower = upi_info['payee'].lower()
                
                # Specific payee-based rules
                if any(food_term in payee_lower for food_term in ['swiggy', 'zomato', 'resto', 'cafe', 'food']):
                    if category == 'food':
                        confidence += 0.9
                elif any(shop_term in payee_lower for shop_term in ['amazon', 'flipkart', 'myntra', 'shop']):
                    if category == 'shopping':
                        confidence += 0.9
                elif any(transport_term in payee_lower for transport_term in ['uber', 'ola', 'metro', 'taxi']):
                    if category == 'transport':
                        confidence += 0.9
                elif any(bill_term in payee_lower for bill_term in ['recharge', 'mobile', 'electricity', 'bill']):
                    if category == 'bills':
                        confidence += 0.9
            
            # Amount-based rules
            if amount > 0:  # Credit transaction
                if 'salary' in description_lower and category == 'salary':
                    confidence += 0.9
                elif amount > 10000 and category == 'salary':
                    confidence += 0.5
                elif category == 'salary':
                    confidence += 0.3
            else:  # Debit transaction
                if abs(amount) < 100 and category == 'food':
                    confidence += 0.2
                elif abs(amount) > 1000 and category in ['shopping', 'investment']:
                    confidence += 0.3
                elif 'atm' in description_lower and category == 'atm':
                    confidence += 0.9
            
            if confidence > max_confidence:
                max_confidence = confidence
                best_category = category
        
        # Map category to account
        account_mapping = {
            'food': 'Expenses:Food:Restaurant',
            'groceries': 'Expenses:Food:Grocery',
            'transport': 'Expenses:Transportation',
            'entertainment': 'Expenses:Entertainment',
            'shopping': 'Expenses:Shopping',
            'medical': 'Expenses:Medical',
            'bills': 'Expenses:Bills',
            'atm': 'Expenses:ATM:Withdrawal',
            'investment': 'Expenses:Investment',
            'salary': 'Income:Salary',
            'transfer': 'Expenses:Transfer',
            'unknown': 'Expenses:Uncategorized'
        }
        
        return best_category, account_mapping.get(best_category, 'Expenses:Uncategorized'), max_confidence
    
    def process_transactions(self, input_file: str, output_file: str) -> pd.DataFrame:
        """
        Process transactions from CSV file and add LLM classifications
        """
        # Read the CSV file
        df = pd.read_csv(input_file)
        
        # Ensure required columns exist
        required_columns = ['Date', 'Description', 'Debit', 'Credit', 'Balance']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' not found in input file")
        
        # Process each transaction
        results = []
        
        for idx, row in df.iterrows():
            description = str(row['Description'])
            debit = float(row['Debit']) if pd.notna(row['Debit']) and row['Debit'] != '' else 0.0
            credit = float(row['Credit']) if pd.notna(row['Credit']) and row['Credit'] != '' else 0.0
            
            # Calculate net amount (positive for credit, negative for debit)
            amount = credit - debit
            
            # Extract UPI information
            upi_info = self.extract_upi_info(description)
            
            # Classify transaction
            category, account, confidence = self.classify_transaction(description, amount)
            
            # Create result record
            result = {
                'Date': row['Date'],
                'Description': description,
                'Amount': amount,
                'Debit': debit,
                'Credit': credit,
                'Balance': row['Balance'],
                'Category': category,
                'Account': account,
                'Confidence': round(confidence, 2),
                'Is_UPI': upi_info['is_upi'],
                'Payee': upi_info['payee'],
                'UPI_Transaction_Type': upi_info['transaction_type'],
                'UPI_Sender_Bank': upi_info['sender_bank'],
                'UPI_Reference': upi_info['reference_number'],
                'UPI_Transaction_ID': upi_info['transaction_id']
            }
            
            results.append(result)
        
        # Create output DataFrame
        output_df = pd.DataFrame(results)
        
        # Save to CSV
        output_df.to_csv(output_file, index=False)
        
        return output_df
    
    def generate_beancount_entries(self, classified_df: pd.DataFrame, output_file: str):
        """
        Generate beancount entries from classified transactions
        """
        with open(output_file, 'w') as f:
            f.write("; Classified transactions generated by LLM classifier\n")
            f.write("; Generated on {}\n\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            # Account declarations
            f.write("; Account declarations\n")
            accounts = set()
            for _, row in classified_df.iterrows():
                accounts.add(row['Account'])
            
            for account in sorted(accounts):
                f.write(f"1900-01-01 open {account} INR\n")
            
            f.write("1900-01-01 open Assets:Bank:ICICI:Checking INR\n")
            f.write("1900-01-01 open Equity:Opening-Balances INR\n\n")
            
            # Transactions
            for _, row in classified_df.iterrows():
                date_str = pd.to_datetime(row['Date']).strftime('%Y-%m-%d')
                description = str(row['Description']).replace('"', '\\"')
                amount = row['Amount']
                account = row['Account']
                
                # Add payee information if available
                payee_info = ""
                if row['Is_UPI'] and row['Payee']:
                    payee_info = f" ; payee: {row['Payee']}"
                
                f.write(f'{date_str} * "{description}"\n')
                if amount > 0:  # Credit
                    f.write(f"  Assets:Bank:ICICI:Checking               {amount:.2f} INR\n")
                    f.write(f"  {account}                              -{amount:.2f} INR{payee_info}\n")
                else:  # Debit
                    f.write(f"  Assets:Bank:ICICI:Checking               {amount:.2f} INR\n")
                    f.write(f"  {account}                               {abs(amount):.2f} INR{payee_info}\n")
                
                # Add metadata
                f.write(f"    ; category: {row['Category']}\n")
                f.write(f"    ; confidence: {row['Confidence']}\n")
                if row['Is_UPI']:
                    f.write(f"    ; upi_payee: {row['Payee']}\n")
                    f.write(f"    ; upi_bank: {row['UPI_Sender_Bank']}\n")
                f.write("\n")

def main():
    """Main function to run the LLM transaction classifier"""
    classifier = LLMTransactionClassifier()
    
    # Input and output file paths
    input_file = "/Users/sujoymukherjee/code/technoworld/llm_classification/classified_transactions.csv"
    output_csv = "/Users/sujoymukherjee/code/technoworld/llm_classification/classified_transactions1.csv"
    output_beancount = "/Users/sujoymukherjee/code/technoworld/llm_classification/classified_transactions.beancount"
    
    print("Starting LLM-based transaction classification...")
    
    # Process transactions
    classified_df = classifier.process_transactions(input_file, output_csv)
    
    print(f"Processed {len(classified_df)} transactions")
    print(f"Classification results saved to: {output_csv}")
    
    # Generate beancount entries
    classifier.generate_beancount_entries(classified_df, output_beancount)
    print(f"Beancount entries generated: {output_beancount}")
    
    # Print summary statistics
    print("\nClassification Summary:")
    category_counts = classified_df['Category'].value_counts()
    for category, count in category_counts.items():
        print(f"  {category}: {count}")
    
    print(f"\nUPI Transactions: {sum(classified_df['Is_UPI'])}")
    print(f"Average Confidence: {classified_df['Confidence'].mean():.2f}")
    
    # Show some example classifications
    print("\nSample Classifications:")
    sample_df = classified_df[['Description', 'Category', 'Payee', 'Confidence']].head(10)
    print(sample_df.to_string(index=False))

if __name__ == "__main__":
    main()
