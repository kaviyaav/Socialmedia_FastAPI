# Socialmedia_FastAPI
# Simple Social

Simple Social is a lightweight social media web application built with FastAPI for the backend and Streamlit for the frontend. It allows users to register, log in, upload images or videos with captions, view a global feed, and manage their own posts. Media uploads are handled via ImageKit, supporting optional caption overlays. 

## Features

- User Authentication
  - Registration and login
  - JWT-based authentication
  - Password reset and email verification
- Media Upload
  - Upload images and videos
  - Optional caption overlay for images
  - Automatic media handling with ImageKit
- Feed
  - Global feed showing all posts in reverse chronological order
  - Delete option for user-owned posts
- Responsive Frontend
  - Built with Streamlit
  - Dynamic session state for seamless user experience


## Tech Stack

- Backend: FastAPI, SQLAlchemy, FastAPI Users, JWT Authentication, ImageKit  
- Frontend: Streamlit  
- Database: SQLite (async support, can switch to PostgreSQL)  
- Other Tools: Python, Requests, Base64, URL Encoding  

## Setup Instructions

1. Clone the repository
```bash
git clone https://github.com/yourusername/simple-social.git
cd simple-social


2. Create virtual environment & install dependencies

python -m venv venv
# Linux/macOS
source venv/bin/activate
# Windows
venv\Scripts\activate

pip install -r requirements.txt

3. Configure Environment Variables

Create a .env file in the backend directory with your ImageKit credentials:

IMAGEKIT_PRIVATE_KEY=your_private_key
IMAGEKIT_PUBLIC_KEY=your_public_key
IMAGEKIT_URL=your_url_endpoint

4. Run Backend
uvicorn app.main:app --reload

5. Run Frontend
streamlit run frontend.py


Contributors: Kaviyaa Vasudevan(kaviyaavasudevan@gmail.com), Arun Kumar Srinivasan
