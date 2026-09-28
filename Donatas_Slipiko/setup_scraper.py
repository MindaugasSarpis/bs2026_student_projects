import subprocess
import sys

def run_installer():
    # List of required libraries from the user's scraper script
    libraries = [
        "selenium", 
        "webdriver-manager", 
        "beautifulsoup4", 
        "pandas", 
        "matplotlib", 
        "seaborn"
    ]

    print("--- Starting Environment Setup for Aruodas Scraper ---")
    
    # 1. Upgrade pip first
    print("Upgrading pip...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    except Exception as e:
        print(f"Note: Could not upgrade pip (non-critical). Error: {e}")

    # 2. Install each required library
    for library in libraries:
        print(f"\nInstalling {library}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", library])
            print(f"Successfully installed {library}.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install {library}. Error: {e}")

    print("\n" + "="*40)
    print("--- Setup Complete! ---")
    print("You can now run: python3 aruodas_data_scraper.py")
    print("="*40)

if __name__ == '__main__':
    run_installer()
