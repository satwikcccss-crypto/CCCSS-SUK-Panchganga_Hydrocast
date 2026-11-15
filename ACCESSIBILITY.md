# ♿ Accessibility Statement — HydroCast

**Last Updated:** November 2026  
**Commitment:** Shivaji University Center for Community Support and Services (CCCSS) & HydroCast Engineering Team

---

## 🎯 Our Commitment

HydroCast is dedicated to ensuring that real-time flood intelligence, water surface elevations, and early warning advisories are accessible to all individuals, including citizens with disabilities, emergency responders operating in high-contrast or low-bandwidth field environments, and individuals using assistive technologies.

We strive to conform to the **Web Content Accessibility Guidelines (WCAG) 2.1 Level AA** standards and Section 508 of the U.S. Rehabilitation Act.

---

## 🛠️ Measures to Support Accessibility

HydroCast integrates accessibility into our design and development workflow across both the **Public Citizen Portal** (`frontend-public`) and the **Operator Console** (`frontend-admin`):

1. **High-Contrast Flood Warning Visuals:**
   - River alert stages (Warning: `542.10 m MSL`, Danger: `543.30 m MSL`) are conveyed through color, distinct typographic weight, numerical values, and iconography (e.g. ⚠️, 🚨) to avoid relying solely on color perception.
2. **Screen Reader Optimization:**
   - Proper ARIA landmarks (`role="banner"`, `role="main"`, `role="region"`), descriptive labels, and table header associations are implemented across live telemetry panels and hydrograph displays.
3. **Keyboard Navigability:**
   - Interactive elements (gauges, dropdowns, navigation sidebars, and disaster alert modals) are fully navigable via standard keyboard inputs (`Tab`, `Shift+Tab`, `Enter`, `Escape`).
4. **Responsive & Mobile Viewports:**
   - Interface dynamically adapts from 320px mobile displays to multi-monitor operations centers without clipping vital emergency metrics or horizontal scroll lock.
5. **Color-Blind Friendly Palettes:**
   - Hydrograph and flood inundation visualizations utilize accessible color palettes with distinct lightness and texture values.

---

## 🌐 Supported Environments & Assistive Technologies

HydroCast is tested against modern evergreen browsers and assistive technologies:
- **Browsers:** Google Chrome, Mozilla Firefox, Microsoft Edge, Safari
- **Screen Readers:** NVDA (Windows), JAWS, VoiceOver (iOS/macOS)
- **Contrast Tools:** Lighthouse Accessibility score target $\ge 95$

---

## ⚠️ Known Limitations & Workarounds

While we strive for comprehensive accessibility, certain complex scientific visualizations present technical challenges:
- **Interactive 2D Cross-Section Geometry (HEC-RAS style):** The SVG river geometry viewer is supplemented by an accessible tabular readout of current stage, water elevation, and riverbank datum.
- **Dynamic Chart Hydrographs:** High-frequency hydrograph points are accompanied by downloadable accessible CSV and PDF advisory bulletins (`GET /api/v1/alerts/bulletin/pdf`).

---

## 📬 Feedback & Reporting Accessibility Barriers

If you encounter an accessibility barrier or require emergency flood advisory information in an alternative format:

- **Contact:** Open a GitHub issue in this repository.
- **Project Lead:** Er. Satwik K. Udupi, Shivaji University CCCSS
- **GitHub Issue:** File an [Accessibility Report](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/new?template=accessibility.yml)

We aim to acknowledge and address accessibility feedback within **48 business hours**.
