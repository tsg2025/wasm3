import streamlit as st
import pandas as pd
import json

st.title("IndexedDB Stock Data Viewer")
st.write("View stock data stored in your browser's IndexedDB")

# Input for symbol to retrieve
symbol_to_retrieve = st.text_input("Enter stock symbol to retrieve", value="AAPL").upper()

# JavaScript component to retrieve and send data
retrieve_component = f"""
<script>
async function retrieveStockData(symbol) {{
    return new Promise((resolve, reject) => {{
        const request = indexedDB.open("StockDatabase", 2);
        
        request.onsuccess = function(event) {{
            const db = event.target.result;
            const transaction = db.transaction(["stockData"], "readonly");
            const objectStore = transaction.objectStore("stockData");
            const index = objectStore.index("symbol");
            const getRequest = index.getAll(IDBKeyRange.only(symbol));
            
            getRequest.onsuccess = function(event) {{
                const results = event.target.result;
                
                // Process the data - handle the unusual structure
                const processedData = results.map(item => {{
                    // Extract the numeric values from the string-like data
                    const closeValue = item.data?.Close || 
                                     (typeof item.data === 'string' ? parseFloat(item.data.match(/Close['"], 'AAPL'}}: ([\d.]+)/)?.[1]) : null);
                    
                    const dateValue = item.data?.Date || 
                                    (typeof item.data === 'string' ? item.data.match(/Date['"], '}}: '([\d-]+)/)?.[1] : null);
                    
                    return {{
                        Date: dateValue || item.date,
                        Symbol: item.symbol,
                        Close: closeValue,
                        // Add other fields if available
                        High: item.data?.High || null,
                        Low: item.data?.Low || null,
                        Open: item.data?.Open || null,
                        Volume: item.data?.Volume || null
                    }};
                }}).filter(item => item.Close); // Only include records with valid Close prices
                
                resolve(processedData);
            }};
            
            getRequest.onerror = function(event) {{
                reject("Error retrieving data: " + event.target.error);
            }};
        }};
        
        request.onerror = function(event) {{
            reject("Database error: " + event.target.error);
        }};
    }});
}}

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
                
                # Convert Date column to datetime and sort
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
                st.warning(f"No valid data found in IndexedDB for symbol {symbol}")
        else:
            st.error(f"Error retrieving data: {response.get('error', 'Unknown error')}")
    except Exception as e:
        st.error(f"Error processing response: {str(e)}")
