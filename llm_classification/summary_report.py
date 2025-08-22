"""
LLM Classification Summary Report
Generated on: 2025-08-15

This report summarizes the results of the LLM-based transaction classification.
"""

import pandas as pd
from datetime import datetime

def generate_summary_report():
    # Load classified transactions
    df = pd.read_csv('/Users/sujoymukherjee/code/technoworld/llm_classification/classified_transactions.csv')
    
    print("=" * 80)
    print("LLM TRANSACTION CLASSIFICATION SUMMARY REPORT")
    print("=" * 80)
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total transactions processed: {len(df)}")
    print()
    
    # Overall statistics
    print("OVERALL STATISTICS:")
    print("-" * 40)
    print(f"Total transactions: {len(df)}")
    print(f"UPI transactions: {sum(df['Is_UPI'])}")
    print(f"Non-UPI transactions: {len(df) - sum(df['Is_UPI'])}")
    print(f"Average confidence score: {df['Confidence'].mean():.2f}")
    print(f"High confidence (>0.5): {sum(df['Confidence'] > 0.5)}")
    print()
    
    # Category distribution
    print("CATEGORY DISTRIBUTION:")
    print("-" * 40)
    category_stats = df['Category'].value_counts()
    for category, count in category_stats.items():
        percentage = (count / len(df)) * 100
        print(f"{category:15}: {count:4} ({percentage:5.1f}%)")
    print()
    
    # UPI Analysis
    upi_df = df[df['Is_UPI'] == True]
    if len(upi_df) > 0:
        print("UPI TRANSACTION ANALYSIS:")
        print("-" * 40)
        print(f"Total UPI transactions: {len(upi_df)}")
        print()
        
        print("Top UPI Payees:")
        payee_stats = upi_df['Payee'].value_counts().head(10)
        for payee, count in payee_stats.items():
            avg_amount = upi_df[upi_df['Payee'] == payee]['Amount'].mean()
            print(f"  {payee:20}: {count:2} transactions, avg: ₹{abs(avg_amount):7.2f}")
        print()
        
        print("UPI Categories:")
        upi_categories = upi_df['Category'].value_counts()
        for category, count in upi_categories.items():
            percentage = (count / len(upi_df)) * 100
            print(f"  {category:15}: {count:2} ({percentage:5.1f}%)")
        print()
    
    # Amount analysis
    print("AMOUNT ANALYSIS:")
    print("-" * 40)
    credit_df = df[df['Amount'] > 0]
    debit_df = df[df['Amount'] < 0]
    
    print(f"Total credits: {len(credit_df):4} transactions, ₹{credit_df['Amount'].sum():12,.2f}")
    print(f"Total debits:  {len(debit_df):4} transactions, ₹{abs(debit_df['Amount'].sum()):12,.2f}")
    print(f"Net amount:    ₹{df['Amount'].sum():12,.2f}")
    print()
    
    print("Largest transactions:")
    largest_credits = df[df['Amount'] > 0].nlargest(5, 'Amount')
    largest_debits = df[df['Amount'] < 0].nsmallest(5, 'Amount')
    
    print("  Largest credits:")
    for _, row in largest_credits.iterrows():
        print(f"    ₹{row['Amount']:8,.2f} - {row['Description'][:50]}...")
    
    print("  Largest debits:")
    for _, row in largest_debits.iterrows():
        print(f"    ₹{row['Amount']:8,.2f} - {row['Description'][:50]}...")
    print()
    
    # Files generated
    print("FILES GENERATED:")
    print("-" * 40)
    print("1. classified_transactions.csv - Complete classification results")
    print("2. classified_transactions.beancount - Beancount journal entries")
    print()
    
    print("USAGE INSTRUCTIONS:")
    print("-" * 40)
    print("1. Review the classified_transactions.csv file for accuracy")
    print("2. Import the .beancount file into your beancount system")
    print("3. Use the UPI payee information for further analysis")
    print("4. Transactions with low confidence scores may need manual review")
    print()
    
    print("=" * 80)

if __name__ == "__main__":
    generate_summary_report()
