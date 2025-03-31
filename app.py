import streamlit as st
import pandas as pd
import requests
from io import StringIO
import json
import uuid

# Streamlit app configuration
st.set_page_config(page_title="CSV to IndexedDB", layout="wide")

# HTML/JS template with complete IndexedDB implementation
indexeddb_js = """
<script>
// Global database reference
let db;

// Open or create the database
const request = indexedDB.open("CSV_Database", 1);

request.onupgradeneeded = function(event) {
    db = event.target.result;
    // Create object store if it doesn't exist
    if (!db.objectStoreNames.contains("csv_data")) {
        const store = db.createObjectStore("csv_data", { keyPath: "id" });
        console.log("Created new object store");
    }
};

request.onsuccess = function(event) {
    db = event.target.result;
    console.log("Database opened successfully");
    // Notify Streamlit that we're ready
    window.parent.postMessage({
        type: "DB_READY",
        status: "success"
    }, "*");
};

request.onerror = function(event) {
    console.error("Database error:", event.target.error);
    window.parent.postMessage({
        type: "DB_ERROR",
        error: event.target.error
    }, "*");
};

// Store data in IndexedDB
function storeCSVData(data, filename) {
    return new Promise((resolve, reject) => {
        if (!db) {
            reject("Database not initialized");
            return;
        }

        const transaction = db.transaction("csv_data", "readwrite");
        const store = transaction.objectStore("csv_data");
        
        const record = {
            id: Date.now().toString() + "_" + Math.random().toString(36).substr(2, 5),
            filename: filename,
            data: data,
            timestamp: new Date().toISOString()
        };

        const request = store.add(record);

        request.onsuccess = function() {
            console.log("Data stored successfully");
            resolve(record.id);
        };

        request.onerror = function(event) {
            console.error("Error storing data:", event.target.error);
            reject(event.target.error);
        };
    });
}

// Retrieve all data from IndexedDB
function getAllCSVData() {
    return new Promise((resolve, reject) => {
        if (!db) {
            reject("Database not initialized");
            return;
        }

        const transaction = db.transaction("csv_data", "readonly");
        const store = transaction.objectStore("csv_data");
        const request = store.getAll();

        request.onsuccess = function() {
            resolve(request.result);
        };

        request.onerror = function(event) {
            reject(event.target.error);
        };
    });
}

// Message handler
window.addEventListener("message", async (event) => {
    if (event.data.type === "STORE_CSV") {
        try {
            const id = await storeCSVData(event.data.data, event.data.filename);
            window.parent.postMessage({
                type: "STORAGE_SUCCESS",
                id: id,
                filename: event.data.filename
            }, "*");
        } catch (error) {
            window.parent.postMessage({
                type: "STORAGE_ERROR",
                error: error.toString()
            }, "*");
        }
    }
    else if (event.data.type === "GET_ALL_DATA") {
        try {
            const allData = await getAllCSVData();
            window.parent.postMessage({
                type: "ALL_DATA",
                data: allData
            }, "*");
        } catch (error) {
            window.parent.postMessage({
                type: "DATA_ERROR",
                error: error.toString()
            }, "*");
        }
    }
});
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
    st.title("CSV to IndexedDB Storage")
    
    # Initialize session state
    if 'storage_status' not in st.session_state:
        st.session_state.storage_status = None
    if 'stored_data' not in st.session_state:
        st.session_state.stored_data = None
    
    # Display status
    if st.session_state.storage_status:
        if st.session_state.storage_status['type'] == 'success':
            st.success(st.session_state.storage_status['message'])
        else:
            st.error(st.session_state.storage_status['message'])
    
    # File upload section
    st.header("Upload CSV File")
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv", "txt"])
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.success("CSV loaded successfully!")
            
            st.subheader("Data Preview")
            st.dataframe(df.head())
            
            # Convert to list of dictionaries for JSON serialization
            data = df.to_dict(orient='records')
            
            # Send to IndexedDB
            js_code = f"""
            <script>
                window.postMessage({{
                    type: "STORE_CSV",
                    data: {json.dumps(data)},
                    filename: "{uploaded_file.name}"
                }}, "*");
            </script>
            """
            st.components.v1.html(js_code, height=0)
            
            with st.spinner('Storing data in IndexedDB...'):
                # We can't directly await the response in Streamlit's execution model
                # So we'll use a placeholder and verify manually
                pass
            
        except Exception as e:
            st.error(f"Error processing file: {e}")
    
    # GitHub section
    st.header("Load from GitHub")
    github_url = st.text_input("Enter GitHub raw CSV URL")
    
    if github_url and st.button("Load from GitHub"):
        csv_content = download_csv_from_github(github_url)
        if csv_content:
            try:
                df = pd.read_csv(StringIO(csv_content))
                st.success("CSV loaded from GitHub successfully!")
                
                st.subheader("Data Preview")
                st.dataframe(df.head())
                
                filename = github_url.split("/")[-1]
                data = df.to_dict(orient='records')
                
                js_code = f"""
                <script>
                    window.postMessage({{
                        type: "STORE_CSV",
                        data: {json.dumps(data)},
                        filename: "{filename}"
                    }}, "*");
                </script>
                """
                st.components.v1.html(js_code, height=0)
                
                with st.spinner('Storing data in IndexedDB...'):
                    pass
                
            except Exception as e:
                st.error(f"Error processing GitHub CSV: {e}")
    
    # Verification section
    st.header("Verify Storage")
    if st.button("Check IndexedDB Contents"):
        js_code = """
        <script>
            window.postMessage({
                type: "GET_ALL_DATA"
            }, "*");
        </script>
        """
        st.components.v1.html(js_code, height=0)
        
        with st.spinner('Checking IndexedDB...'):
            # Placeholder - in a real app you'd await the response
            st.info("Check your browser's console (F12) for IndexedDB contents")
    
    # JavaScript to handle messages from our IndexedDB operations
    message_handler_js = """
    <script>
    window.addEventListener('message', (event) => {
        if (event.data.type === "STORAGE_SUCCESS") {
            console.log('Storage successful:', event.data);
        }
        else if (event.data.type === "STORAGE_ERROR") {
            console.error('Storage error:', event.data);
        }
        else if (event.data.type === "ALL_DATA") {
            console.log('All IndexedDB data:', event.data.data);
        }
        else if (event.data.type === "DATA_ERROR") {
            console.error('Data retrieval error:', event.data);
        }
    });
    </script>
    """
    st.components.v1.html(message_handler_js, height=0)
    
    # Debug instructions
    st.header("Debugging Instructions")
    st.markdown("""
    1. Open browser developer tools (F12)
    2. Go to the Application tab
    3. Under IndexedDB, look for "CSV_Database"
    4. Check the Console tab for operation logs
    5. Click "Check IndexedDB Contents" to verify storage
    """)

if __name__ == "__main__":
    main()
