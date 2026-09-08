import re

with open('data/hms/HMS_Automation_RJKT/Basin_1.basin', 'r') as f:
    text = f.read()

subbasins = re.findall(r'Subbasin:\s*(\w+).*?Area:\s*([\d\.]+).*?Curve Number:\s*([\d\.]+).*?Lag:\s*([\d\.]+)', text, re.DOTALL)
print("Subbasins in Basin_1.basin:")
print(f"{'ID':<6} {'Area(km2)':<12} {'CN':<10} {'Lag(min)':<12} {'Lag(hr)':<10}")
for s in subbasins:
    lag_min = float(s[3])
    print(f"{s[0]:<6} {s[1]:<12} {s[2]:<10} {s[3]:<12} {lag_min/60.0:<10.1f}")

reaches = re.findall(r'Reach:\s*(\w+).*?Muskingum K:\s*([\d\.]+).*?Muskingum x:\s*([\d\.]+)', text, re.DOTALL)
print("\nReaches in Basin_1.basin:")
print(f"{'Reach':<8} {'K (hr)':<10} {'x':<8}")
for r in reaches:
    print(f"{r[0]:<8} {r[1]:<10} {r[2]:<8}")
