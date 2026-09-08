import re

with open('data/hms/HMS_Automation_RJKT/Basin_1.basin', 'r') as f:
    lines = f.readlines()

in_reach = False
reach_text = []
for line in lines:
    if line.strip().startswith('Reach:'):
        in_reach = True
        reach_text.append(line)
    elif in_reach:
        reach_text.append(line)
        if line.strip().startswith('End:'):
            in_reach = False
            print("".join(reach_text))
            reach_text = []
