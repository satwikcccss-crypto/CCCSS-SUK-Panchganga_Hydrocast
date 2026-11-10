#!/usr/bin/env python3
import sys
import re

from playwright.sync_api import sync_playwright

URL = "http://localhost:3001"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    
    page.goto(URL)
    page.wait_for_load_state("networkidle")
    
    print("Title:", page.title())
    print("URL:", page.url)
    print()
    
    # Look for terminal/logs elements
    selectors = [
        ".terminal",
        ".logs",
        ".code",
        "pre",
        ".log-entry",
        ".log-row",
        ".log-container",
        "#terminal",
        "#logs",
    ]
    
    for sel in selectors:
        locator = page.locator(sel)
        count = locator.count()
        if count > 0:
            text = locator.first.text_content()
            print(f"{sel} ({count}): {text[:600] if text else 'empty'}")
    
    # Also check for any numeric stage values that might be stale
    all_text = page.locator("body").text_content()
    if all_text:
        # Find numbers that look like stage values (531-543 range)
        numbers = re.findall(r"53[1-4]\.\d{2}|54[0-3]\.\d{2}", all_text)
        if numbers:
            print(f"\nStage-like numbers found in body: {set(numbers)}")
    
    # Check input values and placeholders
    inputs = page.locator("input")
    input_count = inputs.count()
    if input_count > 0:
        print(f"\nFound {input_count} input elements")
        for i in range(min(input_count, 5)):
            ph = inputs.nth(i).get_attribute("placeholder")
            if ph:
                print(f"  input[{i}] placeholder: {ph}")
    
    browser.close()
    print("\n--- Audit complete ---")