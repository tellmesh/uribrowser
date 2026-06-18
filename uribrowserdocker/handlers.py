from __future__ import annotations
import base64
import os
import time
import webbrowser
from pathlib import Path


def _profile(context):
    return context.get('config', {}).get('browser', {})


def _user_data_dir(profile: dict, payload: dict) -> str | None:
    raw = payload.get('user_data_dir') or profile.get('user_data_dir') or os.environ.get('URISYS_BROWSER_USER_DATA_DIR')
    return str(raw).strip() if raw else None


def _cdp_endpoint(profile: dict, payload: dict) -> str:
    raw = (
        payload.get('cdp_endpoint')
        or payload.get('cdp')
        or profile.get('cdp_endpoint')
        or os.environ.get('URISYS_BROWSER_CDP')
        or 'http://127.0.0.1:9222'
    )
    return str(raw).strip()


def _session_state(context):
    session = context.get('params', {}).get('session', 'default')
    state = context.setdefault('state', {})
    sessions = state.setdefault('browser_sessions', {})
    return sessions.setdefault(session, {'url': None, 'title': None, 'html': '<html><body>empty</body></html>'})


def status(payload, context):
    profile = _profile(context)
    session = context.get('params', {}).get('session', 'default')
    sess = _session_state(context)
    return {
        'session': session,
        'driver': profile.get('driver', 'mock'),
        'url': sess.get('url'),
        'title': sess.get('title'),
        'supports': ['mock', 'system-open', 'playwright', 'cdp', 'remote-cdp'],
    }


def open_page(payload, context):
    profile = _profile(context)
    driver = payload.get('driver') or profile.get('driver', 'mock')
    url = payload.get('url')
    if not url:
        raise ValueError('payload.url is required')
    sess = _session_state(context)
    if context.get('dry_run'):
        return {'driver': driver, 'url': url, 'dry_run': True, 'would_open': True}

    if driver == 'system-open':
        if not context.get('allow_real') and not os.environ.get('URISYS_ALLOW_REAL'):
            raise PermissionError('system-open requires context.allow_real=true or URISYS_ALLOW_REAL=1')
        webbrowser.open(url)
        title = 'Opened by system browser'
        html = '<html><body>Opened in external browser</body></html>'
    elif driver == 'playwright':
        # Optional dependency. Keep the example portable by failing clearly if missing.
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception as exc:
            raise RuntimeError('playwright driver requires: pip install playwright && playwright install chromium') from exc
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=bool(profile.get('headless', True)))
            page = browser.new_page()
            page.goto(url)
            title = page.title()
            html = page.content()
            browser.close()
    elif driver == 'remote-cdp':
        # Placeholder: route to a remote Chrome DevTools Protocol bridge in a real deployment.
        cdp_url = profile.get('remote_cdp_url', 'ws://chrome:9222/devtools/browser')
        title = 'Remote CDP placeholder'
        html = f'<html><body>Would call remote CDP at {cdp_url}</body></html>'
    else:
        title = payload.get('title') or 'Mock page'
        html = f'<html><head><title>{title}</title></head><body><h1>Mock Browser</h1><p>{url}</p></body></html>'

    sess.update({'url': url, 'title': title, 'html': html, 'opened_at': time.time(), 'driver': driver})
    return {'session': context.get('params', {}).get('session'), 'driver': driver, 'url': url, 'title': title}


def get_dom(payload, context):
    sess = _session_state(context)
    return {'html': sess.get('html'), 'url': sess.get('url'), 'title': sess.get('title')}


def submit_form(payload, context):
    profile = _profile(context)
    driver = payload.get('driver') or profile.get('driver', 'mock')
    form_id = str(payload.get('form_id') or payload.get('id') or 'default')
    fields = payload.get('fields') or {}
    sess = _session_state(context)
    if context.get('dry_run'):
        return {
            'dry_run': True,
            'driver': driver,
            'form_id': form_id,
            'fields': fields,
            'url': sess.get('url'),
        }
    return {
        'submitted': True,
        'driver': driver,
        'form_id': form_id,
        'fields': fields,
        'url': sess.get('url'),
        'mock': driver == 'mock',
    }


def screenshot(payload, context):
    profile = _profile(context)
    driver = payload.get('driver') or profile.get('driver', 'mock')
    sess = _session_state(context)
    if context.get('dry_run'):
        return {'dry_run': True, 'would_capture': True, 'driver': driver, 'url': sess.get('url')}
    if driver == 'playwright':
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception as exc:
            raise RuntimeError('playwright driver requires: pip install playwright && playwright install chromium') from exc
        url = sess.get('url') or payload.get('url')
        if not url:
            raise ValueError('screenshot requires an opened page (session.url) or payload.url')
        out_dir = Path(profile.get('screenshot_dir') or os.environ.get('URISYS_BROWSER_SCREEN_DIR') or 'data/browser')
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime('%Y-%m-%d_%H-%M-%S')
        path = out_dir / f"browser_{context.get('params', {}).get('session', 'default')}_{stamp}.png"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=bool(profile.get('headless', True)))
            page = browser.new_page()
            page.goto(url)
            page.screenshot(path=str(path))
            browser.close()
        data = path.read_bytes()
        return {
            'mime': 'image/png',
            'base64': base64.b64encode(data).decode('ascii'),
            'path': str(path),
            'url': url,
            'driver': driver,
        }
    data = f"Screenshot placeholder for {sess.get('url') or 'about:blank'}".encode('utf-8')
    b64 = base64.b64encode(data).decode('ascii')
    return {'mime': 'text/plain', 'base64': b64, 'url': sess.get('url'), 'driver': driver, 'mock': driver == 'mock'}


def _linkedin_compose_url(text: str = "") -> str:
    base = "https://www.linkedin.com/feed/?shareActive=true"
    if not text:
        return base
    from urllib.parse import quote
    return f"{base}&text={quote(text)}"


def publish_post(payload, context):
    profile = _profile(context)
    driver = payload.get('driver') or profile.get('driver', 'mock')
    platform = str(payload.get('platform') or 'linkedin').lower()
    text = str(payload.get('text') or payload.get('body') or '')
    if context.get('dry_run'):
        return {'dry_run': True, 'platform': platform, 'driver': driver, 'chars': len(text)}
    if platform != 'linkedin':
        raise ValueError(f'unsupported platform {platform!r} (supported: linkedin)')

    url = str(payload.get('url') or _linkedin_compose_url(text))
    if driver == 'system-open':
        if not context.get('allow_real') and not os.environ.get('URISYS_ALLOW_REAL'):
            raise PermissionError('system-open requires context.allow_real=true or URISYS_ALLOW_REAL=1')
        webbrowser.open(url)
        return {
            'published': False,
            'opened': True,
            'manual': True,
            'platform': platform,
            'url': url,
            'chars': len(text),
            'hint': 'Finish and submit the post in the browser window',
        }
    if driver == 'playwright':
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception as exc:
            raise RuntimeError('playwright driver requires: pip install playwright && playwright install chromium') from exc
        user_data_dir = _user_data_dir(profile, payload)
        if not user_data_dir:
            raise RuntimeError(
                'playwright LinkedIn publish requires payload.user_data_dir, browser.user_data_dir, or URISYS_BROWSER_USER_DATA_DIR'
            )
        if not context.get('allow_real') and not os.environ.get('URISYS_ALLOW_REAL'):
            raise PermissionError('playwright publish requires context.allow_real=true or URISYS_ALLOW_REAL=1')
        headless = payload.get('headless', profile.get('headless', False))
        with sync_playwright() as p:
            context_pw = p.chromium.launch_persistent_context(
                user_data_dir,
                headless=bool(headless),
            )
            page = context_pw.pages[0] if context_pw.pages else context_pw.new_page()
            page.goto(url, wait_until='domcontentloaded')
            drafted = False
            if text:
                editor = None
                for selector in (
                    'div[contenteditable="true"]',
                    '[role="textbox"]',
                    '.ql-editor',
                    'div[data-placeholder*="post"]',
                ):
                    loc = page.locator(selector).first
                    try:
                        loc.wait_for(timeout=30000)
                        editor = loc
                        break
                    except Exception:
                        continue
                if editor is None:
                    return {
                        'published': False,
                        'drafted': False,
                        'opened': True,
                        'manual_submit': True,
                        'platform': platform,
                        'url': page.url,
                        'driver': driver,
                        'chars': len(text),
                        'hint': 'Compose page opened; LinkedIn editor not found — finish manually in the browser window',
                    }
                editor.fill(text)
                drafted = True
            return {
                'published': False,
                'drafted': drafted,
                'manual_submit': True,
                'platform': platform,
                'url': page.url,
                'driver': driver,
                'chars': len(text),
            }
    if driver in ('cdp', 'remote-cdp'):
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception as exc:
            raise RuntimeError('cdp driver requires: pip install playwright') from exc
        if not context.get('allow_real') and not os.environ.get('URISYS_ALLOW_REAL'):
            raise PermissionError('cdp publish requires context.allow_real=true or URISYS_ALLOW_REAL=1')
        endpoint = _cdp_endpoint(profile, payload)
        submit = bool(payload.get('submit', False))
        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(endpoint)
            except Exception as exc:
                raise RuntimeError(
                    f'cdp connect failed at {endpoint!r}; start Chrome with '
                    f'--remote-debugging-port=9222 and an authenticated LinkedIn session'
                ) from exc
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto('https://www.linkedin.com/feed/', wait_until='domcontentloaded', timeout=60000)
            time.sleep(3)
            if '/login' in page.url or '/checkpoint' in page.url:
                return {
                    'published': False, 'opened': True, 'platform': platform,
                    'url': page.url, 'driver': driver, 'chars': len(text),
                    'hint': 'CDP Chrome is not logged in to LinkedIn',
                }
            page.keyboard.press('Escape')
            time.sleep(0.5)
            page.evaluate(
                """() => { const b=[...document.querySelectorAll('button,div[role="button"]')]"""
                """.find(el => /start a post/i.test(el.textContent||'')); if(b) b.click(); }"""
            )
            time.sleep(2)
            editor = page.locator('div[role="textbox"]').first
            try:
                editor.wait_for(timeout=15000)
            except Exception:
                return {
                    'published': False, 'drafted': False, 'opened': True, 'manual_submit': True,
                    'platform': platform, 'url': page.url, 'driver': driver, 'chars': len(text),
                    'hint': 'Share dialog editor not found — finish manually',
                }
            editor.click(force=True)
            editor.fill(text)
            time.sleep(1)
            if not submit:
                return {
                    'published': False, 'drafted': True, 'manual_submit': True,
                    'platform': platform, 'url': page.url, 'driver': driver, 'chars': len(text),
                    'hint': 'Draft composed via CDP; pass submit=true to post automatically',
                }
            clicked = page.evaluate(
                """() => { const c=[...document.querySelectorAll('button')];"""
                """ for (const el of c.reverse()) { const t=(el.innerText||el.textContent||'').trim();"""
                """ const a=(el.getAttribute('aria-label')||'').trim();"""
                """ if(/^post$/i.test(t)||/^post$/i.test(a)){ el.click(); return true; } } return false; }"""
            )
            time.sleep(6)
            return {
                'published': bool(clicked), 'drafted': True, 'manual_submit': not clicked,
                'platform': platform, 'url': page.url, 'driver': driver, 'chars': len(text),
                'hint': None if clicked else 'Post button not found — submit manually',
            }
    return {'published': True, 'platform': platform, 'mock': True, 'chars': len(text)}
