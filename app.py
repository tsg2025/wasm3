import streamlit as st
import pandas as pd
import requests
from io import StringIO
import json

# Streamlit app configuration
st.set_page_config(page_title="CSV to IndexedDB WASM", layout="wide")

# HTML/JS template for IndexedDB operations
indexeddb_js = """
<script>
// IndexedDB setup
let db;
const request = indexedDB.open("CSVDatabase", 1);

request.onupgradeneeded = (event) => {
    db = event.target.result;
    if (!db.objectStoreNames.contains("csvFiles")) {
        db.createObjectStore("csvFiles", { keyPath: "id" });
    }
};

request.onsuccess = (event) => {
    db = event.target.result;
    console.log("IndexedDB initialized successfully");
};

request.onerror = (event) => {
    console.error("IndexedDB error:", event.target.error);
};

async function storeCSVInIndexedDB(csvData, filename) {
    return new Promise((resolve, reject) => {
        if (!db) {
            reject("IndexedDB not initialized");
            return;
        }

        const transaction = db.transaction(["csvFiles"], "readwrite");
        const store = transaction.objectStore("csvFiles");
        
        const record = {
            id: Date.now(),
            filename: filename,
            data: csvData,
            timestamp: new Date().toISOString()
        };

        const request = store.add(record);

        request.onsuccess = () => {
            console.log("CSV data stored successfully");
            resolve(true);
        };

        request.onerror = (event) => {
            console.error("Error storing CSV data:", event.target.error);
            reject(event.target.error);
        };
    });
}

// Function to handle messages from Python
async function handlePythonMessage(data) {
    if (data.action === "store_csv") {
        try {
            await storeCSVInIndexedDB(data.csv_data, data.filename);
            console.log("CSV stored in IndexedDB successfully");
        } catch (error) {
            console.error("Failed to store CSV:", error);
        }
    }
}

// Set up message listener
window.addEventListener("message", (event) => {
    if (event.data.type === "from_python") {
        handlePythonMessage(event.data.data);
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
    st.title("CSV to IndexedDB (WASM) Uploader")
    
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
            csv_data = df.to_json(orient="records")
            
            # Send data to JS for IndexedDB storage
            js_code = f"""
            <script>
                window.postMessage({{
                    type: "from_python",
                    data: {{
                        action: "store_csv",
                        csv_data: {csv_data},
                        filename: "{uploaded_file.name}"
                    }}
                }}, "*");
            </script>
            """
            st.components.v1.html(js_code, height=0)
            st.success("CSV data sent to IndexedDB!")
            
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
                csv_data = df.to_json(orient="records")
                
                # Send data to JS for IndexedDB storage
                js_code = f"""
                <script>
                    window.postMessage({{
                        type: "from_python",
                        data: {{
                            action: "store_csv",
                            csv_data: {csv_data},
                            filename: "{filename}"
                        }}
                    }}, "*");
                </script>
                """
                st.components.v1.html(js_code, height=0)
                st.success("CSV data sent to IndexedDB!")
                
            except Exception as e:
                st.error(f"Error processing CSV content: {e}")
    
    # Instructions section
    st.header("Instructions")
    st.markdown("""
    1. **Option 1**: Upload a CSV file directly using the file uploader
    2. **Option 2**: Provide a GitHub raw CSV URL to load the file
    3. The data will be stored in your browser's IndexedDB
    4. You can access this data later from your web application
    """)

if __name__ == "__main__":
    main()
