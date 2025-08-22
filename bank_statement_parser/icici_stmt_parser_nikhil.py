import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

st.title("🏦 Bank Statement Parser")

uploaded_file = st.file_uploader("Upload Bank Statement (PDF)", type=["pdf"])
pdf_password = st.text_input("Enter PDF Password", type="password")

if uploaded_file and pdf_password:
    try:
        transactions = []
        buffer = []
        prev_balance = None

        # Regex patterns
        date_pattern = re.compile(r"\d{2}[-.]\d{2}[-.]\d{4}")                 # dd-mm-yyyy OR dd.mm.yyyy
        amount_pattern = re.compile(r"\d{1,3}(?:,\d{2,3})*\.\d{2}")           # strict: 1,234.56 / 12,34,567.89 / 123.45

        # Valid transaction start markers
        txn_starts = ("UPI", "NEFT", "IMPS", "RTGS", "ATM", "ACH", "VPS", "BIL", "MMT", "CLG")

        with pdfplumber.open(uploaded_file, password=pdf_password) as pdf:

            # --- Parse transactions from all pages ---
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                for line in text.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("DATE MODE"):
                        continue

                    # --- Skip headers ---
                    if ("Statement of Transactions" in line 
                        or "C/F" in line 
                        or "Closing" in line):
                        continue

                    # --- Handle Opening / B/F ---
                    if not transactions and ("B/F" in line or "Opening" in line):
                        nums = re.findall(amount_pattern, line)
                        balance = nums[-1] if nums else ""
                        transactions.append({
                            "Date": "",
                            "Particulars": line,
                            "Deposits": "",
                            "Withdrawals": "",
                            "Balance": balance
                        })
                        continue

                    # --- If line has NO date ---
                    if not date_pattern.search(line):
                        if buffer:
                            buffer.append(line)   # still collecting narration
                        elif line.startswith(txn_starts):
                            buffer.append(line)   # valid txn start (UPI/NEFT etc.)
                        elif transactions:
                            transactions[-1]["Particulars"] += " " + line
                        continue

                    # --- If line HAS a date (finalize transaction) ---
                    buffer.append(line)
                    full_line = " ".join(buffer)
                    buffer = []

                    # Extract dates (may be more than one, pick the first for transaction date)
                    all_dates = date_pattern.findall(full_line)
                    date = all_dates[0] if all_dates else ""

                    # Remove all dates before extracting amounts
                    line_without_dates = full_line
                    for d in all_dates:
                        line_without_dates = line_without_dates.replace(d, "")

                    # Extract amounts safely
                    nums = re.findall(amount_pattern, line_without_dates)
                    balance = nums[-1] if nums else ""
                    deposits, withdrawals = "", ""

                    if len(nums) == 3:  # Deposit + Withdrawal + Balance
                        deposits, withdrawals, balance = nums
                    elif len(nums) == 2:  # One amount + Balance
                        amount, balance = nums
                        if prev_balance is not None and amount.strip() != "" and balance.strip() != "":
                            try:
                                amt = float(amount.replace(",", ""))
                                bal = float(balance.replace(",", ""))
                                prev_bal = float(prev_balance.replace(",", ""))
                                if bal > prev_bal:
                                    deposits = amount
                                else:
                                    withdrawals = amount
                            except ValueError:
                                withdrawals = amount
                        else:
                            withdrawals = amount if amount.strip() != "" else ""
                    prev_balance = balance

                    # Clean particulars (remove ALL dates + numbers)
                    particulars = full_line
                    for d in all_dates:
                        particulars = particulars.replace(d, "")
                    for n in nums:
                        particulars = particulars.replace(n, "")
                    particulars = particulars.strip()

                    # --- 🚫 Skip TDS on Fixed Deposit transactions ---
                    skip_keywords = ["TDS", "Tax Deducted", "FD TDS", "TDS on FD", "TDS ON INTEREST"]
                    if any(kw.lower() in particulars.lower() for kw in skip_keywords):
                        continue

                    # --- 🚫 Skip transactions where Particulars is just an account number ---
                    if re.fullmatch(r"\d{8,}", particulars.replace(" ", "")):
                        continue

                    transactions.append({
                        "Date": date,
                        "Particulars": particulars,
                        "Deposits": deposits,
                        "Withdrawals": withdrawals,
                        "Balance": balance
                    })

        # --- Show transactions ---
        if transactions:
            df = pd.DataFrame(transactions)

            # 🔹 Remove first 2 transactions
            df = df.iloc[2:].reset_index(drop=True)

            st.success(f"✅ Extracted transactions for uploaded file")
            st.dataframe(df)

            # Save Excel
            output = BytesIO()
            df.to_excel(output, index=False, engine="openpyxl")
            output.seek(0)

            st.download_button(
                label="📥 Download Excel",
                data=output,
                file_name="parsed_transactions.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ No valid transactions found.")

    except Exception as e:
        st.error(f"Error opening PDF: {e}")
