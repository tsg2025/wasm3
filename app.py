import streamlit as st
import pandas as pd
import base64
from io import StringIO

# Streamlit app configuration
st.set_page_config(page_title="CSV to IndexedDB", layout="wide")

# Main app
st.title("Advanced CSV to IndexedDB Storage")
st.markdown("""
Store CSV data in the browser's IndexedDB with these features:
- Persistent browser storage
- Data preview
- Multiple dataset support
- Storage verification
""")

# File upload section
uploaded_file = st.file_uploader("Choose a CSV file", type=["csv", "txt"])

if uploaded_file is not None:
    try:
        # Read and preview data
        df = pd.read_csv(uploaded_file)
        
        st.subheader("Data Preview")
        st.dataframe(df.head())
        
        # Get unique dataset name
        dataset_name = st.text_input(
            "Name this dataset (for retrieval)", 
            value=uploaded_file.name.split('.')[0]
        )
        
        # Convert to JSON
        data_json = df.to_json(orient='records')
        
        # Enhanced JavaScript with dataset management
        js_code = f"""
        <script>
        // Database configuration
        const DB_NAME = "CSV_Database";
        const DB_VERSION = 2;
        const STORE_NAME = "csv_datasets";
        
        let db;
        const request = indexedDB.open(DB_NAME, DB_VERSION);
        
        // Database upgrade/creation
        request.onupgradeneeded = function(event) {{
            db = event.target.result;
            
            // Create object store if it doesn't exist
            if (!db.objectStoreNames.contains(STORE_NAME)) {{
                const store = db.createObjectStore(STORE_NAME, {{
                    keyPath: "id",
                    autoIncrement: true
                }});
                
                // Create indexes for efficient querying
                store.createIndex("name", "name", {{ unique: false }});
                store.createIndex("timestamp", "timestamp", {{ unique: false }});
                
                console.log("Database setup complete");
            }}
        }};
        
        // Database opened successfully
        request.onsuccess = function(event) {{
            db = event.target.result;
            console.log("Database opened successfully");
            
            // Prepare transaction
            const transaction = db.transaction(STORE_NAME, "readwrite");
            const store = transaction.objectStore(STORE_NAME);
            
            // Prepare dataset
            const timestamp = new Date().toISOString();
            const data = {{
                name: "{dataset_name}",
                filename: "{uploaded_file.name}",
                data: {data_json},
                timestamp: timestamp,
                columns: {json.dumps(list(df.columns))},
                rowCount: {len(df)}
            }};
            
            // Store operation
            const addRequest = store.add(data);
            
            addRequest.onsuccess = function() {{
                console.log("Dataset stored successfully");
                
                // Update UI through Streamlit
                window.parent.postMessage({{
                    type: "STORAGE_SUCCESS",
                    dataset: "{dataset_name}",
                    rows: {len(df)},
                    timestamp: timestamp
                }}, "*");
            }};
            
            addRequest.onerror = function(event) {{
                console.error("Storage error:", event.target.error);
                window.parent.postMessage({{
                    type: "STORAGE_ERROR",
                    error: event.target.error.toString()
                }}, "*");
            }};
        }};
        
        // Database error
        request.onerror = function(event) {{
            console.error("Database error:", event.target.error);
            window.parent.postMessage({{
                type: "DB_ERROR",
                error: event.target.error.toString()
            }}, "*");
        }};
        </script>
        """
        
        # Execute JavaScript
        st.components.v1.html(js_code, height=0)
        
        # Download option
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="{uploaded_file.name}">Download CSV</a>'
        st.markdown(href, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")

# Verification section
st.header("Storage Verification")

if st.button("List Stored Datasets"):
    js_code = """
    <script>
    const DB_NAME = "CSV_Database";
    const STORE_NAME = "csv_datasets";
    
    const request = indexedDB.open(DB_NAME);
    
    request.onsuccess = function(event) {
        const db = event.target.result;
        const transaction = db.transaction(STORE_NAME, "readonly");
        const store = transaction.objectStore(STORE_NAME);
        const request = store.getAll();
        
        request.onsuccess = function() {
            const datasets = request.result;
            console.log("Stored datasets:", datasets);
            
            window.parent.postMessage({
                type: "DATASETS_LIST",
                count: datasets.length,
                datasets: datasets.map(d => ({
                    name: d.name,
                    filename: d.filename,
                    timestamp: d.timestamp,
                    rows: d.rowCount
                }))
            }, "*");
        };
        
        request.onerror = function(event) {
            console.error("Error retrieving data:", event.target.error);
            window.parent.postMessage({
                type: "RETRIEVAL_ERROR",
                error: event.target.error.toString()
            }, "*");
        };
    };
    
    request.onerror = function(event) {
        console.error("Database error:", event.target.error);
        window.parent.postMessage({
            type: "DB_ERROR",
            error: event.target.error.toString()
        }, "*");
    };
    </script>
    """
    st.components.v1.html(js_code, height=0)

# Message handler for JavaScript communication
message_handler = """
<script>
window.addEventListener('message', (event) => {
    if (event.data.type === "STORAGE_SUCCESS") {
        console.log("Storage success:", event.data);
        alert(`Dataset "${event.data.dataset}" stored successfully!\\nRows: ${event.data.rows}\\nTimestamp: ${event.data.timestamp}`);
    }
    else if (event.data.type === "DATASETS_LIST") {
        console.log("Datasets retrieved:", event.data);
        alert(`Found ${event.data.count} datasets in IndexedDB:\\n${
            event.data.datasets.map(d => 
                `• ${d.name} (${d.rows} rows, ${d.timestamp})`
            ).join('\\n')
        }`);
    }
    else if (event.data.type.endsWith("_ERROR")) {
        console.error("Error:", event.data);
        alert(`Error: ${event.data.error}`);
    }
});
</script>
"""
st.components.v1.html(message_handler, height=0)

# Instructions
st.header("Instructions")
st.markdown("""
1. Upload a CSV file
2. Optionally name the dataset
3. Data will be stored in your browser's IndexedDB
4. Use the verification button to check stored data
5. Data persists even after page refresh
""")
