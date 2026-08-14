import { useState, useEffect } from 'react';

/**
 * iOS WKWebView keyboard height detection via Visual Viewport API.
 * Returns the current on-screen keyboard height in pixels (0 when hidden).
 */
export const useKeyboardHeight = (): number => {
  const [keyboardHeight, setKeyboardHeight] = useState(0);

  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;

    const update = () => {
      // visualViewport.offsetTop > 0 means the visual viewport has been scrolled
      // down relative to the layout viewport (iOS does this when keyboard opens).
      const kh = window.innerHeight - vv.height - vv.offsetTop;
      const safeKh = Math.max(0, Math.round(kh));
      setKeyboardHeight(safeKh);

      // Undo the scroll iOS injects when bringing the focused element into view.
      if (safeKh > 0) {
        window.scrollTo(0, 0);
      }
    };

    vv.addEventListener('resize', update);
    vv.addEventListener('scroll', update);
    return () => {
      vv.removeEventListener('resize', update);
      vv.removeEventListener('scroll', update);
    };
  }, []);

  return keyboardHeight;
};
