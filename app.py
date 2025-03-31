import streamlit as st
import pandas as pd
import requests
from io import StringIO
import json
import uuid

# Streamlit app configuration
st.set_page_config(page_title="CSV to IndexedDB WASM", layout="wide")

# HTML/JS template for IndexedDB operations
indexeddb_js = """
<script>
// IndexedDB setup
let db;
const dbName = "CSV_DB";
const storeName = "csv_store";

// Open or create IndexedDB
const request = indexedDB.open(dbName, 1);

request.onupgradeneeded = function(event) {
    db = event.target.result;
    if (!db.objectStoreNames.contains(storeName)) {
        db.createObjectStore(storeName, { keyPath: "id" });
    }
    console.log("Database upgraded");
};

request.onsuccess = function(event) {
    db = event.target.result;
    console.log("Database opened successfully");
};

request.onerror = function(event) {
    console.error("Database error:", event.target.error);
};

// Function to store data in IndexedDB
function storeDataInIndexedDB(data, filename) {
    return new Promise((resolve, reject) => {
        if (!db) {
            reject("Database not initialized");
            return;
        }

        const transaction = db.transaction(storeName, "readwrite");
        const store = transaction.objectStore(storeName);
        
        const record = {
            id: Date.now().toString() + "_" + Math.random().toString(36).substr(2, 9),
            filename: filename,
            data: data,
            timestamp: new Date().toISOString(),
            size: JSON.stringify(data).length
        };

        const request = store.add(record);

        request.onsuccess = function() {
            console.log("Data stored successfully");
            resolve(true);
        };

        request.onerror = function(event) {
            console.error("Error storing data:", event.target.error);
            reject(event.target.error);
        };
    });
}

// Listen for messages from Streamlit
window.addEventListener('message', (event) => {
    if (event.data.type === 'STORE_CSV') {
        const { data, filename } = event.data;
        storeDataInIndexedDB(data, filename)
            .then(() => {
                // Send success message back to Streamlit
                window.parent.postMessage({
                    type: 'STORAGE_SUCCESS',
                    message: 'Data stored in IndexedDB successfully'
                }, '*');
            })
            .catch(error => {
                window.parent.postMessage({
                    type: 'STORAGE_ERROR',
                    message: 'Failed to store data: ' + error
                }, '*');
            });
    }
});

// Report when the script is loaded and ready
window.parent.postMessage({
    type: 'SCRIPT_READY',
    message: 'IndexedDB script is ready'
}, '*');
</script>
"""

# Display the JS in Streamlit
st.components.v1.html(indexeddb_js, height=0)

def download_csv_from_github(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except Exception as e:
        st.error(f"Error downloading CSV from GitHub: {e}")
        return None

def main():
    st.title("CSV to IndexedDB (WASM) Uploader")
    
    # Initialize session state for messages
    if 'storage_message' not in st.session_state:
        st.session_state.storage_message = None
    
    # Display storage message if exists
    if st.session_state.storage_message:
        if st.session_state.storage_message['type'] == 'success':
            st.success(st.session_state.storage_message['text'])
        else:
            st.error(st.session_state.storage_message['text'])
    
    # Option 1: Upload CSV directly
    st.header("Option 1: Upload CSV File")
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    if uploaded_file is not None:
        try:
            # Read CSV file
            df = pd.read_csv(uploaded_file)
            st.success("CSV file loaded successfully!")
            
            # Show preview
            st.subheader("Data Preview")
            st.write(df.head())
            
            # Convert to JSON for sending to JS
            csv_data = df.to_dict(orient='records')
            
            # Generate unique ID for this transaction
            transaction_id = str(uuid.uuid4())
            
            # Send data to JS for IndexedDB storage
            js_code = f"""
            <script>
                window.postMessage({{
                    type: 'STORE_CSV',
                    data: {json.dumps(csv_data)},
                    filename: "{uploaded_file.name}",
                    transaction_id: "{transaction_id}"
                }}, '*');
            </script>
            """
            st.components.v1.html(js_code, height=0)
            
            # Placeholder for storage status
            with st.spinner('Storing data in IndexedDB...'):
                # We'd normally wait for a response here, but Streamlit makes this tricky
                # In a production app, you'd use a more sophisticated message passing system
                pass
            
        except Exception as e:
            st.error(f"Error processing CSV file: {e}")
    
    # Option 2: Load from GitHub URL
    st.header("Option 2: Load CSV from GitHub")
    github_url = st.text_input("Enter GitHub raw CSV URL (e.g., https://raw.githubusercontent.com/user/repo/branch/file.csv)")
    
    if github_url and st.button("Load from GitHub"):
        csv_content = download_csv_from_github(github_url)
        if csv_content:
            try:
                # Read CSV content
                df = pd.read_csv(StringIO(csv_content))
                st.success("CSV file loaded from GitHub successfully!")
                
                # Show preview
                st.subheader("Data Preview")
                st.write(df.head())
                
                # Get filename from URL
                filename = github_url.split("/")[-1]
                
                # Convert to JSON for sending to JS
                csv_data = df.to_dict(orient='records')
                
                # Generate unique ID for this transaction
                transaction_id = str(uuid.uuid4())
                
                # Send data to JS for IndexedDB storage
                js_code = f"""
                <script>
                    window.postMessage({{
                        type: 'STORE_CSV',
                        data: {json.dumps(csv_data)},
                        filename: "{filename}",
                        transaction_id: "{transaction_id}"
                    }}, '*');
                </script>
                """
                st.components.v1.html(js_code, height=0)
                
                with st.spinner('Storing data in IndexedDB...'):
                    pass
                
            except Exception as e:
                st.error(f"Error processing CSV content: {e}")
    
    # Instructions section
    st.header("Instructions")
    st.markdown("""
    1. **Option 1**: Upload a CSV file directly using the file uploader
    2. **Option 2**: Provide a GitHub raw CSV URL to load the file
    3. The data will be stored in your browser's IndexedDB
    4. Check browser console (F12) for storage logs
    """)

    # JavaScript to handle messages from the iframe
    message_js = """
    <script>
    // Listen for messages from the iframe
    window.addEventListener('message', (event) => {
        if (event.data.type === 'STORAGE_SUCCESS') {
            console.log('Storage success:', event.data.message);
        } else if (event.data.type === 'STORAGE_ERROR') {
            console.error('Storage error:', event.data.message);
        } else if (event.data.type === 'SCRIPT_READY') {
            console.log(event.data.message);
        }
    });
    </script>
    """
    st.components.v1.html(message_js, height=0)

if __name__ == "__main__":
    main()
