# file: app.py
from flask import Flask, request, Response, render_template_string, session, redirect
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

app = Flask(__name__)
# CRITICAL: Required for session management. Change this to a random string.
app.secret_key = 'change_this_to_something_random_and_secure'

# Standard browser headers to avoid detection
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

HOME_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Smart Proxy</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 50px auto; text-align: center; background: #f4f4f4; }
        .container { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        input { padding: 12px; width: 70%; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 12px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 Smart Session Proxy</h1>
        <form action="/proxy" method="GET">
            <input type="url" name="url" placeholder="https://google.com" required>
            <button type="submit">Go</button>
        </form>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HOME_HTML)

@app.route('/proxy')
def main_proxy():
    target_url = request.args.get('url')
    if not target_url:
        return redirect('/')

    # 1. Save the root domain to the session for later "leaking" requests
    parsed = urlparse(target_url)
    # Store "https://google.com" so we know where to route relative paths later
    session['active_root'] = f"{parsed.scheme}://{parsed.netloc}"
    session['current_url'] = target_url

    return fetch_and_rewrite(target_url)

# 2. The Catch-All Route: Handles /search, /images/logo.png, /css/style.css
@app.route('/<path:req_path>', methods=['GET', 'POST'])
def catch_all(req_path):
    # If we don't know where the user is browsing, send them home
    if 'active_root' not in session:
        return redirect('/')
    
    # Reconstruct the full URL: https://google.com + /search?q=test
    target_root = session['active_root']
    full_url = f"{target_root}/{req_path}"
    
    # Pass along query parameters (e.g., ?q=hello)
    if request.query_string:
        full_url += f"?{request.query_string.decode('utf-8')}"
        
    return fetch_and_rewrite(full_url)

def fetch_and_rewrite(url):
    try:
        # Handle both GET and POST (Google Search uses GET, logins use POST)
        if request.method == 'POST':
            resp = requests.post(url, headers=HEADERS, data=request.form, allow_redirects=True)
        else:
            resp = requests.get(url, headers=HEADERS, allow_redirects=True)

        # If it's an image, CSS, or JS, just stream it back directly
        content_type = resp.headers.get('Content-Type', '').lower()
        if 'text/html' not in content_type:
            return Response(resp.content, content_type=content_type)

        # If it's HTML, we need to rewrite links
        soup = BeautifulSoup(resp.content, 'html.parser')

        # Rewrite Links (<a> href)
        for tag in soup.find_all('a', href=True):
            tag['href'] = f"/proxy?url={urljoin(url, tag['href'])}"

        # Rewrite Forms (<form action>)
        # This specifically fixes search bars on Google/Bing
        for tag in soup.find_all('form', action=True):
            original_action = tag['action']
            absolute_action = urljoin(url, original_action)
            # We point the form action to our catch-all route or main proxy
            # For simplicity, we let the catch-all handle the submission path
            tag['action'] = absolute_action.replace(session.get('active_root', ''), '')

        # Rewrite Resources (img, script, link)
        for tag in soup.find_all(['img', 'script', 'link'], src=True):
            # We point these to the proxy so it fetches them from the correct session root
            tag['src'] = f"/proxy?url={urljoin(url, tag['src'])}"
            
        # CSS Links
        for tag in soup.find_all('link', href=True):
            tag['href'] = f"/proxy?url={urljoin(url, tag['href'])}"

        return str(soup)

    except Exception as e:
        return f"Proxy Error: {e}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
