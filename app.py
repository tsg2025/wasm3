import streamlit as st
import pandas as pd
import json

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
                // Parse string format
                const dateMatch = item.data.match(/Date['"][ ,:]+'([^']+)'/);
                const closeMatch = item.data.match(/Close['"][ ,:]+([\d.]+)/);
                const highMatch = item.data.match(/High['"][ ,:]+([\d.]+)/);
                const lowMatch = item.data.match(/Low['"][ ,:]+([\d.]+)/);
                const openMatch = item.data.match(/Open['"][ ,:]+([\d.]+)/);
                
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
            const outData = {{
                isWidget: true,
                type: "streamlit:setComponentValue",
                value: jsonData
            }};
            window.parent.postMessage(outData, "*");
        }})
        .catch(error => {{
            const jsonError = JSON.stringify({{
                error: error.toString(),
                status: "error"
            }});
            
            const outError = {{
                isWidget: true,
                type: "streamlit:setComponentValue",
                value: jsonError
            }};
            window.parent.postMessage(outError, "*");
        }});
    </script>
    """

    # Create a placeholder for results
    results_placeholder = st.empty()
    results_placeholder.write("Retrieving data...")

    # Create the component
    response = st.components.v1.html(
        retrieve_component,
        height=0,
        key=f"retrieve_{symbol_to_retrieve}"
    )

    # Handle the response via session state
    if st.session_state.get("indexeddb_data"):
        data = st.session_state.indexeddb_data
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
        
        # Clear the session state
        del st.session_state.indexeddb_data

# JavaScript message handler
message_handler = """
<script>
window.addEventListener("message", (event) => {
    if (event.data.type === "streamlit:setComponentValue") {
        try {
            const data = JSON.parse(event.data.value);
            const outData = {
                isWidget: true,
                type: "streamlit:setComponentValue",
                value: JSON.stringify(data)
            };
            window.parent.postMessage(outData, "*");
        } catch (e) {
            console.error("Error processing data:", e);
        }
    }
});
</script>
"""

# Add the message handler to the page
st.components.v1.html(message_handler, height=0)

# Handle incoming messages in Python
if st._runtime.exists():
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    ctx = get_script_run_ctx()
    if ctx and hasattr(ctx, "forward_msg_queue"):
        for msg in ctx.forward_msg_queue:
            if msg.type == "streamlit:setComponentValue":
                try:
                    data = json.loads(msg.value)
                    st.session_state.indexeddb_data = data
                    st.rerun()
                except json.JSONDecodeError:
                    pass
