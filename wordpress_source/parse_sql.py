import re
import sys
import os

sql_path = 'APP-DATA.SQL'

print("Analyzing database dump...")

posts_inserts = []
postmeta_inserts = []
options_inserts = []

# Simple streaming parser
with open(sql_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        if 'INSERT INTO `wp_posts` VALUES' in line or 'INSERT INTO wp_posts VALUES' in line:
            posts_inserts.append(line)
        elif 'INSERT INTO `wp_options` VALUES' in line or 'INSERT INTO wp_options VALUES' in line:
            options_inserts.append(line)
        elif 'INSERT INTO `wp_postmeta` VALUES' in line or 'INSERT INTO wp_postmeta VALUES' in line:
            postmeta_inserts.append(line)

print(f"Found {len(posts_inserts)} lines of inserts for wp_posts")
print(f"Found {len(options_inserts)} lines of inserts for wp_options")
print(f"Found {len(postmeta_inserts)} lines of inserts for wp_postmeta")

def parse_values(insert_line):
    prefix_match = re.match(r'^INSERT INTO `?\w+`?\s+VALUES\s*\(', insert_line, re.IGNORECASE)
    if not prefix_match:
        return []
    content = insert_line[prefix_match.end():].rstrip()
    if content.endswith(';'):
        content = content[:-1]
    if content.endswith(')'):
        content = content[:-1]
    
    rows = []
    current_row = []
    current_val = []
    in_string = False
    string_char = None
    escaped = False
    
    i = 0
    length = len(content)
    while i < length:
        c = content[i]
        if escaped:
            current_val.append(c)
            escaped = False
        elif c == '\\':
            current_val.append(c)
            escaped = True
        elif (c == "'" or c == '"') and not escaped:
            if not in_string:
                in_string = True
                string_char = c
                current_val.append(c)
            elif c == string_char:
                in_string = False
                current_val.append(c)
        elif c == ',' and not in_string:
            current_row.append(''.join(current_val).strip())
            current_val = []
        elif c == ')' and not in_string:
            current_row.append(''.join(current_val).strip())
            rows.append(current_row)
            current_row = []
            current_val = []
            if i + 2 < length and content[i+1] == ',' and content[i+2] == '(':
                i += 2
        elif c == '(' and not in_string and len(current_row) == 0 and len(current_val) == 0:
            pass
        else:
            current_val.append(c)
        i += 1
        
    return rows

print("Parsing posts...")
all_posts = []
for line in posts_inserts:
    rows = parse_values(line)
    for r in rows:
        if len(r) >= 20:
            all_posts.append(r)

print(f"Total parsed posts/pages/products: {len(all_posts)}")

types = {}
status_count = {}
published_by_type = {}

def clean_sql_str(s):
    if s.startswith("'") and s.endswith("'"):
        s = s[1:-1]
    elif s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    s = s.replace("\\'", "'").replace('\\"', '"').replace('\\n', '\n').replace('\\r', '\r').replace('\\\\', '\\')
    return s

for p in all_posts:
    p_type = clean_sql_str(p[20])
    p_status = clean_sql_str(p[7])
    types[p_type] = types.get(p_type, 0) + 1
    status_count[p_status] = status_count.get(p_status, 0) + 1
    
    if p_status == 'publish':
        if p_type not in published_by_type:
            published_by_type[p_type] = []
        published_by_type[p_type].append(p)

print("\nPost Types Breakdown:")
for k, v in types.items():
    print(f"  {k}: {v}")

print("\nPost Statuses Breakdown:")
for k, v in status_count.items():
    print(f"  {k}: {v}")

print("\nPublished Items by Type:")
for k, v in published_by_type.items():
    print(f"  {k}: {len(v)}")

# List the published pages
if 'page' in published_by_type:
    print("\n--- PUBLISHED PAGES ---")
    for p in published_by_type['page']:
        pid = clean_sql_str(p[0])
        title = clean_sql_str(p[5])
        slug = clean_sql_str(p[11])
        print(f"ID: {pid} | Title: {title} | Slug: {slug}")

# List first 15 products
if 'product' in published_by_type:
    print("\n--- PUBLISHED PRODUCTS (First 15) ---")
    for p in published_by_type['product'][:15]:
        pid = clean_sql_str(p[0])
        title = clean_sql_str(p[5])
        slug = clean_sql_str(p[11])
        print(f"ID: {pid} | Title: {title} | Slug: {slug}")

# List first 10 posts
if 'post' in published_by_type:
    print("\n--- PUBLISHED POSTS (First 10) ---")
    for p in published_by_type['post'][:10]:
        pid = clean_sql_str(p[0])
        title = clean_sql_str(p[5])
        slug = clean_sql_str(p[11])
        print(f"ID: {pid} | Title: {title} | Slug: {slug}")

# Save detailed summary
output_summary_path = 'db_summary.txt'
with open(output_summary_path, 'w', encoding='utf-8') as sf:
    sf.write("DATABASE SUMMARY\n================\n\n")
    sf.write("Post Types Breakdown:\n")
    for k, v in types.items():
        sf.write(f"  {k}: {v}\n")
    sf.write("\nPublished Items:\n")
    for k, v in published_by_type.items():
        sf.write(f"  {k}: {len(v)}\n")
        
    sf.write("\n================\nPUBLISHED PAGES\n================\n")
    if 'page' in published_by_type:
        for p in published_by_type['page']:
            pid = clean_sql_str(p[0])
            title = clean_sql_str(p[5])
            slug = clean_sql_str(p[11])
            sf.write(f"ID: {pid} | Title: {title} | Slug: {slug}\n")
            
    sf.write("\n================\nPUBLISHED PRODUCTS\n================\n")
    if 'product' in published_by_type:
        for p in published_by_type['product']:
            pid = clean_sql_str(p[0])
            title = clean_sql_str(p[5])
            slug = clean_sql_str(p[11])
            sf.write(f"ID: {pid} | Title: {title} | Slug: {slug}\n")

    sf.write("\n================\nPUBLISHED POSTS\n================\n")
    if 'post' in published_by_type:
        for p in published_by_type['post']:
            pid = clean_sql_str(p[0])
            title = clean_sql_str(p[5])
            slug = clean_sql_str(p[11])
            sf.write(f"ID: {pid} | Title: {title} | Slug: {slug}\n")

print(f"\nSaved detailed summary to {output_summary_path}")
