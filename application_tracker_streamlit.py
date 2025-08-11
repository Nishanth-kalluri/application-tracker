import streamlit as st
import hashlib
import pandas as pd
from datetime import datetime, timedelta
import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import DuplicateKeyError

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
    
    /* Search button styling */
    .search-button .stButton > button {
        background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%);
        color: white !important;
    }
    
    .search-button .stButton > button:hover {
        background: linear-gradient(135deg, #44a08d 0%, #4ecdc4 100%);
    }
    
    /* Clear button styling */
    .clear-button .stButton > button {
        background: #f8f9fa;
        color: #6c757d !important;
        border: 1px solid #dee2e6;
    }
    
    .clear-button .stButton > button:hover {
        background: #e9ecef;
        color: #495057 !important;
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
    
    /* Search results styling */
    .search-results {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1rem;
        border-radius: 12px;
        margin: 1rem 0;
        border-left: 4px solid #4ecdc4;
    }
    
    /* Animation for smooth transitions */
    .stButton > button, .stTabs [data-baseweb="tab"] {
        transition: all 0.2s ease;
    }
</style>
""", unsafe_allow_html=True)

# MongoDB configuration
MONGO_URI = "mongodb+srv://nishanth_atlas:<db_password>@stocktracker.bzekz.mongodb.net/?retryWrites=true&w=majority&appName=StockTracker"

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

@st.cache_resource
def init_mongodb():
    """Initialize MongoDB connection."""
    try:
        # Get password from secrets or environment
        print("Connecting with MongoDB")
        print(f"st.secrets exists: {hasattr(st, 'secrets')}")
        if hasattr(st, 'secrets'):
            print(f"Available secret keys: {list(st.secrets.keys())}")
            print(f"mongo_password in secrets: {'mongo_password' in st.secrets}")
            
            # Try to access each key individually
            try:
                users = st.secrets.users
                print(f"users section: {dict(users)}")
            except Exception as e:
                print(f"Error accessing users: {e}")
            
            try:
                mongo_pass = st.secrets.mongo_password
                print(f"mongo_password value: {mongo_pass}")
            except Exception as e:
                print(f"Error accessing mongo_password: {e}")
                
        if hasattr(st, 'secrets') and 'mongo_password' in st.secrets:
            print("fetching password")
            password = st.secrets.mongo_password
            print("password:{password}")
        else:
            password = os.getenv('MONGO_PASSWORD', '<db_password>')
        
        # Replace placeholder with actual password
        uri = MONGO_URI.replace('<db_password>', password)
        
        # Create client and connect
        client = MongoClient(uri, server_api=ServerApi('1'))
        
        # Test connection
        client.admin.command('ping')
        print("Successfully connected to MongoDB!")
        
        # Get database
        db = client.application_tracker
        
        # Create indexes for better performance
        db.users.create_index("email", unique=True)
        db.applications.create_index([("user_email", 1), ("date_applied", -1)])
        db.networking.create_index([("user_email", 1), ("date_sent", -1)])
        db.notes.create_index([("user_email", 1), ("created_at", -1)])
        db.todos.create_index([("user_email", 1), ("created_at", -1)])
        
        return db
        
    except Exception as e:
        st.error(f"Failed to connect to MongoDB: {e}")
        return None

def get_database():
    """Get MongoDB database instance."""
    return init_mongodb()

def hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(email, password):
    """Verify user credentials."""
    db = get_database()
    if db is None:
        return False
        
    password_hash = hash_password(password)
    user = db.users.find_one({
        "email": email,
        "password_hash": password_hash
    })
    
    return user is not None

def create_user(email, password):
    """Create a new user account."""
    db = get_database()
    if db is None:
        return False
        
    password_hash = hash_password(password)
    try:
        db.users.insert_one({
            "email": email,
            "password_hash": password_hash,
            "created_at": datetime.now()
        })
        return True
    except DuplicateKeyError:
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
    db = get_database()
    if db is None:
        return False
        
    # Convert date string to datetime object
    if isinstance(date_applied, str):
        date_applied = datetime.strptime(date_applied, '%Y-%m-%d')
    elif hasattr(date_applied, 'date'):  # It's a datetime.date object
        # Convert date to datetime (start of day)
        date_applied = datetime.combine(date_applied, datetime.min.time())
    
    db.applications.insert_one({
        "user_email": user_email,
        "company_name": company_name,
        "role": role,
        "url": url,
        "date_applied": date_applied,
        "notes": notes,
        "created_at": datetime.now()
    })
    return True

def get_applications(user_email, limit=None):
    """Get all applications for a user with optional limit."""
    db = get_database()
    if db is None:
        return pd.DataFrame()
    
    query = db.applications.find(
        {"user_email": user_email}
    ).sort("date_applied", -1)
    
    if limit:
        query = query.limit(limit)
        
    applications = list(query)
    
    if applications:
        # Convert MongoDB documents to DataFrame
        for app in applications:
            app['ID'] = str(app['_id'])  # Convert ObjectId to string
            app['Company'] = app['company_name']
            app['Role'] = app['role']
            app['URL'] = app['url']
            app['Date Applied'] = app['date_applied']
            app['Notes'] = app['notes']
            app['Created'] = app['created_at']
        
        df = pd.DataFrame(applications)
        return df[['ID', 'Company', 'Role', 'URL', 'Date Applied', 'Notes', 'Created']]
    
    return pd.DataFrame()

def search_applications(user_email, company_filter=None, date_from=None, date_to=None, role_filter=None, limit=50):
    """Search applications with various filters."""
    db = get_database()
    if db is None:
        return pd.DataFrame()
    
    # Build query
    query = {"user_email": user_email}
    
    # Add company filter (case-insensitive partial match)
    if company_filter:
        query["company_name"] = {"$regex": company_filter, "$options": "i"}
    
    # Add role filter (case-insensitive partial match)
    if role_filter:
        query["role"] = {"$regex": role_filter, "$options": "i"}
    
    # Add date range filter
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = datetime.combine(date_from, datetime.min.time())
        if date_to:
            date_query["$lte"] = datetime.combine(date_to, datetime.max.time())
        query["date_applied"] = date_query
    
    # Execute query with limit
    applications = list(db.applications.find(query).sort("date_applied", -1).limit(limit))
    
    if applications:
        # Convert MongoDB documents to DataFrame
        for app in applications:
            app['ID'] = str(app['_id'])  # Convert ObjectId to string
            app['Company'] = app['company_name']
            app['Role'] = app['role']
            app['URL'] = app['url']
            app['Date Applied'] = app['date_applied']
            app['Notes'] = app['notes']
            app['Created'] = app['created_at']
        
        df = pd.DataFrame(applications)
        return df[['ID', 'Company', 'Role', 'URL', 'Date Applied', 'Notes', 'Created']]
    
    return pd.DataFrame()

def delete_application(app_id, user_email):
    """Delete an application."""
    db = get_database()
    if db is None:
        return False
        
    from bson import ObjectId
    
    try:
        db.applications.delete_one({
            "_id": ObjectId(app_id),
            "user_email": user_email
        })
        return True
    except:
        return False

def add_networking(user_email, company_name, linkedin_url, date_sent, notes):
    """Add a new networking attempt."""
    db = get_database()
    if db is None:
        return False
        
    # Convert date string to datetime object
    if isinstance(date_sent, str):
        date_sent = datetime.strptime(date_sent, '%Y-%m-%d')
    elif hasattr(date_sent, 'date'):  # It's a datetime.date object
        # Convert date to datetime (start of day)
        date_sent = datetime.combine(date_sent, datetime.min.time())
    
    db.networking.insert_one({
        "user_email": user_email,
        "company_name": company_name,
        "linkedin_url": linkedin_url,
        "date_sent": date_sent,
        "notes": notes,
        "created_at": datetime.now()
    })
    return True

def get_networking(user_email):
    """Get all networking attempts for a user."""
    db = get_database()
    if db is None:
        return pd.DataFrame()
        
    networking = list(db.networking.find(
        {"user_email": user_email}
    ).sort("date_sent", -1))
    
    if networking:
        # Convert MongoDB documents to DataFrame
        for net in networking:
            net['ID'] = str(net['_id'])  # Convert ObjectId to string
            net['Company'] = net['company_name']
            net['LinkedIn URL'] = net['linkedin_url']
            net['Date Sent'] = net['date_sent']
            net['Notes'] = net['notes']
            net['Created'] = net['created_at']
        
        df = pd.DataFrame(networking)
        return df[['ID', 'Company', 'LinkedIn URL', 'Date Sent', 'Notes', 'Created']]
    
    return pd.DataFrame()

def delete_networking(net_id, user_email):
    """Delete a networking attempt."""
    db = get_database()
    if db is None:
        return False
        
    from bson import ObjectId
    
    try:
        db.networking.delete_one({
            "_id": ObjectId(net_id),
            "user_email": user_email
        })
        return True
    except:
        return False

def add_note(user_email, title, body):
    """Add a new general note."""
    db = get_database()
    if db is None:
        return False
        
    db.notes.insert_one({
        "user_email": user_email,
        "title": title,
        "body": body,
        "created_at": datetime.now()
    })
    return True

def get_notes(user_email):
    """Get all notes for a user."""
    db = get_database()
    if db is None:
        return pd.DataFrame()
        
    notes = list(db.notes.find(
        {"user_email": user_email}
    ).sort("created_at", -1))
    
    if notes:
        # Convert MongoDB documents to DataFrame
        for note in notes:
            note['ID'] = str(note['_id'])  # Convert ObjectId to string
            note['Title'] = note['title']
            note['Body'] = note['body']
            note['Created'] = note['created_at']
        
        df = pd.DataFrame(notes)
        return df[['ID', 'Title', 'Body', 'Created']]
    
    return pd.DataFrame()

def delete_note(note_id, user_email):
    """Delete a note."""
    db = get_database()
    if db is None:
        return False
        
    from bson import ObjectId
    
    try:
        db.notes.delete_one({
            "_id": ObjectId(note_id),
            "user_email": user_email
        })
        return True
    except:
        return False

# ============================================================================
# TODO LIST FUNCTIONS
# ============================================================================

def add_todo(user_email, task, priority="Medium", due_date=None):
    """Add a new todo item."""
    db = get_database()
    if db is None:
        return False
    
    # Convert date if provided
    if due_date and hasattr(due_date, 'date'):
        due_date = datetime.combine(due_date, datetime.min.time())
    
    db.todos.insert_one({
        "user_email": user_email,
        "task": task,
        "priority": priority,
        "due_date": due_date,
        "completed": False,
        "created_at": datetime.now()
    })
    return True

def get_todos(user_email):
    """Get all todos for a user."""
    db = get_database()
    if db is None:
        return pd.DataFrame()
    
    todos = list(db.todos.find(
        {"user_email": user_email}
    ).sort([("completed", 1), ("priority", -1), ("created_at", -1)]))
    
    if todos:
        # Convert MongoDB documents to DataFrame
        for todo in todos:
            todo['ID'] = str(todo['_id'])
            todo['Task'] = todo['task']
            todo['Priority'] = todo['priority']
            todo['Due Date'] = todo.get('due_date', None)
            todo['Completed'] = todo['completed']
            todo['Created'] = todo['created_at']
        
        df = pd.DataFrame(todos)
        return df[['ID', 'Task', 'Priority', 'Due Date', 'Completed', 'Created']]
    
    return pd.DataFrame()

def toggle_todo_status(todo_id, user_email):
    """Toggle the completion status of a todo."""
    db = get_database()
    if db is None:
        return False
    
    from bson import ObjectId
    
    try:
        # Get current status
        todo = db.todos.find_one({
            "_id": ObjectId(todo_id),
            "user_email": user_email
        })
        
        if todo:
            # Toggle the status
            db.todos.update_one(
                {"_id": ObjectId(todo_id)},
                {"$set": {"completed": not todo['completed']}}
            )
            return True
        return False
    except:
        return False

def delete_todo(todo_id, user_email):
    """Delete a todo item."""
    db = get_database()
    if db is None:
        return False
    
    from bson import ObjectId
    
    try:
        db.todos.delete_one({
            "_id": ObjectId(todo_id),
            "user_email": user_email
        })
        return True
    except:
        return False

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_date(date_str):
    """Format date string for better display."""
    try:
        if isinstance(date_str, datetime):
            return date_str.strftime('%b %d, %Y')
        elif hasattr(date_str, 'date'):  # It's a datetime.date object
            return date_str.strftime('%b %d, %Y')
        elif isinstance(date_str, str):
            # Try to parse various date formats
            date_str_clean = str(date_str).split()[0]  # Remove time part if present
            try:
                date_obj = datetime.strptime(date_str_clean, '%Y-%m-%d')
                return date_obj.strftime('%b %d, %Y')
            except ValueError:
                # Try other common formats
                try:
                    date_obj = datetime.fromisoformat(date_str_clean)
                    return date_obj.strftime('%b %d, %Y')
                except:
                    return str(date_str)
        else:
            return str(date_str)
    except:
        return str(date_str)

# ============================================================================
# UI COMPONENTS
# ============================================================================

def display_applications_list(applications_df, search_active=False):
    """Display applications list with optional search context."""
    if not applications_df.empty:
        if search_active:
            st.markdown('<div class="search-results">', unsafe_allow_html=True)
            st.markdown(f"### 🔍 Search Results ({len(applications_df)} found)")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"### 📋 Your Latest Applications (Showing {len(applications_df)} of latest 50)")
        
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
                        if delete_application(row['ID'], st.session_state.user_email):
                            st.rerun()
                        else:
                            st.error("Failed to delete application")
                        
            st.divider()
    else:
        if search_active:
            st.info("🔍 No applications found matching your search criteria. Try adjusting your filters.")
        else:
            st.info("No applications yet. Start tracking your job applications by adding your first one above!")

def applications_tab():
    """Applications management tab with search functionality."""
    # Initialize search state
    if 'search_active' not in st.session_state:
        st.session_state.search_active = False
    if 'search_results' not in st.session_state:
        st.session_state.search_results = pd.DataFrame()
    
    # Get applications for stats (full count)
    all_applications_df = get_applications(st.session_state.user_email)
    
    # Get limited applications for display
    display_applications_df = get_applications(st.session_state.user_email, limit=50)
    
    # Determine which dataframe to use for display
    if st.session_state.search_active and not st.session_state.search_results.empty:
        display_df = st.session_state.search_results
        stats_df = st.session_state.search_results  # Use search results for stats
    else:
        display_df = display_applications_df
        stats_df = all_applications_df  # Use full data for stats
    
    # Header with stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.session_state.search_active:
            st.metric("Search Results", len(stats_df))
        else:
            st.metric("Total Applications", len(stats_df))
    with col2:
        if not stats_df.empty:
            latest = stats_df.iloc[0]['Date Applied']
            st.metric("Latest Application", format_date(latest))
        else:
            st.metric("Latest Application", "None")
    with col3:
        if not stats_df.empty:
            companies = stats_df['Company'].nunique()
            st.metric("Companies", companies)
        else:
            st.metric("Companies", "0")
    with col4:
        if not stats_df.empty:
            this_week = len(stats_df[pd.to_datetime(stats_df['Date Applied']) >= datetime.now() - timedelta(days=7)])
            st.metric("This Week", this_week)
        else:
            st.metric("This Week", "0")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Add new application form - ALWAYS VISIBLE
    st.markdown("### ✨ Add New Application")
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
                if add_application(
                    st.session_state.user_email,
                    company_name,
                    role,
                    url,
                    date_applied.strftime('%Y-%m-%d'),
                    notes
                ):
                    st.success("✅ Application added successfully!")
                    # Reset search if active to show updated results
                    if st.session_state.search_active:
                        st.session_state.search_active = False
                        st.session_state.search_results = pd.DataFrame()
                    st.rerun()
                else:
                    st.error("❌ Failed to add application. Please try again.")
            else:
                st.error("⚠️ Please provide at least Company Name and Role")
    
    st.markdown("---")
    
    # Search Section
    with st.expander("🔍 Search Applications", expanded=st.session_state.search_active):
        with st.form("search_applications_form"):
            st.markdown("#### Filter Your Applications")
            
            col1, col2 = st.columns(2)
            
            with col1:
                search_company = st.text_input("🏢 Company Name", placeholder="e.g., Google, Microsoft...")
                search_role = st.text_input("💼 Role/Position", placeholder="e.g., Software Engineer...")
            
            with col2:
                search_date_from = st.date_input("📅 From Date", value=None, help="Leave empty for no start date limit")
                search_date_to = st.date_input("📅 To Date", value=None, help="Leave empty for no end date limit")
            
            col_search, col_clear = st.columns([2, 1])
            
            with col_search:
                search_submitted = st.form_submit_button("🔍 Search Applications", type="primary", use_container_width=True)
            
            with col_clear:
                clear_submitted = st.form_submit_button("🗑️ Clear Filters", use_container_width=True)
            
            if search_submitted:
                # Perform search with limit
                search_results = search_applications(
                    st.session_state.user_email,
                    company_filter=search_company if search_company else None,
                    date_from=search_date_from,
                    date_to=search_date_to,
                    role_filter=search_role if search_role else None,
                    limit=50
                )
                
                st.session_state.search_results = search_results
                st.session_state.search_active = True
                
                # Show search summary
                filters_applied = []
                if search_company:
                    filters_applied.append(f"Company: '{search_company}'")
                if search_role:
                    filters_applied.append(f"Role: '{search_role}'")
                if search_date_from:
                    filters_applied.append(f"From: {search_date_from}")
                if search_date_to:
                    filters_applied.append(f"To: {search_date_to}")
                
                if filters_applied:
                    st.success(f"✅ Search completed! Filters: {', '.join(filters_applied)}")
                else:
                    st.info("ℹ️ No filters applied - showing all applications")
                
                st.rerun()
            
            if clear_submitted:
                # Clear search
                st.session_state.search_active = False
                st.session_state.search_results = pd.DataFrame()
                st.success("✅ Filters cleared - showing all applications")
                st.rerun()
    
    # Show active search indicator
    if st.session_state.search_active:
        st.info("🔍 **Search Active** - Only showing filtered results. Use 'Clear Filters' to see all applications.")
    
    # Display applications
    display_applications_list(display_df, st.session_state.search_active)

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
    
    # Add new networking attempt form - ALWAYS VISIBLE
    st.markdown("### ✨ Add New Connection")
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
                if add_networking(
                    st.session_state.user_email,
                    company_name,
                    linkedin_url,
                    date_sent.strftime('%Y-%m-%d'),
                    notes
                ):
                    st.success("✅ Connection added successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to add connection. Please try again.")
            else:
                st.error("⚠️ Please provide at least the Company Name")
    
    st.markdown("---")
    
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
                        if delete_networking(row['ID'], st.session_state.user_email):
                            st.rerun()
                        else:
                            st.error("Failed to delete connection")
                        
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
    
    # Add new note form - ALWAYS VISIBLE
    st.markdown("### ✨ Add New Note")
    with st.form("add_note_form", clear_on_submit=True):
        title = st.text_input("📌 Note Title", placeholder="Enter a title for your note...")
        body = st.text_area("📝 Note Content", placeholder="Write your thoughts, ideas, or reminders...", height=150)
        
        submitted = st.form_submit_button("Add Note", type="primary", use_container_width=True)
        
        if submitted:
            if title:
                if add_note(st.session_state.user_email, title, body):
                    st.success("✅ Note added successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to add note. Please try again.")
            else:
                st.error("⚠️ Please provide a title for the note")
    
    st.markdown("---")
    
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
                        if delete_note(row['ID'], st.session_state.user_email):
                            st.rerun()
                        else:
                            st.error("Failed to delete note")
                        
            st.divider()
    else:
        st.info("No notes yet. Start documenting your journey by adding your first note above!")

def todo_tab():
    """TODO list management tab."""
    # Header with stats
    todos_df = get_todos(st.session_state.user_email)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tasks", len(todos_df))
    with col2:
        if not todos_df.empty:
            completed = len(todos_df[todos_df['Completed'] == True])
            st.metric("Completed", completed)
        else:
            st.metric("Completed", "0")
    with col3:
        if not todos_df.empty:
            pending = len(todos_df[todos_df['Completed'] == False])
            st.metric("Pending", pending)
        else:
            st.metric("Pending", "0")
    with col4:
        if not todos_df.empty:
            today_tasks = len(todos_df[
                (pd.to_datetime(todos_df['Due Date']) == datetime.now().date()) | 
                (pd.to_datetime(todos_df['Created']) >= datetime.now() - timedelta(days=1))
            ])
            st.metric("Today", today_tasks)
        else:
            st.metric("Today", "0")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Add new todo form - ALWAYS VISIBLE
    st.markdown("### ✨ Add New Task")
    with st.form("add_todo_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            task = st.text_input("📋 Task Description", placeholder="What needs to be done?")
        
        with col2:
            priority = st.selectbox("🎯 Priority", ["High", "Medium", "Low"], index=1)
        
        with col3:
            due_date = st.date_input("📅 Due Date", value=None, help="Optional due date")
        
        submitted = st.form_submit_button("Add Task", type="primary", use_container_width=True)
        
        if submitted:
            if task:
                if add_todo(st.session_state.user_email, task, priority, due_date):
                    st.success("✅ Task added successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to add task. Please try again.")
            else:
                st.error("⚠️ Please provide a task description")
    
    st.markdown("---")
    
    # Display todos
    st.markdown("### 📋 Your Tasks")
    
    if not todos_df.empty:
        # Separate completed and pending tasks
        pending_df = todos_df[todos_df['Completed'] == False]
        completed_df = todos_df[todos_df['Completed'] == True]
        
        # Show pending tasks first
        if not pending_df.empty:
            st.markdown("#### 🔄 Pending Tasks")
            for idx, row in pending_df.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([0.5, 4.5, 1])
                    
                    with col1:
                        if st.checkbox("", key=f"check_{row['ID']}", value=row['Completed']):
                            if toggle_todo_status(row['ID'], st.session_state.user_email):
                                st.rerun()
                    
                    with col2:
                        # Priority color coding
                        priority_color = {
                            "High": "🔴",
                            "Medium": "🟡", 
                            "Low": "🟢"
                        }
                        
                        st.markdown(f"{priority_color.get(row['Priority'], '⚪')} **{row['Task']}**")
                        
                        details = []
                        if row['Due Date']:
                            details.append(f"📅 Due: {format_date(row['Due Date'])}")
                        details.append(f"Created: {format_date(str(row['Created']).split()[0])}")
                        
                        st.caption(" • ".join(details))
                    
                    with col3:
                        if st.button("Delete", key=f"del_todo_{row['ID']}", help="Remove this task"):
                            if delete_todo(row['ID'], st.session_state.user_email):
                                st.rerun()
                            else:
                                st.error("Failed to delete task")
                
                st.divider()
        
        # Show completed tasks
        if not completed_df.empty:
            with st.expander(f"✅ Completed Tasks ({len(completed_df)})", expanded=False):
                for idx, row in completed_df.iterrows():
                    with st.container():
                        col1, col2, col3 = st.columns([0.5, 4.5, 1])
                        
                        with col1:
                            if st.checkbox("", key=f"check_{row['ID']}", value=row['Completed']):
                                pass
                            else:
                                if toggle_todo_status(row['ID'], st.session_state.user_email):
                                    st.rerun()
                        
                        with col2:
                            st.markdown(f"~~{row['Task']}~~")
                            st.caption(f"Completed • Created: {format_date(str(row['Created']).split()[0])}")
                        
                        with col3:
                            if st.button("Delete", key=f"del_todo_{row['ID']}", help="Remove this task"):
                                if delete_todo(row['ID'], st.session_state.user_email):
                                    st.rerun()
                                else:
                                    st.error("Failed to delete task")
                    
                    st.divider()
    else:
        st.info("No tasks yet. Start organizing your day by adding your first task above!")

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application function."""
    # Initialize database connection
    db = init_mongodb()
    if db is None:
        st.error("❌ Unable to connect to database. Please check your connection.")
        return
    
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
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Applications", "🤝 Networking", "📝 Notes", "✅ TODO List"])
    
    with tab1:
        applications_tab()
    
    with tab2:
        networking_tab()
    
    with tab3:
        notes_tab()
    
    with tab4:
        todo_tab()

if __name__ == "__main__":
    main()