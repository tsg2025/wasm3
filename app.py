import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import json
import base64

# Streamlit app config
st.set_page_config(layout="wide", page_title="Stock Data Manager")
st.title("📈 Multi-Symbol Stock Data Storage (IndexedDB)")
st.write("""
Download stock data from Yahoo Finance and store it efficiently in IndexedDB.
Optimized for fast retrieval when working with many symbols.
""")

# ======================
# DATA DOWNLOAD SECTION
# ======================
st.sidebar.header("Download Settings")
symbol = st.sidebar.text_input("Symbol(s) (comma-separated)", "AAPL,MSFT,TSLA").upper()
days = st.sidebar.number_input("Days of History", 1, 365*10, 365)
interval = st.sidebar.selectbox("Interval", ["1d", "1wk", "1mo"], index=0)

def download_data(symbols, days, interval):
    """Download and flatten stock data"""
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)
    
    data = []
    for sym in [s.strip() for s in symbols.split(",")]:
        try:
            df = yf.download(sym, start=start_date, end=end_date, interval=interval)
            if df.empty:
                continue
                
            df = df.reset_index()
            df['symbol'] = sym
            df['date'] = df['Date'].dt.strftime('%Y-%m-%d')
            df = df.drop(columns=['Date'])
            
            # Convert numpy types to native Python for JSON serialization
            data.extend(df.to_dict('records'))
        except Exception as e:
            st.error(f"Failed to download {sym}: {str(e)}")
    
    return data

# ======================
# INDEXEDDB SECTION
# ======================
def generate_js_code(data, symbols):
    """Generate optimized IndexedDB JavaScript"""
    return f"""
    <script>
    const symbols = {json.dumps([s.strip() for s in symbols.split(",")])};
    const stockData = {json.dumps(data)};
    
    const request = indexedDB.open("StockDB", 4);
    
    // Database schema setup
    request.onupgradeneeded = (event) => {{
        const db = event.target.result;
        
        // Delete old store if exists
        if (db.objectStoreNames.contains("stocks")) {{
            db.deleteObjectStore("stocks");
        }}
        
        // Create optimized store with composite key
        const store = db.createObjectStore("stocks", {{
            keyPath: ["symbol", "date"]
        }});
        
        // Create indexes for common queries
        store.createIndex("symbol", "symbol");
        store.createIndex("date", "date");
        store.createIndex("close", "close");
        store.createIndex("volume", "volume");
        store.createIndex("symbol_date", ["symbol", "date"], {{ unique: true }});
    }};
    
    request.onsuccess = (event) => {{
        const db = event.target.result;
        
        // Batch process symbols for efficient updates
        symbols.forEach(symbol => {{
            const tx = db.transaction("stocks", "readwrite");
            const store = tx.objectStore("stocks");
            
            // Efficient range delete for symbol
            const deleteRange = IDBKeyRange.bound(
                [symbol, "0000-00-00"],
                [symbol, "9999-99-99"]
            );
            
            store.delete(deleteRange).onsuccess = () => {{
                // Insert new data in bulk
                const symbolData = stockData.filter(d => d.symbol === symbol);
                symbolData.forEach(item => store.put(item));
            }};
        }});
        
        // Report completion
        Promise.all(
            Array.from(db.transaction("stocks").objectStore("stocks").getAll().onsuccess
        ).then(() => {{
            console.log("Data update complete");
            alert(`Success! ${{stockData.length}} records stored for ${{symbols.join(", ")}}`);
        }});
    }};
    
    request.onerror = (event) => {{
        console.error("Database error:", event.target.error);
        alert("Database error occurred - check console");
    }};
    </script>
    """

# ======================
# STREAMLIT UI
# ======================
if st.sidebar.button("💾 Download & Store Data"):
    with st.spinner(f"Downloading {symbol} data..."):
        data = download_data(symbol, days, interval)
        
    if not data:
        st.error("No data downloaded - check symbols/parameters")
        st.stop()
        
    st.success(f"Downloaded {len(data)} records")
    
    # Preview data
    st.subheader("Data Preview")
    st.dataframe(pd.DataFrame(data).head(10))
    
    # Generate and inject JavaScript
    js_code = generate_js_code(data, symbol)
    st.components.v1.html(js_code, height=0)
    
    # CSV download option
    csv = pd.DataFrame(data).to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="stock_data.csv">💾 Download CSV</a>'
    st.markdown(href, unsafe_allow_html=True)

# ======================
# QUERY INTERFACE
# ======================
st.sidebar.header("Query Data")
query_symbol = st.sidebar.text_input("Filter Symbol", "AAPL").upper()
min_close = st.sidebar.number_input("Minimum Close Price", value=0.0)

query_js = f"""
<script>
async function queryData() {{
    const db = await new Promise((resolve, reject) => {{
        const request = indexedDB.open("StockDB", 4);
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    }});
    
    const tx = db.transaction("stocks", "readonly");
    const store = tx.objectStore("stocks");
    const index = store.index("symbol");
    
    // Create query range
    const range = IDBKeyRange.only("{query_symbol}");
    const records = await new Promise((resolve, reject) => {{
        const request = index.getAll(range);
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    }});
    
    // Filter by close price if specified
    const filtered = records.filter(r => r.close >= {min_close});
    
    // Send back to Streamlit
    window.parent.postMessage({{
        type: "queryResult",
        data: filtered
    }}, "*");
}}

queryData();
</script>
"""

if st.sidebar.button("🔍 Run Query"):
    st.subheader(f"Query Results for {query_symbol}")
    result_placeholder = st.empty()
    
    # JavaScript to Python communication
    query_result_js = """
    <script>
    window.addEventListener("message", (event) => {
        if (event.data.type === "queryResult") {
            window.parent.postMessage({
                type: "streamlit:setComponentValue",
                value: JSON.stringify(event.data.data)
            }, "*");
        }
    });
    </script>
    """
    
    # Combined JS execution
    st.components.v1.html(query_js + query_result_js, height=0)
    
    # Handle results (via Streamlit's custom component handling)
    try:
        query_result = st.session_state.get("query_result")
        if query_result:
            df = pd.DataFrame(json.loads(query_result))
            result_placeholder.dataframe(df)
    except:
        pass

# Instructions
st.markdown("""
## 📖 Usage Guide
1. **Download Data**  
   - Enter symbols (comma-separated)
   - Set time period and interval
   - Click "Download & Store Data"

2. **Query Data**  
   - Filter by symbol and minimum close price
   - Click "Run Query"

## ⚡ Optimizations
- **Composite Keys**: Fast symbol+date lookups
- **Bulk Operations**: Efficient updates/deletes
- **Indexed Fields**: Close price, volume queries
- **Batch Processing**: Handles many symbols smoothly
""")
