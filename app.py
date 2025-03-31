import streamlit as st
import pandas as pd
import json
import re

st.title("IndexedDB Stock Data Viewer")
st.write("View stock data stored in your browser's IndexedDB")

# Input for symbol to retrieve
symbol_to_retrieve = st.text_input("Enter stock symbol to retrieve", value="AAPL").upper()

if st.button("Retrieve Data"):
    # JavaScript component to retrieve and send data
    retrieve_component = f"""
    <script>
    // Function to process the unusual data format
    function processStockRecord(item) {{
        try {{
            // Handle both object and string formats
            let date, close, high, low, open, volume;
            
            if (typeof item.data === 'string') {{
                // Parse string format with proper regex
                const dateMatch = item.data.match(/Date['"][ ,:]+'([^']+)'/);
                const closeMatch = item.data.match(/Close['"][ ,:]+([\\d.]+)/);
                const highMatch = item.data.match(/High['"][ ,:]+([\\d.]+)/);
                const lowMatch = item.data.match(/Low['"][ ,:]+([\\d.]+)/);
                const openMatch = item.data.match(/Open['"][ ,:]+([\\d.]+)/);
                
                date = dateMatch ? dateMatch[1] : item.date;
                close = closeMatch ? parseFloat(closeMatch[1]) : null;
                high = highMatch ? parseFloat(highMatch[1]) : null;
                low = lowMatch ? parseFloat(lowMatch[1]) : null;
                open = openMatch ? parseFloat(openMatch[1]) : null;
            }} else {{
                // Handle object format
                date = item.data?.Date || item.date;
                close = item.data?.Close || null;
                high = item.data?.High || null;
                low = item.data?.Low || null;
                open = item.data?.Open || null;
                volume = item.data?.Volume || null;
            }}
            
            return {{
                Date: date,
                Symbol: item.symbol,
                Close: close,
                High: high,
                Low: low,
                Open: open,
                Volume: volume
            }};
        }} catch (e) {{
            console.error("Error processing record:", e);
            return null;
        }}
    }}

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
                    const results = event.target.result
                        .map(processStockRecord)
                        .filter(item => item && item.Close);
                    resolve(results);
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

    // Send data to Streamlit
    retrieveStockData("{symbol_to_retrieve}")
        .then(data => {{
            const jsonData = JSON.stringify({{
                data: data,
                symbol: "{symbol_to_retrieve}",
                status: "success"
            }});
            
            // Send data back to Streamlit
            window.parent.postMessage({{
                isWidget: true,
                type: "streamlit:setComponentValue",
                value: jsonData
            }}, "*");
        }})
        .catch(error => {{
            const jsonError = JSON.stringify({{
                error: error.toString(),
                status: "error"
            }});
            
            window.parent.postMessage({{
                isWidget: true,
                type: "streamlit:setComponentValue",
                value: jsonError
            }}, "*");
        }});
    </script>
    """

    # Create a placeholder for results
    results_placeholder = st.empty()
    results_placeholder.write("Retrieving data...")

    # Create the component and handle response
    response = st.components.v1.html(
        retrieve_component,
        height=0,
        key=f"retrieve_{symbol_to_retrieve}"
    )

    # Handle the response when it arrives
    if response:
        try:
            if isinstance(response, str):
                data = json.loads(response)
            else:
                data = response
            
            if data.get("status") == "success":
                df = pd.DataFrame(data["data"])
                
                # Convert and sort dates
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df = df.sort_values('Date')
                
                # Display results
                results_placeholder.empty()
                st.subheader(f"Retrieved {len(df)} records for {data['symbol']}")
                st.dataframe(df)
                
                # Show chart
                if 'Close' in df.columns:
                    st.line_chart(df.set_index('Date')['Close'])
                
                # Download button
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name=f"{data['symbol']}_stock_data.csv",
                    mime="text/csv"
                )
            else:
                results_placeholder.error(f"Error: {data.get('error', 'Unknown error')}")
        except Exception as e:
            results_placeholder.error(f"Error processing data: {str(e)}")

# Add message handler for component communication
message_handler = """
<script>
window.addEventListener("message", (event) => {
    if (event.data.type === "streamlit:setComponentValue") {
        const outData = {
            isWidget: true,
            type: "streamlit:setComponentValue",
            value: event.data.value
        };
        window.parent.postMessage(outData, "*");
    }
});
</script>
"""

st.components.v1.html(message_handler, height=0)
