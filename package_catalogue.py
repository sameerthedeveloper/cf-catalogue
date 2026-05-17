import json
import zipfile
import os

sql_path = os.path.join('wordpress_source', 'APP-DATA.SQL')

print("Extracting fresh products data from the SQL database...")

# We can reuse the extraction logic to make sure we have the exact data
tables = {
    'wp_posts': [],
    'wp_postmeta': [],
    'wp_terms': [],
    'wp_term_taxonomy': [],
    'wp_term_relationships': []
}

with open(sql_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        for tname in tables.keys():
            if f'INSERT INTO `{tname}` VALUES' in line or f'INSERT INTO {tname} VALUES' in line:
                tables[tname].append(line)

def parse_values(insert_line):
    import re
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

def clean_sql_str(s):
    if s.startswith("'") and s.endswith("'"):
        s = s[1:-1]
    elif s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    s = s.replace("\\'", "'").replace('\\"', '"').replace('\\n', '\n').replace('\\r', '\r').replace('\\\\', '\\')
    return s

# 1. Parse terms
terms = {}
for line in tables['wp_terms']:
    rows = parse_values(line)
    for r in rows:
        if len(r) >= 3:
            tid = clean_sql_str(r[0])
            name = clean_sql_str(r[1])
            slug = clean_sql_str(r[2])
            terms[tid] = {'name': name, 'slug': slug}

# 2. Parse term taxonomy
taxonomies = {}
for line in tables['wp_term_taxonomy']:
    rows = parse_values(line)
    for r in rows:
        if len(r) >= 3:
            ttid = clean_sql_str(r[0])
            tid = clean_sql_str(r[1])
            tax = clean_sql_str(r[2])
            taxonomies[ttid] = {'term_id': tid, 'taxonomy': tax}

# 3. Parse term relationships
relationships = {}
for line in tables['wp_term_relationships']:
    rows = parse_values(line)
    for r in rows:
        if len(r) >= 2:
            oid = clean_sql_str(r[0])
            ttid = clean_sql_str(r[1])
            if oid not in relationships:
                relationships[oid] = []
            relationships[oid].append(ttid)

# 4. Parse postmeta
postmeta = {}
for line in tables['wp_postmeta']:
    rows = parse_values(line)
    for r in rows:
        if len(r) >= 4:
            pid = clean_sql_str(r[1])
            mkey = clean_sql_str(r[2])
            mval = clean_sql_str(r[3])
            if pid not in postmeta:
                postmeta[pid] = {}
            postmeta[pid][mkey] = mval

# 5. Parse posts
all_posts_raw = []
for line in tables['wp_posts']:
    rows = parse_values(line)
    for r in rows:
        if len(r) >= 20:
            all_posts_raw.append(r)

posts_by_id = {}
for p in all_posts_raw:
    pid = clean_sql_str(p[0])
    posts_by_id[pid] = p

# Extract attachments (images)
images = {}
for pid, p in posts_by_id.items():
    ptype = clean_sql_str(p[20])
    if ptype == 'attachment':
        guid = clean_sql_str(p[18])
        if 'wp-content/uploads' in guid:
            idx = guid.find('wp-content/uploads')
            images[pid] = guid[idx:]
        else:
            images[pid] = guid

# Extract Categories
def get_categories(oid):
    cat_names = []
    if oid in relationships:
        for ttid in relationships[oid]:
            if ttid in taxonomies:
                tax = taxonomies[ttid]
                if tax['taxonomy'] == 'product_cat':
                    tid = tax['term_id']
                    if tid in terms:
                        cat_names.append(terms[tid]['name'])
    return cat_names

products = []
for pid, p in posts_by_id.items():
    ptype = clean_sql_str(p[20])
    status = clean_sql_str(p[7])
    
    if ptype == 'product' and status == 'publish':
        title = clean_sql_str(p[5])
        content = clean_sql_str(p[4])
        excerpt = clean_sql_str(p[6])
        slug = clean_sql_str(p[11])
        
        pm = postmeta.get(pid, {})
        price = pm.get('_price', '')
        reg_price = pm.get('_regular_price', '')
        sku = pm.get('_sku', '')
        
        thumb_id = pm.get('_thumbnail_id', '')
        image_url = images.get(thumb_id, 'wp-content/themes/audib/assets/images/placeholder.jpg')
        
        gallery_ids = pm.get('_product_image_gallery', '').split(',')
        gallery_urls = [images[gid] for gid in gallery_ids if gid in images]
        
        import re
        desc = re.sub(r'\[.*?\]', '', content)
        
        products.append({
            'id': pid,
            'title': title,
            'slug': slug,
            'price': price,
            'regular_price': reg_price,
            'sku': sku,
            'image': image_url,
            'gallery': gallery_urls,
            'categories': get_categories(pid),
            'excerpt': excerpt,
            'description': desc
        })

print(f"Parsed {len(products)} products.")

# Save to products.json
with open('products.json', 'w', encoding='utf-8') as jsonf:
    json.dump(products, jsonf, indent=4)

print("Saved products.json")

# Generate self-contained catalogue.html
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cinema Focus | Hi-Fi Product Catalogue</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;700;800&display=swap');

        :root {{
            --bg-obsidian: #080809;
            --bg-charcoal: #0F0F11;
            --bg-panel: #16161A;
            --text-primary: #F5F5F7;
            --text-secondary: #9A9A9F;
            --text-muted: #5F5F64;
            --gold-accent: #C5A880;
            --gold-bright: #E2C9A5;
            --gold-glass: rgba(197, 168, 128, 0.08);
            --gold-glow: rgba(197, 168, 128, 0.25);
            --border-light: rgba(255, 255, 255, 0.07);
            --border-gold: rgba(197, 168, 128, 0.2);
            --glass-bg: rgba(15, 15, 17, 0.8);
            --glass-blur: blur(20px);
            --radius-sm: 6px;
            --radius-md: 12px;
            --radius-lg: 20px;
            --transition-smooth: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-font-smoothing: antialiased;
        }}

        body {{
            background-color: var(--bg-obsidian);
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
            line-height: 1.6;
            overflow-x: hidden;
            padding-bottom: 5rem;
        }}

        h1, h2, h3, h4 {{
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            color: var(--text-primary);
        }}

        .header {{
            background: rgba(8, 8, 9, 0.8);
            backdrop-filter: var(--glass-blur);
            border-bottom: 1px solid var(--border-light);
            position: sticky;
            top: 0;
            z-index: 100;
            padding: 1.25rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .logo-section {{
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }}
        .logo-img {{
            height: 40px;
            width: auto;
            object-fit: contain;
        }}
        .logo-icon {{
            background: var(--gold-glass);
            border: 1px solid var(--border-gold);
            color: var(--gold-accent);
            padding: 0.4rem 0.8rem;
            border-radius: var(--radius-sm);
            font-family: 'Outfit', sans-serif;
            font-weight: 800;
            font-size: 1.2rem;
        }}
        .logo-text h1 {{
            font-size: 1.3rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .logo-text p {{
            font-size: 0.75rem;
            color: var(--text-secondary);
        }}

        .badge-bar {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        .badge-btn {{
            background: var(--bg-panel);
            border: 1px solid var(--border-light);
            padding: 0.6rem 1.2rem;
            border-radius: var(--radius-sm);
            font-size: 0.85rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            transition: var(--transition-smooth);
        }}
        .badge-btn:hover {{
            border-color: var(--gold-accent);
            color: var(--gold-accent);
        }}
        .badge-count {{
            background: var(--gold-accent);
            color: var(--bg-obsidian);
            font-weight: 700;
            padding: 0.1rem 0.4rem;
            border-radius: 10px;
            font-size: 0.75rem;
        }}

        .layout {{
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 3rem;
            max-width: 1400px;
            margin: 3rem auto;
            padding: 0 2rem;
        }}

        .sidebar {{
            position: sticky;
            top: 110px;
            height: calc(100vh - 150px);
            overflow-y: auto;
        }}

        .widget {{
            margin-bottom: 2.5rem;
        }}
        .widget-title {{
            font-size: 1.05rem;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 1.2rem;
            border-left: 3px solid var(--gold-accent);
            padding-left: 0.8rem;
        }}

        .search-box {{
            position: relative;
        }}
        .search-input {{
            width: 100%;
            background: var(--bg-panel);
            border: 1px solid var(--border-light);
            border-radius: var(--radius-sm);
            padding: 0.8rem 1rem 0.8rem 2.5rem;
            font-size: 0.95rem;
            color: var(--text-primary);
            transition: var(--transition-smooth);
        }}
        .search-input:focus {{
            border-color: var(--gold-accent);
            box-shadow: 0 0 10px rgba(197, 168, 128, 0.15);
        }}
        .search-icon {{
            position: absolute;
            left: 0.9rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-secondary);
            font-size: 1.1rem;
        }}

        .filter-list {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}
        .filter-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.6rem 0.8rem;
            border-radius: var(--radius-sm);
            cursor: pointer;
            transition: var(--transition-smooth);
            font-size: 0.9rem;
            color: var(--text-secondary);
        }}
        .filter-item:hover, .filter-item.active {{
            background: var(--gold-glass);
            color: var(--text-primary);
        }}
        .filter-item.active {{
            font-weight: 600;
            border-left: 2px solid var(--gold-accent);
        }}
        .filter-count {{
            background: var(--bg-obsidian);
            font-size: 0.75rem;
            padding: 0.15rem 0.4rem;
            border-radius: 10px;
            border: 1px solid var(--border-light);
        }}

        .main-catalog {{
            display: flex;
            flex-direction: column;
            gap: 1.8rem;
        }}

        .catalog-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-light);
            padding-bottom: 1rem;
        }}
        .results-count {{
            color: var(--text-secondary);
            font-size: 0.95rem;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1.8rem;
        }}

        .card {{
            background: var(--glass-bg);
            border: 1px solid var(--border-light);
            border-radius: var(--radius-md);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: var(--transition-smooth);
        }}
        .card:hover {{
            border-color: var(--border-gold);
            box-shadow: 0 10px 25px rgba(0,0,0,0.5), 0 0 15px rgba(197, 168, 128, 0.05);
        }}

        .img-container {{
            background: linear-gradient(135deg, var(--bg-panel) 0%, rgba(22, 22, 26, 0.4) 100%);
            aspect-ratio: 1.1;
            padding: 1.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
        }}
        .card-img {{
            max-width: 100%;
            max-height: 180px;
            object-fit: contain;
            transition: var(--transition-smooth);
        }}
        .card:hover .card-img {{
            transform: scale(1.06);
        }}
        .badge-brand {{
            position: absolute;
            top: 1rem;
            left: 1rem;
            background: var(--bg-obsidian);
            border: 1px solid var(--border-gold);
            color: var(--gold-accent);
            font-size: 0.65rem;
            text-transform: uppercase;
            font-weight: 700;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            letter-spacing: 0.5px;
        }}

        .info {{
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            flex-grow: 1;
        }}
        .card-title {{
            font-size: 1.15rem;
            font-weight: 600;
            margin-bottom: 0.4rem;
            display: -webkit-box;
            -webkit-line-clamp: 1;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .card-sku {{
            font-family: monospace;
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 0.8rem;
        }}
        .card-desc {{
            font-size: 0.88rem;
            color: var(--text-secondary);
            margin-bottom: 1.25rem;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            flex-grow: 1;
        }}
        .card-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: auto;
        }}
        .card-price {{
            font-weight: 700;
            color: var(--gold-accent);
        }}

        .btn-card-add {{
            background: var(--gold-accent);
            color: var(--bg-obsidian);
            padding: 0.6rem 1rem;
            border-radius: var(--radius-sm);
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition-smooth);
            border: 1px solid var(--gold-accent);
        }}
        .btn-card-add:hover {{
            background: transparent;
            color: var(--gold-accent);
        }}
        .btn-card-add.added {{
            background: transparent;
            border-color: var(--border-light);
            color: var(--text-secondary);
        }}

        /* --- Quick View Specs Lightbox Modals --- */
        .modal {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0,0,0,0.85);
            backdrop-filter: blur(8px);
            z-index: 500;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            opacity: 0;
            transition: var(--transition-smooth);
        }}
        .modal.open {{
            display: flex;
            opacity: 1;
        }}
        .modal-card {{
            background: var(--bg-panel);
            border: 1px solid var(--border-gold);
            border-radius: var(--radius-lg);
            width: 100%;
            max-width: 950px;
            max-height: 90vh;
            overflow-y: auto;
            position: relative;
            padding: 3rem;
            display: grid;
            grid-template-columns: 1fr 1.2fr;
            gap: 3.5rem;
        }}
        .modal-close {{
            position: absolute;
            top: 1.5rem;
            right: 1.5rem;
            font-size: 1.8rem;
            cursor: pointer;
            color: var(--text-secondary);
            transition: var(--transition-smooth);
        }}
        .modal-close:hover {{
            color: var(--gold-accent);
        }}

        .modal-gallery {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}
        .modal-img-wrapper {{
            background: var(--bg-charcoal);
            border: 1px solid var(--border-light);
            border-radius: var(--radius-md);
            padding: 1.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            aspect-ratio: 1;
        }}
        .modal-img {{
            max-width: 100%;
            max-height: 250px;
            object-fit: contain;
        }}
        .modal-thumbs {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}
        .modal-thumb {{
            width: 50px;
            height: 50px;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border-light);
            background: var(--bg-charcoal);
            padding: 0.2rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .modal-thumb.active {{
            border-color: var(--gold-accent);
        }}
        .modal-thumb img {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }}

        .modal-details {{
            display: flex;
            flex-direction: column;
        }}
        .modal-brand {{
            color: var(--gold-accent);
            text-transform: uppercase;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 1px;
            margin-bottom: 0.5rem;
        }}
        .modal-title {{
            font-size: 1.8rem;
            margin-bottom: 0.4rem;
        }}
        .modal-sku {{
            font-family: monospace;
            color: var(--text-muted);
            font-size: 0.85rem;
            text-transform: uppercase;
            margin-bottom: 1.5rem;
        }}
        .modal-price {{
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--gold-accent);
            margin-bottom: 1.5rem;
        }}
        .modal-desc {{
            color: var(--text-secondary);
            font-size: 0.92rem;
            max-height: 180px;
            overflow-y: auto;
            margin-bottom: 2rem;
            padding-right: 0.5rem;
        }}

        .no-results {{
            grid-column: 1 / -1;
            text-align: center;
            padding: 5rem 2rem;
            color: var(--text-muted);
        }}
        .no-results-icon {{
            font-size: 3rem;
            margin-bottom: 1rem;
        }}

        /* Shortlist drawer styling */
        .drawer-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0,0,0,0.6);
            backdrop-filter: blur(5px);
            z-index: 400;
            display: none;
            justify-content: flex-end;
        }}
        .drawer-overlay.open {{
            display: flex;
        }}
        .drawer {{
            background: var(--bg-panel);
            width: 100%;
            max-width: 450px;
            height: 100vh;
            border-left: 1px solid var(--border-light);
            display: flex;
            flex-direction: column;
            padding: 2rem;
        }}
        .drawer-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-light);
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
        }}
        .drawer-close {{
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--text-secondary);
        }}
        .drawer-close:hover {{
            color: var(--gold-accent);
        }}
        .drawer-items {{
            flex-grow: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}
        .drawer-item {{
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.8rem;
            background: var(--bg-charcoal);
            border: 1px solid var(--border-light);
            border-radius: var(--radius-sm);
        }}
        .drawer-item-img {{
            width: 50px;
            height: 50px;
            object-fit: contain;
            background: var(--bg-panel);
            border-radius: 4px;
        }}
        .drawer-item-info {{
            flex-grow: 1;
        }}
        .drawer-item-title {{
            font-size: 0.88rem;
            font-weight: 600;
        }}
        .drawer-item-remove {{
            cursor: pointer;
            color: var(--text-muted);
        }}
        .drawer-item-remove:hover {{
            color: #FF3B30;
        }}
        .drawer-footer {{
            border-top: 1px solid var(--border-light);
            padding-top: 1.5rem;
            margin-top: 1.5rem;
        }}
        .btn-action {{
            width: 100%;
            background: var(--gold-accent);
            color: var(--bg-obsidian);
            padding: 0.8rem 1.5rem;
            border-radius: var(--radius-sm);
            font-weight: 600;
            font-size: 0.88rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            cursor: pointer;
            border: 1px solid var(--gold-accent);
            transition: var(--transition-smooth);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }}
        .btn-action:hover {{
            background: transparent;
            color: var(--gold-accent);
        }}

        /* Responsive */
        @media (max-width: 1100px) {{
            .grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            .modal-card {{
                grid-template-columns: 1fr;
                gap: 2rem;
                padding: 2rem;
            }}
            .modal-img-wrapper {{
                aspect-ratio: 1.5;
            }}
        }}
        @media (max-width: 860px) {{
            .layout {{
                grid-template-columns: 1fr;
            }}
            .sidebar {{
                position: relative;
                top: 0;
                height: auto;
            }}
        }}
        @media (max-width: 580px) {{
            .grid {{
                grid-template-columns: 1fr;
            }}
            .header {{
                padding: 1rem;
            }}
        }}

        /* Print styles */
        @media print {{
            body {{
                background: white;
                color: black;
            }}
            .header, .sidebar, .catalog-header, .btn-card-add, .badge-bar {{
                display: none !important;
            }}
            .layout {{
                display: block;
                padding: 0;
                margin: 0;
            }}
            .grid {{
                display: block;
            }}
            .card {{
                page-break-inside: avoid;
                border: 1px solid #ccc;
                border-radius: 8px;
                margin-bottom: 1.5rem;
                display: flex;
                flex-direction: row;
                height: auto !important;
                min-height: 150px;
                background: white;
                overflow: visible !important;
            }}
            .img-container {{
                width: 150px;
                padding: 10px;
                border-right: 1px solid #ccc;
                background: none;
                flex-shrink: 0;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .card-img {{
                max-height: 120px;
                max-width: 100%;
                object-fit: contain;
            }}
            .info {{
                padding: 1rem;
                flex-grow: 1;
                display: flex;
                flex-direction: column;
                justify-content: center;
                overflow: visible !important;
            }}
            .card-title {{
                display: block !important;
                overflow: visible !important;
                -webkit-line-clamp: unset !important;
                white-space: normal !important;
                color: #111 !important;
                font-size: 1.3rem !important;
                font-weight: 700 !important;
                margin-bottom: 0.3rem !important;
                height: auto !important;
            }}
            .card-desc {{
                display: block !important;
                overflow: visible !important;
                -webkit-line-clamp: unset !important;
                color: #555 !important;
                font-size: 0.88rem !important;
                line-height: 1.4 !important;
                height: auto !important;
                margin-bottom: 0.5rem !important;
            }}
            .card-sku {{
                color: #777 !important;
                font-size: 0.8rem !important;
                margin-bottom: 0.5rem !important;
            }}
            .card-price {{
                color: var(--gold-accent) !important;
                font-weight: 700 !important;
                font-size: 1.15rem !important;
            }}
            .badge-brand {{
                display: none !important;
            }}
            .card-footer {{
                margin-top: 0.5rem;
            }}

            /* Shortlist PDF styles */
            #print-shortlist-container {{
                display: none;
            }}
            body.print-shortlist-only .layout {{
                display: none !important;
            }}
            body.print-shortlist-only #print-shortlist-container {{
                display: block !important;
            }}
            .print-shortlist-header {{
                border-bottom: 2px solid #C5A880;
                padding-bottom: 1rem;
                margin-bottom: 2rem;
                display: flex;
                justify-content: space-between;
                align-items: flex-end;
            }}
            .print-shortlist-title h1 {{
                font-size: 2.2rem;
                font-family: 'Outfit', sans-serif;
                color: #111;
                margin-bottom: 0.2rem;
            }}
            .print-shortlist-title p {{
                font-size: 0.95rem;
                color: #666;
            }}
            .print-shortlist-meta {{
                text-align: right;
                font-size: 0.88rem;
                color: #444;
                line-height: 1.4;
            }}
        }}
        #print-shortlist-container {{
            display: none;
        }}
    </style>
</head>
<body>

    <!-- --- Header Navigation Bar --- -->
    <header class="header">
        <div class="logo-section">
            <img src="image.png" alt="Cinema Focus Logo" class="logo-img">
            <div class="logo-text">
                <h1>Cinema Focus</h1>
                <p>High-End Hi-Fi Master Catalogue</p>
            </div>
        </div>
        <div class="badge-bar">
            <button class="badge-btn" id="shortlist-btn">
                <i class="fa-solid fa-list-check"></i> Shortlisted Gear 
                <span class="badge-count" id="badge-count">0</span>
            </button>
            <button class="badge-btn" style="border-color: var(--border-gold); color: var(--gold-accent);" onclick="window.print()">
                <i class="fa-solid fa-print"></i> Print PDF
            </button>
        </div>
    </header>

    <!-- --- Layout Shell --- -->
    <div class="layout">
        
        <!-- Sidebar filters -->
        <aside class="sidebar">
            <!-- Search widget -->
            <div class="widget">
                <h3 class="widget-title">Live Search</h3>
                <div class="search-box">
                    <i class="fa-solid fa-magnifying-glass search-icon"></i>
                    <input type="text" placeholder="Search title, SKU..." class="search-input" id="search-input">
                </div>
            </div>
            
            <!-- Category checklist -->
            <div class="widget">
                <h3 class="widget-title">Categories</h3>
                <div class="filter-list" id="cat-filter-list">
                    <!-- Loaded dynamically -->
                </div>
            </div>
            
            <!-- Brands checklist -->
            <div class="widget">
                <h3 class="widget-title">Distributor Network</h3>
                <div class="filter-list" id="brand-filter-list">
                    <!-- Loaded dynamically -->
                </div>
            </div>
        </aside>
        
        <!-- Main Catalog grid -->
        <main class="main-catalog">
            <div class="catalog-header">
                <span class="results-count" id="count-display">Showing 0 of 0 premium gears</span>
                <select id="sort-selector" style="background: var(--bg-panel); border: 1px solid var(--border-light); padding: 0.5rem; border-radius: var(--radius-sm); color: var(--text-primary); cursor: pointer;">
                    <option value="default">Default Sort</option>
                    <option value="alpha-asc">Name (A-Z)</option>
                    <option value="alpha-desc">Name (Z-A)</option>
                </select>
            </div>
            
            <div class="grid" id="products-grid">
                <!-- Cards loaded dynamically -->
            </div>
        </main>
    </div>

    <!-- --- Detail specs Modal --- -->
    <div class="modal" id="specs-modal">
        <div class="modal-card">
            <div class="modal-close" id="modal-close">&times;</div>
            <div class="modal-gallery">
                <div class="modal-img-wrapper">
                    <img src="" alt="" class="modal-img" id="modal-main-img">
                </div>
                <div class="modal-thumbs" id="modal-thumbs">
                    <!-- Dynamic -->
                </div>
            </div>
            <div class="modal-details">
                <span class="modal-brand" id="modal-brand">Brand</span>
                <h2 class="modal-title" id="modal-title">Product Name</h2>
                <div class="modal-sku" id="modal-sku">SKU Code</div>
                <div class="modal-price" id="modal-price">₹0.00</div>
                
                <h3 style="font-size: 1rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem;">Acoustic Parameters</h3>
                <div class="modal-desc" id="modal-desc">Description contents</div>
                
                <button class="btn-action" style="margin-top: auto;" id="modal-shortlist-btn">
                    <i class="fa-solid fa-plus"></i> Add To Shortlist
                </button>
            </div>
        </div>
    </div>

    <!-- --- Shortlist Drawer --- -->
    <div class="drawer-overlay" id="drawer-overlay">
        <div class="drawer">
            <div class="drawer-header">
                <h2>Shortlisted Systems</h2>
                <div class="drawer-close" id="drawer-close">&times;</div>
            </div>
            <div class="drawer-items" id="drawer-items">
                <!-- Loaded dynamically -->
            </div>
            <div class="drawer-footer">
                <button class="btn-action" onclick="printShortlist()" style="margin-bottom: 0.8rem;">
                    <i class="fa-solid fa-file-pdf"></i> Generate PDF Sheet
                </button>
                <button class="btn-action" style="background: transparent; border-color: var(--border-light); color: var(--text-secondary);" id="clear-shortlist-btn">
                    <i class="fa-solid fa-trash-can"></i> Clear Selection
                </button>
            </div>
        </div>
    </div>

    <!-- --- Embed Products Database --- -->
    <script>
        const productsData = {json.dumps(products, indent=4)};
    </script>

    <!-- --- Catalogue Application Script --- -->
    <script>
        let selectedItems = [];
        let activeCat = 'all';
        let activeBrand = 'all';
        let searchQuery = '';
        let currentSort = 'default';

        // Online fallbacks for backup images
        const liveSitePrefix = 'https://www.cinemafocus.in/';

        document.addEventListener("DOMContentLoaded", () => {{
            loadShortlist();
            initFilters();
            renderCatalog();
            bindEvents();
        }});

        function initFilters() {{
            const catContainer = document.getElementById("cat-filter-list");
            const brandContainer = document.getElementById("brand-filter-list");
            
            const catMap = {{}};
            const brandMap = {{}};
            
            productsData.forEach(p => {{
                if (p.categories && Array.isArray(p.categories)) {{
                    p.categories.forEach(cat => {{
                        catMap[cat] = (catMap[cat] || 0) + 1;
                    }});
                }}
                
                const b = getProductBrand(p);
                brandMap[b] = (brandMap[b] || 0) + 1;
            }});
            
            // Render Cats
            let catHtml = `
                <div class="filter-item active" data-cat="all" onclick="selectCat('all')">
                    <span>All Categories</span>
                    <span class="filter-count">${{productsData.length}}</span>
                </div>
            `;
            Object.keys(catMap).sort().forEach(cat => {{
                catHtml += `
                    <div class="filter-item" data-cat="${{cat}}" onclick="selectCat('${{cat}}')">
                        <span>${{cat}}</span>
                        <span class="filter-count">${{catMap[cat]}}</span>
                    </div>
                `;
            }});
            catContainer.innerHTML = catHtml;
            
            // Render Brands
            let brandHtml = `
                <div class="filter-item active" data-brand="all" onclick="selectBrand('all')">
                    <span>All Networks</span>
                    <span class="filter-count">${{productsData.length}}</span>
                </div>
            `;
            Object.keys(brandMap).sort().forEach(brand => {{
                brandHtml += `
                    <div class="filter-item" data-brand="${{brand}}" onclick="selectBrand('${{brand}}')">
                        <span>${{brand}}</span>
                        <span class="filter-count">${{brandMap[brand]}}</span>
                    </div>
                `;
            }});
            brandContainer.innerHTML = brandHtml;
        }}

        function getProductBrand(product) {{
            const titleLower = product.title.toLowerCase();
            if (titleLower.includes('kii')) return 'Kii Audio';
            if (titleLower.includes('proac') || titleLower.includes('pro ac')) return 'ProAc';
            if (titleLower.includes('audio vector') || titleLower.includes('audiovector')) return 'Audiovector';
            if (titleLower.includes('system audio') || titleLower.includes('saxo') || titleLower.includes('legend')) return 'System Audio';
            if (titleLower.includes('octave')) return 'Octave';
            if (titleLower.includes('lumin')) return 'Lumin';
            if (titleLower.includes('aurender')) return 'Aurender';
            if (titleLower.includes('mj acoustic') || titleLower.includes('mj acoustics')) return 'MJ Acoustics';
            if (titleLower.includes('eversolo')) return 'Eversolo';
            if (titleLower.includes('ferrum')) return 'Ferrum';
            if (titleLower.includes('hifirose') || titleLower.includes('rose')) return 'Hifirose';
            return 'Other Brands';
        }}

        function selectCat(cat) {{
            activeCat = cat;
            document.querySelectorAll("#cat-filter-list .filter-item").forEach(el => {{
                if (el.getAttribute("data-cat") === cat) el.classList.add("active");
                else el.classList.remove("active");
            }});
            renderCatalog();
        }}

        function selectBrand(brand) {{
            activeBrand = brand;
            document.querySelectorAll("#brand-filter-list .filter-item").forEach(el => {{
                if (el.getAttribute("data-brand") === brand) el.classList.add("active");
                else el.classList.remove("active");
            }});
            renderCatalog();
        }}

        function renderCatalog() {{
            const grid = document.getElementById("products-grid");
            const countText = document.getElementById("count-display");
            
            let filtered = productsData.filter(p => {{
                const matchesCat = activeCat === 'all' || (p.categories && p.categories.includes(activeCat));
                const matchesBrand = activeBrand === 'all' || getProductBrand(p).toLowerCase() === activeBrand.toLowerCase();
                const matchesSearch = p.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                                     (p.sku && p.sku.toLowerCase().includes(searchQuery.toLowerCase())) ||
                                     (p.excerpt && p.excerpt.toLowerCase().includes(searchQuery.toLowerCase()));
                
                return matchesCat && matchesBrand && matchesSearch;
            }});

            if (currentSort === 'alpha-asc') {{
                filtered.sort((a,b) => a.title.localeCompare(b.title));
            }} else if (currentSort === 'alpha-desc') {{
                filtered.sort((a,b) => b.title.localeCompare(a.title));
            }}
            
            countText.innerText = `Showing ${{filtered.length}} of ${{productsData.length}} premium gears`;
            
            if (filtered.length === 0) {{
                grid.innerHTML = `
                    <div class="no-results">
                        <div class="no-results-icon"><i class="fa-solid fa-volume-xmark"></i></div>
                        <h3>No matching gear found</h3>
                        <p>Refine your search term or select another category.</p>
                    </div>
                `;
                return;
            }}
            
            let html = '';
            filtered.forEach(p => {{
                const inShortlist = selectedItems.includes(p.id);
                const btnClass = inShortlist ? 'btn-card-add added' : 'btn-card-add';
                const btnText = inShortlist ? '<i class="fa-solid fa-check"></i> Added' : '<i class="fa-solid fa-plus"></i> Shortlist';
                
                let priceStr = 'Price on Request';
                if (p.price && p.price !== '') {{
                    const numPrice = parseFloat(p.price);
                    if (!isNaN(numPrice)) {{
                        priceStr = '₹' + numPrice.toLocaleString('en-IN', {{ minimumFractionDigits: 2 }});
                    }}
                }}
                
                let mainImg = p.image || 'wp-content/themes/audib/assets/images/placeholder.jpg';
                
                html += `
                    <div class="card">
                        <div class="img-container" onclick="openSpecsModal('${{p.id}}')" style="cursor: pointer;">
                            <span class="badge-brand">${{getProductBrand(p)}}</span>
                            <img src="${{mainImg}}" alt="${{p.title}}" class="card-img" onerror="this.src='${{liveSitePrefix}}' + '${{mainImg}}'; this.onerror=function(){{this.src='wp-content/uploads/woocommerce-placeholder.png'}}">
                        </div>
                        <div class="info">
                            <h3 class="card-title" onclick="openSpecsModal('${{p.id}}')" style="cursor: pointer;" title="${{p.title}}">${{p.title}}</h3>
                            <div class="card-sku">SKU: ${{p.sku || 'N/A'}}</div>
                            <p class="card-desc">${{p.excerpt || 'Elite Hi-Fi component crafted for pristine soundstage acoustics.'}}</p>
                            <div class="card-footer">
                                <span class="card-price">${{priceStr}}</span>
                                <button class="${{btnClass}}" onclick="toggleShortlist('${{p.id}}', event)">${{btnText}}</button>
                            </div>
                        </div>
                    </div>
                `;
            }});
            grid.innerHTML = html;
        }}

        // Modal View
        window.openSpecsModal = function(productId) {{
            const product = productsData.find(p => p.id === productId);
            if (!product) return;
            
            const mainImg = product.image || 'wp-content/themes/audib/assets/images/placeholder.jpg';
            document.getElementById("modal-main-img").src = mainImg;
            document.getElementById("modal-main-img").onerror = function() {{
                this.src = liveSitePrefix + mainImg;
                this.onerror = function() {{
                    this.src = 'wp-content/uploads/woocommerce-placeholder.png';
                }}
            }};
            
            document.getElementById("modal-brand").innerText = getProductBrand(product);
            document.getElementById("modal-title").innerText = product.title;
            document.getElementById("modal-sku").innerText = 'SKU Code: ' + (product.sku || 'N/A');
            
            let priceStr = 'Price on Audition';
            if (product.price && product.price !== '') {{
                const numPrice = parseFloat(product.price);
                if (!isNaN(numPrice)) {{
                    priceStr = '₹' + numPrice.toLocaleString('en-IN', {{ minimumFractionDigits: 2 }});
                }}
            }}
            document.getElementById("modal-price").innerText = priceStr;
            
            document.getElementById("modal-desc").innerHTML = `<p style="margin-bottom:10px;">${{product.excerpt || 'Elite high fidelity loudspeaker component representing state-of-the-art acoustic physics.'}}</p><p>${{product.description || 'Dedicated room acoustic calibration services are bundled with this luxury setup.'}}</p>`;
            
            // Build thumbs
            const thumbsContainer = document.getElementById("modal-thumbs");
            let thumbHtml = `
                <div class="modal-thumb active" onclick="swapModalImage(this, '${{mainImg}}')">
                    <img src="${{mainImg}}" onerror="this.src='${{liveSitePrefix}}' + '${{mainImg}}'; this.onerror=function(){{this.src='wp-content/uploads/woocommerce-placeholder.png'}}">
                </div>
            `;
            if (product.gallery && Array.isArray(product.gallery)) {{
                product.gallery.forEach(img => {{
                    if (img && img !== '' && img !== mainImg) {{
                        thumbHtml += `
                            <div class="modal-thumb" onclick="swapModalImage(this, '${{img}}')">
                                <img src="${{img}}" onerror="this.src='${{liveSitePrefix}}' + '${{img}}'; this.onerror=function(){{this.src='wp-content/uploads/woocommerce-placeholder.png'}}">
                            </div>
                        `;
                    }}
                }});
            }}
            thumbsContainer.innerHTML = thumbHtml;
            
            // Hook Add button
            const addBtn = document.getElementById("modal-shortlist-btn");
            const inShortlist = selectedItems.includes(product.id);
            if (inShortlist) {{
                addBtn.innerHTML = '<i class="fa-solid fa-check"></i> Added To Shortlist';
                addBtn.style.background = 'transparent';
                addBtn.style.borderColor = 'var(--border-light)';
                addBtn.style.color = 'var(--text-secondary)';
            }} else {{
                addBtn.innerHTML = '<i class="fa-solid fa-plus"></i> Add To Shortlist';
                addBtn.style.background = 'var(--gold-accent)';
                addBtn.style.borderColor = 'var(--gold-accent)';
                addBtn.style.color = 'var(--bg-obsidian)';
            }}
            
            addBtn.onclick = function() {{
                toggleShortlist(product.id, null);
                openSpecsModal(product.id); // Refresh modal state
            }};
            
            document.getElementById("specs-modal").classList.add("open");
        }};

        window.swapModalImage = function(thumb, src) {{
            document.querySelectorAll(".modal-thumb").forEach(t => t.classList.remove("active"));
            thumb.classList.add("active");
            
            const mainImg = document.getElementById("modal-main-img");
            mainImg.src = src;
            mainImg.onerror = function() {{
                this.src = liveSitePrefix + src;
                this.onerror = function() {{
                    this.src = 'wp-content/uploads/woocommerce-placeholder.png';
                }}
            }};
        }};

        // Shortlist Logic
        window.toggleShortlist = function(productId, event) {{
            if (event) event.stopPropagation();
            
            const idx = selectedItems.indexOf(productId);
            if (idx === -1) {{
                selectedItems.push(productId);
            }} else {{
                selectedItems.splice(idx, 1);
            }}
            
            saveShortlist();
            updateUI();
            renderCatalog();
        }};

        function updateUI() {{
            document.getElementById("badge-count").innerText = selectedItems.length;
            
            // Update Drawer
            const drawerContainer = document.getElementById("drawer-items");
            if (selectedItems.length === 0) {{
                drawerContainer.innerHTML = `
                    <div style="text-align: center; padding: 4rem 1rem; color: var(--text-muted);">
                        <i class="fa-solid fa-list-ul" style="font-size: 2rem; margin-bottom:1rem;"></i>
                        <p>No shortlisted items yet.</p>
                    </div>
                `;
                return;
            }}
            
            let html = '';
            selectedItems.forEach(pid => {{
                const p = productsData.find(prod => prod.id === pid);
                if (!p) return;
                
                const mainImg = p.image || 'wp-content/themes/audib/assets/images/placeholder.jpg';
                
                html += `
                    <div class="drawer-item">
                        <img src="${{mainImg}}" alt="${{p.title}}" class="drawer-item-img" onerror="this.src='${{liveSitePrefix}}' + '${{mainImg}}'; this.onerror=function(){{this.src='wp-content/uploads/woocommerce-placeholder.png'}}">
                        <div class="drawer-item-info">
                            <h4 class="drawer-item-title">${{p.title}}</h4>
                            <span style="font-size:0.75rem; color:var(--text-muted);">${{p.sku || 'SD-TBA'}}</span>
                        </div>
                        <div class="drawer-item-remove" onclick="toggleShortlist('${{p.id}}', null)">
                            <i class="fa-solid fa-trash-can"></i>
                        </div>
                    </div>
                `;
            }});
            drawerContainer.innerHTML = html;
        }}

        function saveShortlist() {{
            localStorage.setItem("cf_shortlist_catalogue", JSON.stringify(selectedItems));
        }}

        function loadShortlist() {{
            const saved = localStorage.getItem("cf_shortlist_catalogue");
            if (saved) {{
                try {{
                    selectedItems = JSON.parse(saved);
                    updateUI();
                }} catch(e) {{
                    selectedItems = [];
                }}
            }}
        }}

        function bindEvents() {{
            // Search filter
            document.getElementById("search-input").addEventListener("input", (e) => {{
                searchQuery = e.target.value;
                renderCatalog();
            }});
            
            // Sort filter
            document.getElementById("sort-selector").addEventListener("change", (e) => {{
                currentSort = e.target.value;
                renderCatalog();
            }});
            
            // Modal close
            document.getElementById("modal-close").addEventListener("click", () => {{
                document.getElementById("specs-modal").classList.remove("open");
            }});
            
            document.getElementById("specs-modal").addEventListener("click", (e) => {{
                if (e.target === document.getElementById("specs-modal")) {{
                    document.getElementById("specs-modal").classList.remove("open");
                }}
            }});
            
            // Drawer toggles
            document.getElementById("shortlist-btn").addEventListener("click", () => {{
                document.getElementById("drawer-overlay").classList.add("open");
            }});
            document.getElementById("drawer-close").addEventListener("click", () => {{
                document.getElementById("drawer-overlay").classList.remove("open");
            }});
            document.getElementById("drawer-overlay").addEventListener("click", (e) => {{
                if (e.target === document.getElementById("drawer-overlay")) {{
                    document.getElementById("drawer-overlay").classList.remove("open");
                }}
            }});
            
            // Clear shortlist button
            document.getElementById("clear-shortlist-btn").addEventListener("click", () => {{
                selectedItems = [];
                saveShortlist();
                updateUI();
                renderCatalog();
            }});
        }}

        window.printShortlist = function() {{
            if (selectedItems.length === 0) {{
                alert("Please add some premium gears to your shortlist first!");
                return;
            }}
            
            const container = document.getElementById("print-shortlist-container");
            if (!container) return;
            
            const today = new Date().toLocaleDateString('en-IN', {{
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            }});
            
            const randomRef = 'CF-' + Math.floor(100000 + Math.random() * 900000);
            
            let html = `
                <div class="print-shortlist-header">
                    <div class="print-shortlist-title" style="display: flex; align-items: center; gap: 1rem;">
                        <img src="image.png" alt="Cinema Focus Logo" class="logo-img" style="height: 50px; width: auto; object-fit: contain;">
                        <div>
                            <h1 style="margin: 0; font-size: 2rem; font-family: 'Outfit', sans-serif; color: #111;">Cinema Focus</h1>
                            <p style="margin: 0; font-size: 0.95rem; color: #666;">High-End Hi-Fi Master Catalogue | Shortlist Systems</p>
                        </div>
                    </div>
                    <div class="print-shortlist-meta">
                        <div><strong>Date:</strong> ${{today}}</div>
                        <div><strong>Ref Code:</strong> ${{randomRef}}</div>
                    </div>
                </div>
                <div class="grid">
            `;
            
            selectedItems.forEach(pid => {{
                const p = productsData.find(prod => prod.id === pid);
                if (!p) return;
                
                let priceStr = 'Price on Request';
                if (p.price && p.price !== '') {{
                    const numPrice = parseFloat(p.price);
                    if (!isNaN(numPrice)) {{
                        priceStr = '₹' + numPrice.toLocaleString('en-IN', {{ minimumFractionDigits: 2 }});
                    }}
                }}
                
                let mainImg = p.image || 'wp-content/themes/audib/assets/images/placeholder.jpg';
                
                html += `
                    <div class="card">
                        <div class="img-container">
                            <img src="${{mainImg}}" alt="${{p.title}}" class="card-img" onerror="this.src='${{liveSitePrefix}}' + '${{mainImg}}'; this.onerror=function(){{this.src='wp-content/uploads/woocommerce-placeholder.png'}}">
                        </div>
                        <div class="info">
                            <h3 class="card-title">${{p.title}}</h3>
                            <div class="card-sku">SKU: ${{p.sku || 'N/A'}}</div>
                            <p class="card-desc">${{p.excerpt || 'Elite Hi-Fi component crafted for pristine soundstage acoustics.'}}</p>
                            <div class="card-footer">
                                <span class="card-price">${{priceStr}}</span>
                            </div>
                        </div>
                    </div>
                `;
            }});
            
            html += `</div>`;
            container.innerHTML = html;
            
            document.body.classList.add("print-shortlist-only");
            window.print();
        }};

        window.addEventListener("afterprint", () => {{
            document.body.classList.remove("print-shortlist-only");
            const container = document.getElementById("print-shortlist-container");
            if (container) container.innerHTML = '';
        }});
    </script>
    <div id="print-shortlist-container"></div>
</body>
</html>
"""

with open('catalogue.html', 'w', encoding='utf-8') as htmlf:
    htmlf.write(html_content)

print("Saved catalogue.html")

# Create a zip file containing products.json, catalogue.html and image.png
zip_name = 'cinema_focus_catalogue.zip'
with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.write('products.json')
    zf.write('catalogue.html')
    if os.path.exists('image.png'):
        zf.write('image.png')

print(f"Successfully packaged {zip_name}!")
