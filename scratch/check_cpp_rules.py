import re

with open('DLDD-MAFF-JDLA.cpp', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check lines 4805 to 5055 (1-based)
start = 4805
end = 5065

print(f"Scanning DLDD-MAFF-JDLA.cpp lines {start} to {end}...")

violations = []
for i in range(start - 1, min(end, len(lines))):
    line_num = i + 1
    line = lines[i]
    stripped = line.strip()

    # remove comments
    if '//' in stripped:
        stripped = stripped[:stripped.find('//')].strip()

    # check break
    if re.search(r'\bbreak\b', stripped):
        violations.append((line_num, "break", line))
    # check continue
    if re.search(r'\bcontinue\b', stripped):
        violations.append((line_num, "continue", line))
    # check switch
    if re.search(r'\bswitch\b', stripped):
        violations.append((line_num, "switch", line))
    # check ternary ?
    if '?' in stripped:
        violations.append((line_num, "ternary", line))
    # check return in void
    if re.search(r'\breturn\b', stripped):
        violations.append((line_num, "return in void function", line))
    # check single line if: if (...) stmt; (without {)
    if re.match(r'^\s*if\s*\(.*\)[^{]*;$', line):
        violations.append((line_num, "single line if", line))

print(f"Total violations found: {len(violations)}")
for v in violations:
    print(v)
