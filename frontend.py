import streamlit as st
import requests
import base64
import urllib.parse

st.set_page_config(page_title="Simple Social", layout="wide")

# Initialize session state
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None
if 'current_user' not in st.session_state:
    st.session_state.current_user = None


# -----------------------------
# Helper Functions
# -----------------------------
def get_auth_headers():
    """Return authorization headers if token exists"""
    if st.session_state.auth_token:
        return {"Authorization": f"Bearer {st.session_state.auth_token}"}
    return {}


def encode_text_for_overlay(text):
    """Encode text for ImageKit overlay - base64 then URL encode"""
    if not text:
        return ""
    base64_text = base64.b64encode(text.encode('utf-8')).decode('utf-8')
    return urllib.parse.quote(base64_text)


def create_transformed_url(original_url, transformation_params="", caption_text=None):
    """Apply ImageKit transformation and optional text overlay"""
    if caption_text:
        encoded_caption = encode_text_for_overlay(caption_text)
        text_overlay = f"l-text,ie-{encoded_caption},ly-N20,lx-20,fs-100,co-white,bg-000000A0,l-end"
        transformation_params = text_overlay

    if not transformation_params:
        return original_url

    parts = original_url.split("/")
    base_url = "/".join(parts[:4])
    file_path = "/".join(parts[4:])
    return f"{base_url}/tr:{transformation_params}/{file_path}"


# -----------------------------
# Pages
# -----------------------------
def login_page():
    st.title("🚀 Welcome to Simple Social")

    user_email = st.text_input("Email:")
    user_password = st.text_input("Password:", type="password")

    if user_email and user_password:
        col_login, col_signup = st.columns(2)

        # Login
        with col_login:
            if st.button("Login", type="primary", use_container_width=True):
                login_payload = {"username": user_email, "password": user_password}
                login_response = requests.post(
                    "http://localhost:8000/auth/jwt/login",
                    data=login_payload
                )

                if login_response.status_code == 200:
                    token_data = login_response.json()
                    st.session_state.auth_token = token_data["access_token"]

                    user_response = requests.get(
                        "http://localhost:8000/users/me",
                        headers=get_auth_headers()
                    )

                    if user_response.status_code == 200:
                        st.session_state.current_user = user_response.json()
                        st.rerun()
                    else:
                        st.error("Failed to fetch user info")
                else:
                    st.error("Invalid email or password!")

        # Sign Up
        with col_signup:
            if st.button("Sign Up", type="secondary", use_container_width=True):
                signup_payload = {"email": user_email, "password": user_password}
                signup_response = requests.post(
                    "http://localhost:8000/auth/register",
                    json=signup_payload
                )

                if signup_response.status_code == 201:
                    st.success("Account created! Click Login now.")
                else:
                    error_msg = signup_response.json().get("detail", "Registration failed")
                    st.error(f"Registration failed: {error_msg}")

    else:
        st.info("Enter your email and password above")


def upload_page():
    st.title("📸 Share Something")

    uploaded_file = st.file_uploader(
        "Choose media",
        type=['png', 'jpg', 'jpeg', 'mp4', 'avi', 'mov', 'mkv', 'webm']
    )
    caption_text = st.text_area("Caption:", placeholder="What's on your mind?")

    if uploaded_file and st.button("Share", type="primary"):
        with st.spinner("Uploading..."):
            file_data = {
                "file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
            }
            request_payload = {"caption": caption_text}

            upload_response = requests.post(
                "http://localhost:8000/upload",
                files=file_data,
                data=request_payload,
                headers=get_auth_headers()
            )

            if upload_response.status_code == 200:
                st.success("Posted!")
                st.rerun()
            else:
                st.error(upload_response.json().get("detail", "Upload failed"))


def feed_page():
    st.title("🏠 Feed")

    feed_response = requests.get(
        "http://localhost:8000/feed",
        headers=get_auth_headers()
    )

    if feed_response.status_code == 200:
        post_list = feed_response.json()["posts"]

        if not post_list:
            st.info("No posts yet! Be the first to share something.")
            return

        for post_item in post_list:
            st.markdown("---")

            # Header: user + date + delete button
            col_user, col_action = st.columns([4, 1])

            with col_user:
                st.markdown(f"**{post_item['email']}** • {post_item['created_at'][:10]}")

            with col_action:
                if post_item.get('is_owner', False):
                    if st.button("🗑️", key=f"delete_{post_item['id']}"):
                        delete_response = requests.delete(
                            f"http://localhost:8000/posts/{post_item['id']}",
                            headers=get_auth_headers()
                        )

                        if delete_response.status_code == 200:
                            st.success("Post deleted!")
                            st.rerun()
                        else:
                            st.error("Failed to delete post")

            caption_text = post_item.get('caption', '')

            # Display media
            if post_item['file_type'] == 'image':
                transformed_url = create_transformed_url(post_item['url'], "", caption_text)
                st.image(transformed_url, width=300)
            else:
                video_url = create_transformed_url(
                    post_item['url'],
                    "w-400,h-200,cm-pad_resize,bg-blurred"
                )
                st.video(video_url, width=300)
                st.caption(caption_text)


# -----------------------------
# Main App
# -----------------------------
if st.session_state.current_user is None:
    login_page()
else:
    st.sidebar.title(f"👋 Hi {st.session_state.current_user['email']}!")

    if st.sidebar.button("Logout"):
        st.session_state.current_user = None
        st.session_state.auth_token = None
        st.rerun()

    st.sidebar.markdown("---")
    page_selection = st.sidebar.radio("Navigate:", ["🏠 Feed", "📸 Upload"])

    if page_selection == "🏠 Feed":
        feed_page()
    else:
        upload_page()
