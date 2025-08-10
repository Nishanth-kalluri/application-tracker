import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime, timedelta
import os

# ============================================================================
# CONFIGURATION AND SETUP
# ============================================================================

# Page configuration
st.set_page_config(
    page_title="Application Tracker",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for beautiful minimal design - Theme Compatible
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Main container styling */
    .main {
        padding: 0;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* Custom button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border: none;
        padding: 0.5rem 1.5rem;
        border-radius: 12px;
        font-weight: 500;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.25);
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.35);
    }
    
    /* Delete button styling */
    div[data-testid="column"]:last-child .stButton > button {
        background: #ff6b6b;
        padding: 0.4rem 1rem;
        font-size: 0.875rem;
    }
    
    div[data-testid="column"]:last-child .stButton > button:hover {
        background: #ff5252;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        border-bottom: 3px solid #667eea;
        font-weight: 600;
    }
    
    /* Headers styling */
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 2rem;
    }
    
    /* Animation for smooth transitions */
    .stButton > button, .stTabs [data-baseweb="tab"] {
        transition: all 0.2s ease;
    }
</style>
""", unsafe_allow_html=True)

# Database file path
DB_FILE = "application_tracker.db"

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def init_database():
    """Initialize the SQLite database with required tables."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Users table for authentication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Applications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            company_name TEXT,
            role TEXT,
            url TEXT,
            date_applied DATE NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users (email)
        )
    ''')
    
    # Networking attempts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS networking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            company_name TEXT,
            linkedin_url TEXT,
            date_sent DATE NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users (email)
        )
    ''')
    
    # General notes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users (email)
        )
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(email, password):
    """Verify user credentials."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    password_hash = hash_password(password)
    cursor.execute(
        "SELECT email FROM users WHERE email = ? AND password_hash = ?",
        (email, password_hash)
    )
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def create_user(email, password):
    """Create a new user account."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    password_hash = hash_password(password)
    try:
        cursor.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

# ============================================================================
# AUTHENTICATION FUNCTIONS
# ============================================================================

def load_users_from_secrets():
    """Load users from Streamlit secrets if available."""
    if hasattr(st, 'secrets') and 'users' in st.secrets:
        for email, password in st.secrets.users.items():
            # Try to create user, ignore if already exists
            create_user(email, password)

def check_session_validity():
    """Check if the current session is still valid (24 hours)."""
    if 'login_time' in st.session_state:
        login_time = st.session_state.login_time
        if datetime.now() - login_time > timedelta(hours=24):
            # Session expired
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            return False
    return 'authenticated' in st.session_state and st.session_state.authenticated

def login_page():
    """Display the login page."""
    # Center the login form
    st.markdown("<div style='height: 10vh;'></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        st.markdown("# ✨")
        st.markdown("## Welcome Back")
        st.markdown("Track your journey to success")
        st.markdown("---")
        
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("✉️ Email", placeholder="your@email.com")
            password = st.text_input("🔐 Password", type="password", placeholder="Enter your password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            col_login, col_register = st.columns(2)
            
            with col_login:
                login_submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")
            
            with col_register:
                register_submitted = st.form_submit_button("Create Account", use_container_width=True)
            
            if login_submitted:
                if verify_user(email, password):
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.login_time = datetime.now()
                    st.success("✅ Welcome back! Redirecting...")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials. Please try again.")
            
            if register_submitted:
                if email and password:
                    if create_user(email, password):
                        st.success("✅ Account created successfully! Please sign in.")
                    else:
                        st.error("⚠️ This email is already registered.")
                else:
                    st.error("⚠️ Please provide both email and password.")

# ============================================================================
# DATA MANAGEMENT FUNCTIONS
# ============================================================================

def add_application(user_email, company_name, role, url, date_applied, notes):
    """Add a new job application."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO applications (user_email, company_name, role, url, date_applied, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_email, company_name, role, url, date_applied, notes))
    
    conn.commit()
    conn.close()

def get_applications(user_email):
    """Get all applications for a user."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, company_name, role, url, date_applied, notes, created_at
        FROM applications 
        WHERE user_email = ?
        ORDER BY date_applied DESC
    ''', (user_email,))
    
    results = cursor.fetchall()
    conn.close()
    
    if results:
        df = pd.DataFrame(results, columns=['ID', 'Company', 'Role', 'URL', 'Date Applied', 'Notes', 'Created'])
        return df
    return pd.DataFrame()

def delete_application(app_id, user_email):
    """Delete an application."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "DELETE FROM applications WHERE id = ? AND user_email = ?",
        (app_id, user_email)
    )
    
    conn.commit()
    conn.close()

def add_networking(user_email, company_name, linkedin_url, date_sent, notes):
    """Add a new networking attempt."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO networking (user_email, company_name, linkedin_url, date_sent, notes)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_email, company_name, linkedin_url, date_sent, notes))
    
    conn.commit()
    conn.close()

def get_networking(user_email):
    """Get all networking attempts for a user."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, company_name, linkedin_url, date_sent, notes, created_at
        FROM networking 
        WHERE user_email = ?
        ORDER BY date_sent DESC
    ''', (user_email,))
    
    results = cursor.fetchall()
    conn.close()
    
    if results:
        df = pd.DataFrame(results, columns=['ID', 'Company', 'LinkedIn URL', 'Date Sent', 'Notes', 'Created'])
        return df
    return pd.DataFrame()

def delete_networking(net_id, user_email):
    """Delete a networking attempt."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "DELETE FROM networking WHERE id = ? AND user_email = ?",
        (net_id, user_email)
    )
    
    conn.commit()
    conn.close()

def add_note(user_email, title, body):
    """Add a new general note."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO notes (user_email, title, body)
        VALUES (?, ?, ?)
    ''', (user_email, title, body))
    
    conn.commit()
    conn.close()

def get_notes(user_email):
    """Get all notes for a user."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, title, body, created_at
        FROM notes 
        WHERE user_email = ?
        ORDER BY created_at DESC
    ''', (user_email,))
    
    results = cursor.fetchall()
    conn.close()
    
    if results:
        df = pd.DataFrame(results, columns=['ID', 'Title', 'Body', 'Created'])
        return df
    return pd.DataFrame()

def delete_note(note_id, user_email):
    """Delete a note."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "DELETE FROM notes WHERE id = ? AND user_email = ?",
        (note_id, user_email)
    )
    
    conn.commit()
    conn.close()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_date(date_str):
    """Format date string for better display."""
    try:
        date_obj = datetime.strptime(str(date_str).split()[0], '%Y-%m-%d')
        return date_obj.strftime('%b %d, %Y')
    except:
        return date_str

# ============================================================================
# UI COMPONENTS
# ============================================================================

def applications_tab():
    """Applications management tab."""
    # Header with stats
    applications_df = get_applications(st.session_state.user_email)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Applications", len(applications_df))
    with col2:
        if not applications_df.empty:
            latest = applications_df.iloc[0]['Date Applied']
            st.metric("Latest Application", format_date(latest))
        else:
            st.metric("Latest Application", "None")
    with col3:
        if not applications_df.empty:
            companies = applications_df['Company'].nunique()
            st.metric("Companies", companies)
        else:
            st.metric("Companies", "0")
    with col4:
        if not applications_df.empty:
            this_week = len(applications_df[pd.to_datetime(applications_df['Date Applied']) >= datetime.now() - timedelta(days=7)])
            st.metric("This Week", this_week)
        else:
            st.metric("This Week", "0")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Add new application form
    with st.expander("✨ Add New Application", expanded=False):
        with st.form("add_application_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                company_name = st.text_input("🏢 Company Name", placeholder="e.g., Google")
                role = st.text_input("💼 Role/Position", placeholder="e.g., Software Engineer")
            
            with col2:
                url = st.text_input("🔗 Job URL", placeholder="https://...")
                date_applied = st.date_input("📅 Date Applied", value=datetime.now().date())
            
            notes = st.text_area("📝 Notes", placeholder="Add any relevant notes about this application...")
            
            submitted = st.form_submit_button("Add Application", type="primary", use_container_width=True)
            
            if submitted:
                if company_name and role:
                    add_application(
                        st.session_state.user_email,
                        company_name,
                        role,
                        url,
                        date_applied.strftime('%Y-%m-%d'),
                        notes
                    )
                    st.success("✅ Application added successfully!")
                    st.rerun()
                else:
                    st.error("⚠️ Please provide at least Company Name and Role")
    
    # Display existing applications
    st.markdown("### 📋 Your Applications")
    
    if not applications_df.empty:
        for idx, row in applications_df.iterrows():
            with st.container():
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    st.markdown(f"**{row['Company']}** • {row['Role']}")
                    st.caption(f"📅 Applied: {format_date(row['Date Applied'])}")
                    
                    if row['URL']:
                        st.markdown(f"🔗 [View Job Posting]({row['URL']})")
                    
                    if row['Notes']:
                        st.info(f"💭 {row['Notes']}")
                
                with col2:
                    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
                    if st.button("Delete", key=f"del_app_{row['ID']}", help="Remove this application"):
                        delete_application(row['ID'], st.session_state.user_email)
                        st.rerun()
                        
            st.divider()
    else:
        st.info("No applications yet. Start tracking your job applications by adding your first one above!")

def networking_tab():
    """Networking attempts management tab."""
    # Header with stats
    networking_df = get_networking(st.session_state.user_email)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Connections", len(networking_df))
    with col2:
        if not networking_df.empty:
            latest = networking_df.iloc[0]['Date Sent']
            st.metric("Latest Outreach", format_date(latest))
        else:
            st.metric("Latest Outreach", "None")
    with col3:
        if not networking_df.empty:
            companies = networking_df['Company'].nunique()
            st.metric("Companies", companies)
        else:
            st.metric("Companies", "0")
    with col4:
        if not networking_df.empty:
            this_week = len(networking_df[pd.to_datetime(networking_df['Date Sent']) >= datetime.now() - timedelta(days=7)])
            st.metric("This Week", this_week)
        else:
            st.metric("This Week", "0")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Add new networking attempt form
    with st.expander("✨ Add New Connection", expanded=False):
        with st.form("add_networking_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                company_name = st.text_input("🏢 Company Name", placeholder="e.g., Microsoft")
                linkedin_url = st.text_input("💼 LinkedIn Profile URL", placeholder="https://linkedin.com/in/...")
            
            with col2:
                date_sent = st.date_input("📅 Date Sent", value=datetime.now().date())
            
            notes = st.text_area("📝 Notes", placeholder="Add notes about your connection attempt...")
            
            submitted = st.form_submit_button("Add Connection", type="primary", use_container_width=True)
            
            if submitted:
                if company_name:
                    add_networking(
                        st.session_state.user_email,
                        company_name,
                        linkedin_url,
                        date_sent.strftime('%Y-%m-%d'),
                        notes
                    )
                    st.success("✅ Connection added successfully!")
                    st.rerun()
                else:
                    st.error("⚠️ Please provide at least the Company Name")
    
    # Display existing networking attempts
    st.markdown("### 🤝 Your Connections")
    
    if not networking_df.empty:
        for idx, row in networking_df.iterrows():
            with st.container():
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    st.markdown(f"**{row['Company']}**")
                    st.caption(f"📅 Reached out: {format_date(row['Date Sent'])}")
                    
                    if row['LinkedIn URL']:
                        st.markdown(f"💼 [View LinkedIn Profile]({row['LinkedIn URL']})")
                    
                    if row['Notes']:
                        st.info(f"💭 {row['Notes']}")
                
                with col2:
                    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
                    if st.button("Delete", key=f"del_net_{row['ID']}", help="Remove this connection"):
                        delete_networking(row['ID'], st.session_state.user_email)
                        st.rerun()
                        
            st.divider()
    else:
        st.info("No connections yet. Start building your network by adding your first connection above!")

def notes_tab():
    """General notes management tab."""
    # Header with stats
    notes_df = get_notes(st.session_state.user_email)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Notes", len(notes_df))
    with col2:
        if not notes_df.empty:
            latest = notes_df.iloc[0]['Created']
            st.metric("Latest Note", format_date(str(latest).split()[0]))
        else:
            st.metric("Latest Note", "None")
    with col3:
        if not notes_df.empty:
            avg_length = notes_df['Body'].str.len().mean()
            st.metric("Avg. Length", f"{int(avg_length)} chars")
        else:
            st.metric("Avg. Length", "0 chars")
    with col4:
        if not notes_df.empty:
            this_week = len(notes_df[pd.to_datetime(notes_df['Created']) >= datetime.now() - timedelta(days=7)])
            st.metric("This Week", this_week)
        else:
            st.metric("This Week", "0")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Add new note form
    with st.expander("✨ Add New Note", expanded=False):
        with st.form("add_note_form", clear_on_submit=True):
            title = st.text_input("📌 Note Title", placeholder="Enter a title for your note...")
            body = st.text_area("📝 Note Content", placeholder="Write your thoughts, ideas, or reminders...", height=150)
            
            submitted = st.form_submit_button("Add Note", type="primary", use_container_width=True)
            
            if submitted:
                if title:
                    add_note(st.session_state.user_email, title, body)
                    st.success("✅ Note added successfully!")
                    st.rerun()
                else:
                    st.error("⚠️ Please provide a title for the note")
    
    # Display existing notes
    st.markdown("### 📝 Your Notes")
    
    if not notes_df.empty:
        for idx, row in notes_df.iterrows():
            with st.container():
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    st.markdown(f"**{row['Title']}**")
                    st.caption(f"📅 Created: {format_date(str(row['Created']).split()[0])}")
                    
                    if row['Body']:
                        with st.expander("View Note", expanded=False):
                            st.write(row['Body'])
                
                with col2:
                    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
                    if st.button("Delete", key=f"del_note_{row['ID']}", help="Remove this note"):
                        delete_note(row['ID'], st.session_state.user_email)
                        st.rerun()
                        
            st.divider()
    else:
        st.info("No notes yet. Start documenting your journey by adding your first note above!")

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application function."""
    # Initialize database
    init_database()
    
    # Load users from secrets if available
    load_users_from_secrets()
    
    # Check authentication
    if not check_session_validity():
        login_page()
        return
    
    # Main application UI
    st.title("✨ Application Tracker")
    st.caption("Your journey to success, beautifully organized")
    
    # Sidebar with user info and logout
    with st.sidebar:
        st.markdown("### 👤 User Profile")
        st.write(f"**Email:** {st.session_state.user_email}")
        
        hours_remaining = 24 - int((datetime.now() - st.session_state.login_time).total_seconds() / 3600)
        
        st.markdown("---")
        
        st.metric("⏱️ Session Time", f"{hours_remaining} hours remaining")
        
        st.markdown("---")
        
        if st.button("🚪 Sign Out", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📋 Applications", "🤝 Networking", "📝 Notes"])
    
    with tab1:
        applications_tab()
    
    with tab2:
        networking_tab()
    
    with tab3:
        notes_tab()

if __name__ == "__main__":
    main()