import subprocess
import sys
import re
def run_server():
    while True:
        print("\n🚀 Attempting to start the Django server...")
        # Run the server and capture both standard output and error logs
        process = subprocess.Popen(
            [sys.executable, "manage.py", "runserver"],
            stderr=subprocess.PIPE,
            text=True
        )
        # Read the error log line by line to detect missing modules
        missing_module = None
        while True:
            line = process.stderr.readline()
            if not line:
                break
            print(line, end="") # Print the error to your console
            
            # Look for common python missing module error patterns
            match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", line)
            if match:
                missing_module = match.group(1)
                process.terminate() # Kill the server process to fix the error
                break
        process.wait()
        # If a missing module was caught, install it and loop again
        if missing_module:
            # Handle cases where package name differs from import name (e.g., PIL vs Pillow)
            package_map = {"PIL": "Pillow"}
            package_to_install = package_map.get(missing_module, missing_module)
            print(f"\n📦 Missing module detected: '{missing_module}'")
            print(f"🛠️ Installing {package_to_install} via pip...")
            subprocess.run([sys.executable, "-m", "pip", "install", package_to_install])
            print("🔄 Retrying server launch...")
        else:
            # If the server stopped for another reason (or Ctrl+C), break the loop
            break
if __name__ == "__main__":
    run_server()
