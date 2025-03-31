import streamlit as st
import pandas as pd
from datetime import datetime
import base64
from io import StringIO

st.title("IndexedDB Stock Data Viewer")
st.write("View and download stock data stored in your browser's IndexedDB")

# JavaScript code to retrieve data from IndexedDB
js_retrieve_code = """
<script>
function retrieveStockData(symbol, callback) {
    let db;
    const request = indexedDB.open("StockDatabase", 2);
    
    request.onerror = function(event) {
        console.error("Database error:", event.target.error);
        callback([]);
    };
    
    request.onsuccess = function(event) {
        db = event.target.result;
        const transaction = db.transaction(["stockData"], "readonly");
        const objectStore = transaction.objectStore("stockData");
        const index = objectStore.index("symbol");
        const request = index.getAll(IDBKeyRange.only(symbol));
        
        request.onerror = function(event) {
            console.error("Error retrieving data:", event.target.error);
            callback([]);
        };
        
        request.onsuccess = function(event) {
            const results = event.target.result;
            console.log(`Retrieved ${results.length} records for ${symbol}`);
            callback(results);
        };
    };
    
    request.onupgradeneeded = function(event) {
        console.log("Database upgrade needed - no data exists yet");
        callback([]);
    };
}

// Function to send data back to Streamlit
function sendDataToStreamlit(symbol) {
    retrieveStockData(symbol, function(data) {
        // Convert the data to a format Streamlit can handle
        const processedData = data.map(item => {
            return {
                ...item.data,
                Date: item.date,
                Symbol: item.symbol
            };
        });
        
        // Send to Streamlit
        window.parent.postMessage({
            type: 'stockData',
            data: processedData,
            symbol: symbol
        }, '*');
    });
}
</script>
"""

# Add the JavaScript to the page
st.components.v1.html(js_retrieve_code, height=0)

# UI for retrieving data
symbol_to_retrieve = st.text_input("Enter stock symbol to retrieve", value="AAPL").upper()

if st.button("Retrieve Data from IndexedDB"):
    # JavaScript to trigger data retrieval
    trigger_js = f"""
    <script>
    sendDataToStreamlit("{symbol_to_retrieve}");
    </script>
    """
    
    # Create a placeholder for the data
    data_placeholder = st.empty()
    data_placeholder.write("Retrieving data...")
    
    # Create a message handler to receive the data
    js_message_handler = """
    <script>
    window.addEventListener('message', function(event) {
        if (event.data.type === 'stockData') {
            // Convert the data to a string that Streamlit can parse
            const dataStr = JSON.stringify(event.data);
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: dataStr
            }, '*');
        }
    });
    </script>
    """
    
    # Combine all the JavaScript
    full_js = trigger_js + js_message_handler
    
    # Use Streamlit's component system to handle the response
    response = st.components.v1.html(full_js, height=0)
    
    # Parse the response when it arrives
    if response:
        try:
            data = eval(response) if isinstance(response, str) else response
            if isinstance(data, dict) and 'data' in data:
                df = pd.DataFrame(data['data'])
                
                # Convert Date column to datetime
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df = df.sort_values('Date')
                
                # Display the data
                st.subheader(f"Retrieved {len(df)} records for {data['symbol']}")
                st.dataframe(df)
                
                # Show a chart
                if not df.empty and 'Close' in df.columns:
                    st.line_chart(df.set_index('Date')['Close'])
                
                # Add download option
                csv = df.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="{symbol_to_retrieve}_from_indexeddb.csv">Download CSV</a>'
                st.markdown(href, unsafe_allow_html=True)
            else:
                st.warning("No data found for this symbol in IndexedDB")
        except Exception as e:
            st.error(f"Error processing data: {str(e)}")
