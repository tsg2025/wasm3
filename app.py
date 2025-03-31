import streamlit as st
import pandas as pd
import json
from datetime import datetime

st.title("IndexedDB Stock Data Viewer")
st.write("View stock data stored in your browser's IndexedDB")

# Input for symbol to retrieve
symbol_to_retrieve = st.text_input("Enter stock symbol to retrieve", value="AAPL").upper()

# JavaScript component to retrieve and send data
retrieve_component = f"""
<script>
// Function to retrieve data from IndexedDB
async function retrieveStockData(symbol) {{
    return new Promise((resolve, reject) => {{
        let db;
        const request = indexedDB.open("StockDatabase", 2);
        
        request.onerror = (event) => {{
            reject("Database error: " + event.target.error);
        }};
        
        request.onsuccess = (event) => {{
            db = event.target.result;
            const transaction = db.transaction(["stockData"], "readonly");
            const objectStore = transaction.objectStore("stockData");
            const index = objectStore.index("symbol");
            const getRequest = index.getAll(IDBKeyRange.only(symbol));
            
            getRequest.onerror = (event) => {{
                reject("Error retrieving data: " + event.target.error);
            }};
            
            getRequest.onsuccess = (event) => {{
                const results = event.target.result.map(item => ({{
                    ...item.data,
                    Date: item.date,
                    Symbol: item.symbol
                }}));
                resolve(results);
            }};
        }};
        
        request.onupgradeneeded = (event) => {{
            // Database doesn't exist or needs upgrade
            resolve([]);
        }};
    }});
}}

// Main function to handle communication with Streamlit
async function sendData() {{
    const symbol = "{symbol_to_retrieve}";
    try {{
        const data = await retrieveStockData(symbol);
        window.parent.postMessage({{
            type: "streamlit:setComponentValue",
            value: {{
                data: data,
                symbol: symbol,
                status: "success"
            }}
        }}, "*");
    }} catch (error) {{
        window.parent.postMessage({{
            type: "streamlit:setComponentValue",
            value: {{
                error: error.toString(),
                status: "error"
            }}
        }}, "*");
    }}
}}

// Run when component loads
sendData();
</script>
"""

# Create component and handle response
response = st.components.v1.html(retrieve_component, height=0)

if response:
    try:
        # Parse the response
        if isinstance(response, str):
            response = json.loads(response)
        
        if response.get("status") == "success":
            data = response.get("data", [])
            symbol = response.get("symbol", "")
            
            if data:
                df = pd.DataFrame(data)
                
                # Convert Date column to datetime
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df = df.sort_values('Date')
                
                # Display results
                st.subheader(f"Retrieved {len(df)} records for {symbol}")
                st.dataframe(df)
                
                # Show chart if we have Close prices
                if 'Close' in df.columns:
                    st.line_chart(df.set_index('Date')['Close'])
                
                # Add download button
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name=f"{symbol}_stock_data.csv",
                    mime="text/csv"
                )
            else:
                st.warning(f"No data found in IndexedDB for symbol {symbol}")
        else:
            st.error(f"Error retrieving data: {response.get('error', 'Unknown error')}")
    except Exception as e:
        st.error(f"Error processing response: {str(e)}")

# Add some instructions
st.markdown("""
### Notes:
1. Data must have been previously stored using the uploader tool
2. Only shows data from the current browser (IndexedDB is browser-specific)
3. Data persists until browser cache is cleared
""")
