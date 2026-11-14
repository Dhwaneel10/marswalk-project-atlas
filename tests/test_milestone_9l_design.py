"""
Unit and integration tests for MarsWalk 2.0 Milestone 9L:
Visual Identity Transformation, Editorial Typography, Landing Page & Onboarding.
"""

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
WEB_DIR = REPO_ROOT / "web"


def test_design_system_specification_exists():
    """Verify that docs/marswalk-visual-design-system.md exists and contains design token specifications."""
    design_doc = DOCS_DIR / "marswalk-visual-design-system.md"
    assert design_doc.exists(), "docs/marswalk-visual-design-system.md must exist."

    content = design_doc.read_text(encoding="utf-8")
    # Verify core design reference synthesis
    assert "REFERENCE 1: AEROSPACE" in content or "Space-exploration startup" in content
    assert "REFERENCE 2: PLANETARY" in content or "Planetary onboarding" in content
    assert "REFERENCE 3: ASPERA" in content or "Aspera editorial" in content

    # Verify color palette and design tokens
    assert "--accent-coral" in content
    assert "--accent-lavender" in content
    assert "--accent-rose" in content
    assert "--bg-space-void" in content
    assert "--bg-space-navy" in content

    # Verify typography hierarchy
    assert "--font-display" in content
    assert "Cinzel" in content
    assert "Playfair Display" in content

    # Verify responsive breakpoints & scientific provenance
    assert "1920" in content
    assert "1366" in content
    assert "1024" in content
    assert "390" in content
    assert "USGS" in content
    assert "ESRI:103885" in content


def test_index_html_landing_page_structure():
    """Verify web/index.html includes the full landing page hero, CTAs, and destination selector."""
    index_html = WEB_DIR / "index.html"
    assert index_html.exists(), "web/index.html must exist."

    html = index_html.read_text(encoding="utf-8")

    # Fonts
    assert "Cinzel" in html
    assert "Playfair Display" in html
    assert "Inter" in html
    assert "JetBrains Mono" in html

    # Landing page elements
    assert 'id="marsLandingPage"' in html
    assert "landing-headline" in html
    assert "A NEW WORLD." in html
    assert "WITHIN REACH." in html

    # Primary and secondary CTAs
    assert 'id="btnLandingExplore"' in html
    assert 'id="btnLandingHowItWorks"' in html
    assert 'id="btnLandingBrowseMissions"' in html
    assert 'id="btnLandingEnterWorkstation"' in html

    # Vertical destination selector
    assert "vertical-destination-list" in html
    assert 'data-dest="jezero"' in html
    assert 'data-dest="olympus"' in html
    assert 'data-dest="valles"' in html
    assert 'data-dest="gale"' in html

    # Expandable How It Works section
    assert 'id="landingHowItWorksSection"' in html
    assert 'id="btnHowEnterAtlas"' in html
    assert 'id="btnHowClose"' in html

    # Onboarding Modal
    assert 'id="marsOnboardingModal"' in html
    assert 'id="onboardingStepLabel"' in html
    assert 'id="btnOnboardingPrev"' in html
    assert 'id="btnOnboardingNext"' in html
    assert 'id="btnOnboardingFinish"' in html
    assert 'id="btnOnboardingSkip"' in html

    # 3 Distinct Steps
    assert 'data-step="1"' in html
    assert 'data-step="2"' in html
    assert 'data-step="3"' in html

    # HUD Header affordances
    assert 'id="btnHeaderLanding"' in html
    assert 'id="btnHeaderGuide"' in html
    assert 'id="btnHeaderBrandLanding"' in html


def test_styles_css_design_system_and_responsive_rules():
    """Verify web/styles.css contains the design tokens, landing rules, and responsive media queries."""
    styles_css = WEB_DIR / "styles.css"
    assert styles_css.exists(), "web/styles.css must exist."

    css = styles_css.read_text(encoding="utf-8")

    # Tokens in :root
    assert "--accent-coral:" in css
    assert "--accent-lavender:" in css
    assert "--accent-rose:" in css
    assert "--bg-space-void:" in css
    assert "--bg-space-navy:" in css
    assert "--bg-surface-glass:" in css
    assert "--font-editorial:" in css
    assert "--font-serif:" in css

    # Core components
    assert ".landing-page-overlay" in css
    assert ".landing-headline" in css
    assert ".vertical-destination-list" in css
    assert ".dest-item" in css
    assert ".onboarding-modal-overlay" in css
    assert ".onboarding-card" in css
    assert ".progress-bar" in css
    assert ".btn-header-landing" in css
    assert ".btn-header-guide" in css

    # Responsive breakpoints
    assert "@media (max-width: 1366px)" in css
    assert "@media (max-width: 1024px)" in css
    assert "@media (max-width: 768px)" in css
    assert "@media (max-width: 480px)" in css


def test_app_js_methods_and_onboarding_storage_contract():
    """Verify web/app.js implements the landing page & onboarding controller and exposes __atlas methods."""
    app_js = WEB_DIR / "app.js"
    assert app_js.exists(), "web/app.js must exist."

    js = app_js.read_text(encoding="utf-8")

    # LocalStorage key
    assert "marswalk_onboarding_v1" in js

    # Core functions
    assert "function showLandingPage" in js
    assert "function hideLandingPage" in js
    assert "function openOnboarding" in js
    assert "function closeOnboarding" in js
    assert "function setOnboardingStep" in js
    assert "function resetOnboarding" in js
    assert "function handleDestinationSelect" in js

    # Public window.__atlas exposure
    assert "showLandingPage:" in js
    assert "hideLandingPage:" in js
    assert "isLandingPageActive:" in js
    assert "openOnboarding:" in js
    assert "closeOnboarding:" in js
    assert "setOnboardingStep:" in js
    assert "getOnboardingStep:" in js
    assert "resetOnboarding:" in js
    assert "selectDestination:" in js

    # Deep-linking detection to avoid trapping automation
    assert "isDeepLink" in js
    assert "skip_landing" in js
