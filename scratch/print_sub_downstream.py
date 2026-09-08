import re

with open('data/hms/HMS_Automation_RJKT/Basin_1.basin', 'r') as f:
    text = f.read()

subbasins = re.findall(r'Subbasin:\s*(\w+).*?Area:\s*([\d\.]+).*?Downstream:\s*(\w+)', text, re.DOTALL)
for s in subbasins:
    print(f"Subbasin {s[0]} (Area {s[1]} km2) -> Downstream: {s[2]}")
