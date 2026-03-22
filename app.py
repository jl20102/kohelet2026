import streamlit as st
import requests
import urllib.parse

st.set_page_config(page_title="Sefaria Siddur Browser", layout="wide")

# Custom CSS for Hebrew styling
st.markdown("""
    <style>
    .hebrew-text {
        direction: rtl;
        text-align: right;
        font-family: 'SBL Hebrew', 'Arial';
        font-size: 28px;
        line-height: 1.8;
        background-color: #f9f9f9;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #ddd;
    }
    </style>
    """, unsafe_allow_html=True)

BASE_URL = "https://www.sefaria.org/api"
INDEX_NAME = "Siddur_Ashkenaz"

@st.cache_data
def get_siddur_index():
    response = requests.get(f"{BASE_URL}/v2/index/{INDEX_NAME}")
    response.raise_for_status()
    return response.json()['schema']

def flatten_text(text_data):
    if isinstance(text_data, list):
        return "\n\n".join([flatten_text(item) for item in text_data])
    return str(text_data)

# --- APP LOGIC ---
st.sidebar.title("Siddur Navigator")

try:
    schema = get_siddur_index()
    
    # Level 1: Main sections (e.g., Weekday, Shabbat)
    l1_nodes = schema.get('nodes', [])
    l1_titles = [n.get('enTitle', n.get('key', 'Unknown')) for n in l1_nodes]
    choice1 = st.sidebar.selectbox("Section", l1_titles)
    
    # Find selected node
    node1 = next(n for n in l1_nodes if n.get('enTitle', n.get('key')) == choice1)
    
    # Level 2: Sub-sections (e.g., Shacharit, Minchah)
    final_ref_parts = [INDEX_NAME, choice1.replace(" ", "_")]
    
    if 'nodes' in node1:
        l2_nodes = node1['nodes']
        l2_titles = [n.get('enTitle', n.get('key', 'Unknown')) for n in l2_nodes]
        choice2 = st.sidebar.selectbox("Service", l2_titles)
        node2 = next(n for n in l2_nodes if n.get('enTitle', n.get('key')) == choice2)
        final_ref_parts.append(choice2.replace(" ", "_"))
        
        # Level 3: Individual Prayers
        if 'nodes' in node2:
            l3_nodes = node2['nodes']
            l3_titles = [n.get('enTitle', n.get('key', 'Unknown')) for n in l3_nodes]
            choice3 = st.sidebar.selectbox("Prayer", l3_titles)
            final_ref_parts.append(choice3.replace(" ", "_"))
            display_title = choice3
        else:
            display_title = choice2
    else:
        display_title = choice1

    final_ref = ",_".join(final_ref_parts)

    # --- DISPLAY ---
    st.title(display_title.replace("_", " "))
    st.caption(f"Ref: {final_ref.replace(',_', ' > ')}")

    if st.button("Display Prayer"):
        with st.spinner("Loading Hebrew text..."):
            # Encode each part specifically to avoid 400 errors
            encoded_parts = [urllib.parse.quote(p) for p in final_ref.split(",_")]
            safe_ref = ",_".join(encoded_parts)
            
            url = f"{BASE_URL}/v3/texts/{safe_ref}?context=0"
            
            res = requests.get(url)
            if res.status_code == 200:
                data = res.json()
                hebrew_text = ""
                for v in data.get('versions', []):
                    if v.get('language') == 'he':
                        hebrew_text = flatten_text(v.get('text', []))
                        break
                
                if hebrew_text:
                    st.markdown(f'<div class="hebrew-text">{hebrew_text}</div>', unsafe_allow_html=True)
                else:
                    st.error("No Hebrew version found for this selection.")
            else:
                st.error(f"Sefaria API Error {res.status_code}. The Ref might be too broad.")
                st.info("Try selecting a more specific prayer from the third dropdown.")

except Exception as e:
    st.sidebar.error(f"Navigation Error: {e}")
    st.write("Please select a specific prayer from the sidebar to begin.")