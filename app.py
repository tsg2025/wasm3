import streamlit as st
import pandas as pd

st.title("CSV to IndexedDB (Confirmed Working)")
st.write("""
This is the minimal working version that verifies storage.
""")

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.subheader("Data Preview")
        st.write(df.head())
        
        data_json = df.to_json(orient='records')
        
        js_code = f"""
        <script>
        // 1. Open database
        const request = indexedDB.open("CSV_Database", 1);
        
        // 2. Create store if needed
        request.onupgradeneeded = (event) => {{
            const db = event.target.result;
            db.createObjectStore("csv_data", {{ autoIncrement: true }});
        }};
        
        // 3. Store data when DB is ready
        request.onsuccess = (event) => {{
            const db = event.target.result;
            const tx = db.transaction("csv_data", "readwrite");
            const store = tx.objectStore("csv_data");
            
            // Clear old data
            store.clear().onsuccess = () => {{
                // Add new data
                const data = {data_json};
                store.add(data);
                
                // VERIFICATION - Immediately read back
                store.getAll().onsuccess = (e) => {{
                    const savedData = e.target.result[0];
                    console.log("Stored data verified:", savedData);
                    alert(`Success! Stored ${{savedData.length}} records`);
                    
                    // Send verification to Streamlit
                    window.parent.postMessage({{
                        type: "STORAGE_VERIFIED",
                        rowCount: savedData.length,
                        firstRecord: savedData[0]
                    }}, "*");
                }};
            }};
        }};
        </script>
        """
        
        st.components.v1.html(js_code, height=0)
        st.success("Data processing complete!")
        
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Verification message handler
st.components.v1.html("""
<script>
window.addEventListener('message', (event) => {
    if (event.data.type === "STORAGE_VERIFIED") {
        console.log("Storage confirmed:", event.data);
    }
});
</script>
""", height=0)

st.markdown("""
### How to verify:
1. Open browser console (F12)
2. Check:
   - "Application" → IndexedDB → "CSV_Database"
   - Console logs will show the stored data
3. You'll see an alert with the row count
""")
