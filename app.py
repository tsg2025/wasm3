import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import base64
from io import StringIO

# Streamlit app title and description
st.title("Yahoo Finance to IndexedDB (WASM) Uploader")
st.write("""
Download stock data from Yahoo Finance and store it in the browser's IndexedDB.
The data will persist in the user's browser.
""")

# User inputs
col1, col2 = st.columns(2)
with col1:
    symbol = st.text_input("Stock Symbol", value="AAPL").upper()
with col2:
    days = st.number_input("Days of History", min_value=1, max_value=365*5, value=30)

# New section for retrieving data
st.subheader("Retrieve Stored Data")
retrieve_symbol = st.text_input("Symbol to Retrieve", value="AAPL").upper()

if st.button("Retrieve Data from IndexedDB"):
    # JavaScript code to retrieve data from IndexedDB
    retrieve_js = f"""
    <script>
    // Function to handle retrieved data
    function displayData(data) {{
        // Create a hidden element with the data
        const container = document.createElement('div');
        container.id = 'retrievedDataContainer';
        container.style.display = 'none';
        container.textContent = JSON.stringify(data);
        document.body.appendChild(container);
        
        // Notify Streamlit that we have data
        window.parent.postMessage({{
            type: 'retrievedStockData',
            data: data
        }}, '*');
    }}

    // Open IndexedDB
    let db;
    const request = indexedDB.open("StockDatabase", 2);
    
    request.onerror = function(event) {{
        console.error("Database error:", event.target.error);
    }};
    
    request.onsuccess = function(event) {{
        db = event.target.result;
        const transaction = db.transaction(["stockData"], "readonly");
        const objectStore = transaction.objectStore("stockData");
        const index = objectStore.index("symbol");
        const request = index.getAll(IDBKeyRange.only("{retrieve_symbol}"));
        
        request.onerror = function(event) {{
            console.error("Error retrieving data:", event.target.error);
        }};
        
        request.onsuccess = function(event) {{
            const results = event.target.result;
            if (results && results.length > 0) {{
                // Extract and format the data
                const formattedData = results.map(item => ({{
                    ...item.data,
                    Date: item.date,
                    Symbol: item.symbol
                }}));
                displayData(formattedData);
            }} else {{
                console.log("No data found for symbol:", "{retrieve_symbol}");
                window.parent.postMessage({{
                    type: 'retrievedStockData',
                    data: []
                }}, '*');
            }}
        }};
    }};
    </script>
    """
    
    # Execute the JavaScript
    st.components.v1.html(retrieve_js, height=0)
    
    # Placeholder for the data display
    data_placeholder = st.empty()
    data_placeholder.write("Retrieving data from IndexedDB...")

# Handle the data when it comes back from JavaScript
retrieved_data_js = """
<script>
// Listen for messages from the iframe
window.addEventListener('message', function(event) {
    if (event.data.type === 'retrievedStockData') {
        // Send the data to Streamlit
        const data = event.data.data;
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: JSON.stringify(data)
        }, '*');
    }
});
</script>
"""

# Add the listener
st.components.v1.html(retrieved_data_js, height=0)

# Handle the returned data
if 'retrieved_data' not in st.session_state:
    st.session_state.retrieved_data = None

# Create a component to receive the data
retrieved_data = st.text_input("Retrieved Data Holder", key="retrieved_data_holder", disabled=True, label_visibility="collapsed")

if retrieved_data:
    try:
        data = pd.read_json(retrieved_data)
        if not data.empty:
            st.subheader(f"Retrieved Data for {retrieve_symbol}")
            st.write(data)
            
            # Add download button for retrieved data
            csv = data.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="{retrieve_symbol}_retrieved_data.csv">Download Retrieved Data as CSV</a>'
            st.markdown(href, unsafe_allow_html=True)
        else:
            st.warning(f"No data found in IndexedDB for symbol: {retrieve_symbol}")
    except ValueError:
        pass

if st.button("Download and Store Data"):
    try:
        # [Keep your existing download and store code here...]
        # ... (all your existing code for downloading and storing data)
        
        pass
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

# [Keep your existing instructions section here...]
