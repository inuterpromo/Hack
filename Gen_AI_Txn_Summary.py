import os  
import pandas as pd  
import openai
import base64
from openai import AzureOpenAI
# -------------------------------  
# Set your OpenAI API key  
# -------------------------------  
# Option 1: Using an environment variable for security  
 
# openai.api_key = os.getenv("OPENAI_API_KEY")  
# Option 2: Alternatively, you may assign it directly (less secure)  
key1 =
 
endpoint = os.getenv("ENDPOINT_URL", "")
deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4o")
subscription_key = os.getenv("AZURE_OPENAI_API_KEY", key1 )
 
# Initialize Azure OpenAI client with key-based authentication
 
# -------------------------------  
# Define the list of sanctioned countries considered high risk for financial crime.  
# -------------------------------  
sanctioned_countries = [  
    "Afghanistan", "Belarus", "Burma", "Cuba", "North Korea", "Iran", "Iraq",  
    "Libya", "Russia", "South Sudan", "Sudan", "Syria", "Ukraine", "Venezuela", "Yemen"  
]  
 
# -------------------------------  
# Load and process the Excel file containing transactions.  
# -------------------------------  
excel_filename = "C:\\Users\\KKhare\\Downloads\\synthetic_transactions_complete.xlsx"
df = pd.read_excel(excel_filename, engine = 'openpyxl')  
 
# Convert the 'Date' column to datetime format.  
df['Date'] = pd.to_datetime(df['Date'])  
 
# Define a function to classify each transaction's financial crime risk.  
def classify_financial_crime(row):  
    # If either origin or destination is sanctioned, flag as "High"  
    if row['Origin_country'] in sanctioned_countries or row['Destination_country'] in sanctioned_countries:  
        return "High"  
    # Otherwise, retain the risk provided in the CSV.  
    return row['Risk']  
 
# Apply the risk classification function to the DataFrame.  
df['Financial_Crime_Risk'] = df.apply(classify_financial_crime, axis=1)  
 
# -------------------------------  
# Calculate summary statistics.  
# -------------------------------  
total_transactions = len(df)  
total_amount = df['Amount'].sum()  
receipts_amount = df[df['Receipt/Payment'] == 'Receipt']['Amount'].sum()  
payments_amount = df[df['Receipt/Payment'] == 'Payment']['Amount'].sum()  
 
# Summarize risk breakdown  
risk_summary = df.groupby('Financial_Crime_Risk').agg({'Amount': ['sum', 'count']}).reset_index()  
risk_summary.columns = ['Risk', 'Total_Amount', 'Transaction_Count']  
 
# Summarize by 3rd party business nature  
business_summary = df.groupby('3rd_party_business_nature').agg({'Amount': ['sum', 'count']}).reset_index()  
business_summary.columns = ['3rd_party_business_nature', 'Total_Amount', 'Transaction_Count']  
 
# Sanctioned transactions summary (High risk due to sanctioned countries)  
sanctioned_transactions = df[df['Financial_Crime_Risk'] == 'High']  
sanctioned_summary = {  
    "count": len(sanctioned_transactions),  
    "total_amount": sanctioned_transactions['Amount'].sum()  
}  
 
# -------------------------------  
# Prepare a narrative summary prompt for the Gen AI agent.  
# -------------------------------  
prompt = f"""You are a seasoned financial crime analyst. Analyze the following statistics from a financial transactions dataset and generate a detailed narrative report. The report should explain key findings, potential financial crime risks, and operational insights.  
 
Key Statistics:
- Total Transactions: {total_transactions}
- Total Transaction Amount: {total_amount:,.2f}
- Receipts Total: {receipts_amount:,.2f}
- Payments Total: {payments_amount:,.2f}
 
Risk Summary (by assigned financial crime risk):
{risk_summary.to_string(index=False)}
 
3rd Party Business Nature Summary:
{business_summary.to_string(index=False)}
 
Sanctioned Transactions Summary (High Financial Crime Risk):
- Count: {sanctioned_summary['count']}
- Total Amount: {sanctioned_summary['total_amount']:,.2f}
 
Please provide a narrative report that:
1. Introduces the dataset and its context.
2. Discusses the volume and financial activity.
3. Explains the risks associated with high-risk transactions, especially those involving sanctioned countries.
4. Offers recommendations or observations on potential financial crime concerns.
Ensure the tone is analytical, data-driven, and insightful.
"""
 
# -------------------------------
# Define a function to call the Gen AI agent using the updated API interface.
# -------------------------------
def get_ai_summary(prompt_text):
    try:  
        client = AzureOpenAI(  
            azure_endpoint=endpoint,  
            api_key=subscription_key,  
            api_version="2025-01-01-preview",  
        )  
        completion = client.chat.completions.create(  
            model=deployment,  
            messages=[  
                {"role": "system", "content": "You are a knowledgeable and analytical financial crime analyst."},  
                {"role": "user", "content": prompt_text}  
            ],  
            max_tokens=500,  
            temperature=0.5,  
            top_p=0.95  
        )  
   
        # Access the response content using the new recommended access method
        summary = completion.choices[0].message.content.strip()  
        return summary
    except Exception as e:
        print("Error calling the Gen AI agent:", e)
        return None
 
# -------------------------------
# Generate and display the AI-narrative summary report.
# -------------------------------
summary_report = get_ai_summary(prompt)
 
if summary_report is not None:
    print("AI Generated Summary Report for Financial Crime Risk Analysis")
    print("--------------------------------------------------------------")
    print(summary_report)
 
    # Optionally, write the generated report to a file.
    report_filename = "ai_summary_report.txt"
    with open(report_filename, "w") as f:
        f.write(summary_report)
    print(f"\nThe AI-generated summary report has been written to '{report_filename}'.")
else:
    print("Failed to generate the AI summary report.")