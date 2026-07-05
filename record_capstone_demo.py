import asyncio
import os
from playwright.async_api import async_playwright

async def record_demo():
    output_dir = "demo_output"
    os.makedirs(output_dir, exist_ok=True)
    print(f"🎬 Starting Capstone Demo Recording... Video will be saved to '{output_dir}'")
    
    async with async_playwright() as p:
        # Launch headless browser for recording
        browser = await p.chromium.launch(headless=True)
        
        # Create a context with video recording enabled
        context = await browser.new_context(
            viewport={'width': 1536, 'height': 800},
            record_video_dir=output_dir,
            record_video_size={'width': 1536, 'height': 800}
        )
        
        page = await context.new_page()
        
        print("🌐 Navigating to FactCheck Live...")
        await page.goto("http://localhost:3000")
        await page.wait_for_timeout(3000)
        
        print("📰 Fetching live news stream...")
        await page.click("#fetch-btn")
        # Wait 4 seconds for news to fully load
        await page.wait_for_timeout(4000) 
        
        print("🤖 Triggering Multi-Agent AI Verify on the top article...")
        verify_btns = await page.query_selector_all("text=AI Verify")
        if verify_btns and len(verify_btns) > 0:
            await verify_btns[0].click()
            # Wait 8 seconds to capture the full streaming terminal output and the final badge render
            await page.wait_for_timeout(8000) 
        
        print("💬 Switching to AI Chat Workspace...")
        chat_tab = await page.query_selector("text=AI Chat")
        if chat_tab:
            await chat_tab.click()
            await page.wait_for_timeout(1500)
            
            chat_input = await page.query_selector("#chat-input")
            if chat_input:
                print("⌨️  Typing message to Orchestrator...")
                await chat_input.fill("Can you explain how you evaluate a source's credibility?")
                await chat_input.press("Enter")
                # Wait for the AI to stream its response
                await page.wait_for_timeout(5000)
                
        print("✨ Demo complete! Wrapping up...")
        await page.wait_for_timeout(2000)
        
        # Closing the context finalizes and saves the .webm video file
        await context.close()
        await browser.close()
        
        # Find the generated video file
        files = [f for f in os.listdir(output_dir) if f.endswith(".webm")]
        if files:
            print(f"✅ SUCCESS: Video saved as {os.path.join(output_dir, files[-1])}")

if __name__ == "__main__":
    asyncio.run(record_demo())
