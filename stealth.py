"""
Browser stealth module — injects scripts and configures contexts
to evade TikTok's bot detection.
"""

import random
from fake_useragent import UserAgent
from playwright.async_api import BrowserContext

from logger import log

_ua = UserAgent(browsers=["chrome"], os=["windows", "macos"], min_version=118.0)

# Realistic viewport sizes
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
]

TIMEZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "Europe/London",
]

LOCALES = ["en-US", "en-GB", "en-CA", "en-AU"]


def random_profile() -> dict:
    """Generate a randomized browser profile."""
    viewport = random.choice(VIEWPORTS)
    return {
        "user_agent": _ua.random,
        "viewport": viewport,
        "screen": {"width": viewport["width"], "height": viewport["height"]},
        "locale": random.choice(LOCALES),
        "timezone_id": random.choice(TIMEZONES),
        "color_scheme": random.choice(["light", "dark", "no-preference"]),
        "device_scale_factor": random.choice([1, 1.25, 1.5, 2]),
    }


# JavaScript to inject before every page load
STEALTH_JS = """
// --- webdriver ---
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
delete navigator.__proto__.webdriver;

// --- languages ---
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});

// --- plugins ---
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const arr = [
            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
            {name: 'Native Client', filename: 'internal-nacl-plugin'},
        ];
        arr.item = i => arr[i];
        arr.namedItem = n => arr.find(p => p.name === n);
        arr.refresh = () => {};
        return arr;
    }
});

// --- chrome runtime ---
window.chrome = window.chrome || {};
window.chrome.runtime = window.chrome.runtime || {
    connect: () => {},
    sendMessage: () => {},
    PlatformOs: {MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros', LINUX: 'linux'},
};

// --- permissions ---
const _query = window.Notification
    ? Notification.permission
    : 'default';
if (navigator.permissions) {
    const origQuery = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = params =>
        params.name === 'notifications'
            ? Promise.resolve({state: _query})
            : origQuery(params);
}

// --- iframe contentWindow ---
try {
    const iframeProto = HTMLIFrameElement.prototype;
    const origGetter = Object.getOwnPropertyDescriptor(iframeProto, 'contentWindow').get;
    Object.defineProperty(iframeProto, 'contentWindow', {
        get: function() {
            const w = origGetter.call(this);
            if (w && !w.chrome) w.chrome = window.chrome;
            return w;
        }
    });
} catch(e) {}

// --- WebGL vendor/renderer ---
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(param) {
    if (param === 37445) return 'Intel Inc.';
    if (param === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.call(this, param);
};
try {
    const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(param) {
        if (param === 37445) return 'Intel Inc.';
        if (param === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter2.call(this, param);
    };
} catch(e) {}

// --- hairline feature ---
try {
    Object.defineProperty(document, 'hasFocus', {value: () => true});
} catch(e) {}
"""


async def apply_stealth(context: BrowserContext, profile: dict | None = None):
    """Apply stealth scripts and settings to a browser context."""
    if profile is None:
        profile = random_profile()

    await context.add_init_script(STEALTH_JS)
    log.debug("Stealth scripts injected (UA: %s)", profile.get("user_agent", "default"))
