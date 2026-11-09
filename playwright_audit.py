import playwright.sync_api as p

def run_audit():
    with p.chromium.launch(headless=True) as browser:
        # === Public Dashboard ===
        page = browser.new_page()
        page.goto('http://localhost:3000')
        print('=== PUBLIC DASHBOARD ===')
        # Check page title/heading
        title = page.title()
        print(f'Page title: {title}')
        
        # Check for stage values visible on page
        # Look for elements containing stage text
        stage_elements = page.locator('text=533').all()
        print(f'Elements with "533" (Shivaji stage): {len(stage_elements)}')
        
        stage_elements_541 = page.locator('text=541').all()
        print(f'Elements with "541" (alert threshold): {len(stage_elements_541)}')
        
        # Check if CrossSectionViewer is visible
        try:
            cs_visible = page.locator('text=Cross Section').is_visible()
            print(f'CrossSectionViewer visible: {cs_visible}')
        except: pass
        
        # Check EngineeringGauge
        try:
            gauge_visible = page.locator('text=Current Level').is_visible()
            print(f'EngineeringGauge "Current Level" visible: {gauge_visible}')
        except: pass
        
        page.close()
        
        # === Admin Dashboard ===
        page = browser.new_page()
        page.goto('http://localhost:3001')
        print()
        print('=== ADMIN DASHBOARD ===')
        title = page.title()
        print(f'Page title: {title}')
        
        # Check pipeline status
        try:
            pipeline_text = page.locator('text=pipeline').text_content()
            print(f'Pipeline text: {pipeline_text[:100]}')
        except: pass
        
        # Check stage values
        stage_elements = page.locator('text=533').all()
        print(f'Elements with "533" (Shivaji stage): {len(stage_elements)}')
        
        stage_elements_541 = page.locator('text=541').all()
        print(f'Elements with "541" (alert threshold): {len(stage_elements_541)}')
        
        page.close()
        
        print()
        print('=== AUDIT COMPLETE ===')
        print('Summary:')
        print('  - If "533" count > 0 and "541" count == alert threshold count: PASSED')
        print('  - If "541" appears as "forecast" (not threshold): FAILED - stale data')

run_audit()