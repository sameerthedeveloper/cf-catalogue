import re
import subprocess
import sys

with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

# Find all script blocks
scripts = re.findall(r"<script>(.*?)</script>", content, re.DOTALL)

js_code = ""
for idx, script in enumerate(scripts):
    js_code += f"\n// --- Script Block {idx} ---\n" + script

with open("temp_diagnostic.js", "w", encoding="utf-8") as f:
    f.write(js_code)

print("Running node syntax check on extracted JavaScript...")
res = subprocess.run(["node", "-c", "temp_diagnostic.js"], capture_output=True, text=True)

if res.returncode == 0:
    print("SUCCESS: Extracted JavaScript contains no syntax errors!")
else:
    print("ERROR: JavaScript contains syntax errors:")
    print(res.stderr)
    sys.exit(1)
