# file: app.py
from flask import Flask, request, Response, render_template_string
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = Flask(__name__)

# Basic Homepage
HOME_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Anonymous View</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 50px auto; text-align: center; }
        input { padding: 12px; width: 70%; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 12px 20px; background: #333; color: #fff; border: none; cursor: pointer; }
        button:hover { background: #555; }
    </style>
</head>
<body>
    <h1>👻 Anonymous View</h1>
    <form action="/view">
        <input type="url" name="target" placeholder="https://example.com" required>
        <button type="submit">Go Hidden</button>
    </form>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HOME_HTML)

@app.route('/view')
def proxy():
    target_url = request.args.get('target')
    if not target_url:
        return "Error: No URL provided", 400

    try:
        # 1. Fetch the content SERVER-SIDE (Masks your IP)
        # We verify=False to ignore SSL errors on some older sites
        headers = {'User-Agent': 'Mozilla/5.0 (Compatible; AnonymousProxy/1.0)'}
        resp = requests.get(target_url, headers=headers, verify=False, timeout=10)
        
        # If it's not text/html (e.g., an image), stream it directly
        content_type = resp.headers.get('Content-Type', '')
        if 'text/html' not in content_type:
            return Response(resp.content, content_type=content_type)

        # 2. Parse and Rewrite the DOM
        soup = BeautifulSoup(resp.content, 'html.parser')

        # Rewrite all links (<a> href)
        for tag in soup.find_all('a', href=True):
            original_link = tag['href']
            # Convert relative paths (/about) to absolute (https://site.com/about)
            absolute_link = urljoin(target_url, original_link)
            # Point the link back to our proxy
            tag['href'] = f"/view?target={absolute_link}"

        # Rewrite all resources (<img> src, <link> href, <script> src)
        for tag in soup.find_all(['img', 'script', 'iframe'], src=True):
            original_src = tag['src']
            absolute_src = urljoin(target_url, original_src)
            tag['src'] = f"/view?target={absolute_src}"
            
        for tag in soup.find_all('link', href=True): # CSS
            original_href = tag['href']
            absolute_href = urljoin(target_url, original_href)
            tag['href'] = f"/view?target={absolute_href}"

        # 3. Inject a visual banner (optional)
        banner = soup.new_tag("div", style="background:#333;color:#fff;padding:10px;text-align:center;font-size:12px;position:fixed;top:0;left:0;width:100%;z-index:99999;")
        banner.string = f"Viewing via Proxy: {target_url}"
        if soup.body:
            soup.body.insert(0, banner)

        return str(soup)

    except Exception as e:
        return f"Proxy Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
