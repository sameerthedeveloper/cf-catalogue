import re
import json

sql_path = 'APP-DATA.SQL'

print("Starting deep data extraction...")

tables = {
    'wp_posts': [],
    'wp_postmeta': [],
    'wp_terms': [],
    'wp_term_taxonomy': [],
    'wp_term_relationships': []
}

# Stream SQL dump to find lines for each table
with open(sql_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        for tname in tables.keys():
            if f'INSERT INTO `{tname}` VALUES' in line or f'INSERT INTO {tname} VALUES' in line:
                tables[tname].append(line)

print({k: len(v) for k, v in tables.items()})

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

def clean_sql_str(s):
    if s.startswith("'") and s.endswith("'"):
        s = s[1:-1]
    elif s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    s = s.replace("\\'", "'").replace('\\"', '"').replace('\\n', '\n').replace('\\r', '\r').replace('\\\\', '\\')
    return s

# 1. Parse terms
terms = {} # id -> name, slug
for line in tables['wp_terms']:
    rows = parse_values(line)
    for r in rows:
        if len(r) >= 3:
            tid = clean_sql_str(r[0])
            name = clean_sql_str(r[1])
            slug = clean_sql_str(r[2])
            terms[tid] = {'name': name, 'slug': slug}

# 2. Parse term taxonomy
taxonomies = {} # taxonomy_id -> term_id, taxonomy
for line in tables['wp_term_taxonomy']:
    rows = parse_values(line)
    for r in rows:
        if len(r) >= 3:
            ttid = clean_sql_str(r[0])
            tid = clean_sql_str(r[1])
            tax = clean_sql_str(r[2])
            taxonomies[ttid] = {'term_id': tid, 'taxonomy': tax}

# 3. Parse term relationships
relationships = {} # object_id -> list of taxonomy_ids
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
postmeta = {} # post_id -> dict of key-value pairs
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

# Map all raw posts by ID first so we can resolve attachments/thumbnails
posts_by_id = {}
for p in all_posts_raw:
    pid = clean_sql_str(p[0])
    posts_by_id[pid] = p

print(f"Loaded {len(posts_by_id)} posts by ID")

# Extract attachments (images)
images = {} # attachment_id -> guid
for pid, p in posts_by_id.items():
    ptype = clean_sql_str(p[20])
    if ptype == 'attachment':
        guid = clean_sql_str(p[18])
        # Clean standard absolute WordPress URLs to relative paths if possible
        # e.g., https://cinemafocus.in/wp-content/uploads/... -> wp-content/uploads/...
        if 'wp-content/uploads' in guid:
            idx = guid.find('wp-content/uploads')
            images[pid] = guid[idx:]
        else:
            images[pid] = guid

# Extract Categories for Products
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
pages = []

for pid, p in posts_by_id.items():
    ptype = clean_sql_str(p[20])
    status = clean_sql_str(p[7])
    
    if status != 'publish':
        continue
        
    title = clean_sql_str(p[5])
    content = clean_sql_str(p[4])
    excerpt = clean_sql_str(p[6])
    slug = clean_sql_str(p[11])
    
    if ptype == 'product':
        # Get price
        pm = postmeta.get(pid, {})
        price = pm.get('_price', '')
        reg_price = pm.get('_regular_price', '')
        sale_price = pm.get('_sale_price', '')
        sku = pm.get('_sku', '')
        
        # Get thumbnail image
        thumb_id = pm.get('_thumbnail_id', '')
        image_url = images.get(thumb_id, 'wp-content/themes/audib/assets/images/placeholder.jpg')
        
        # Get gallery images
        gallery_ids = pm.get('_product_image_gallery', '').split(',')
        gallery_urls = [images[gid] for gid in gallery_ids if gid in images]
        
        cats = get_categories(pid)
        
        # Clean HTML content a bit for displaying
        desc = re.sub(r'\[.*?\]', '', content) # Remove shortcodes
        
        products.append({
            'id': pid,
            'title': title,
            'slug': slug,
            'price': price,
            'regular_price': reg_price,
            'sale_price': sale_price,
            'sku': sku,
            'image': image_url,
            'gallery': gallery_urls,
            'categories': cats,
            'excerpt': excerpt,
            'description': desc
        })
        
    elif ptype == 'page':
        # Don't include admin or system pages
        if slug in ['cart', 'checkout', 'my-account', 'wishlist', 'cart-2', 'checkout-2', 'my-account-2', 'wishlist-2', 'enquiry-cart', 'request-a-quote']:
            continue
            
        desc = re.sub(r'\[.*?\]', '', content)
        pages.append({
            'id': pid,
            'title': title,
            'slug': slug,
            'description': desc
        })

print(f"Extracted {len(products)} products and {len(pages)} pages.")

# Save to data.js as a structured JS object
js_content = f"""// Structured Site Data extracted from WordPress Backup
const siteInfo = {{
    title: "Cinema Focus",
    tagline: "Cinema Focus in Chennai - India - Premium Audio, Loudspeakers, Electronics and Master Clocks",
    url: "https://www.cinemafocus.in",
    email: "vijay@spintadigital.com",
    phone: "+91 98400 12345", // Custom placeholder
    address: "Chennai, India"
}};

const pagesData = {json.dumps(pages, indent=4)};

const productsData = {json.dumps(products, indent=4)};
"""

with open('data.js', 'w', encoding='utf-8') as jsf:
    jsf.write(js_content)

print("Saved structured data to data.js!")
