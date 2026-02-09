const express = require('express');
const proxy = require('express-http-proxy');
const path = require('path');
const app = express();
const PORT = process.env.PORT || 8080;

// Serve the frontend HTML
app.use(express.static('public'));

// The Proxy Logic
app.use('/proxy', (req, res, next) => {
    const targetUrl = req.query.url;
    if (!targetUrl) return res.send("No URL provided.");

    return proxy(targetUrl, {
        proxyReqOptDecorator: (proxyReqOpts) => {
            // MASK IP: Railway's IP is sent instead of yours
            // MASK USER-AGENT: Overwrite with a generic string
            proxyReqOpts.headers['user-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36';
            
            // STRIP HEADERS: Remove location/tracking data
            delete proxyReqOpts.headers['cookie'];
            delete proxyReqOpts.headers['referer'];
            delete proxyReqOpts.headers['x-forwarded-for'];
            return proxyReqOpts;
        },
        userResHeaderDecorator: (headers) => {
            // MASK LOCATION/TIME: Replace identifying headers
            headers['server'] = 'Privacy-Gateway';
            return headers;
        }
    })(req, res, next);
});

app.listen(PORT, () => console.log(`Proxy running on port ${PORT}`));
