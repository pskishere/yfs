import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./App";
import { initApp } from "./config/app";
import "./i18n";

// Initialize application modules
initApp();

// Lock document scroll in Tauri (iOS WKWebView keyboard avoidance fix).
// Must run before React mounts so the class is present from first paint.
if ((window as any).__TAURI_INTERNALS__ !== undefined) {
  document.documentElement.classList.add('tauri-app');

  // Ant Design's ScrollLocker sets html.style.top = '-Npx' (inline style) when a
  // Drawer/Modal opens. Inline styles beat !important stylesheet rules, so we watch
  // the attribute and immediately reset any non-zero offset back to ''.
  const htmlEl = document.documentElement;
  new MutationObserver(() => {
    if (htmlEl.style.top !== '' && htmlEl.style.top !== '0px') {
      htmlEl.style.top = '';
    }
  }).observe(htmlEl, { attributes: true, attributeFilter: ['style'] });

  // WKWebView keyboard avoidance: iOS scrolls the underlying UIScrollView when the
  // keyboard appears, shifting every element upward — even position:fixed ones,
  // because they are fixed to the layout viewport, not the visual viewport.
  //
  // Fix: use the Visual Viewport API to measure the shift (vv.offsetTop) and the
  // remaining visible height (vv.height), then apply an inverse translateY to #root
  // so it stays anchored at the top of the screen, and shrink its height to match
  // the area above the keyboard.
  const vv = window.visualViewport;
  if (vv) {
    const syncViewport = () => {
      const root = document.getElementById('root');
      if (!root) return;
      const offsetTop = Math.max(0, vv.offsetTop);
      // setProperty with 'important' overrides the CSS `height: 100% !important` rule
      root.style.setProperty('height', `${vv.height}px`, 'important');
      root.style.transform = offsetTop > 0 ? `translateY(${offsetTop}px)` : '';
    };
    vv.addEventListener('resize', syncViewport);
    vv.addEventListener('scroll', syncViewport);
    syncViewport();
  }
}

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Failed to find the root element");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
