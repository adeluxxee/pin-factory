import streamlit as st
import io, os, re, json, uuid, zipfile, random
from datetime import datetime, date, time, timedelta
from pathlib import Path

# =========================
# PIN FACTORY.exe — v0.5
# =========================
st.set_page_config(page_title="PIN FACTORY.exe", page_icon="🎀", layout="wide", initial_sidebar_state="collapsed")

APP_DIR = Path(__file__).resolve().parent
STYLE_REFERENCE_DIR = APP_DIR / "style_references"
STYLE_REFERENCE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

STYLE_REFERENCE_FOLDERS = {
    "Makeup": "makeup_skincare",
    "Skincare": "makeup_skincare",
    "Perfume": "perfume",
    "Fashion": "fashion",
    "Hair": "hair",
    "Accessories": "accessories",
    "Beauty": "beauty",
    "Other": "beauty",
}


def ensure_style_reference_folders():
    STYLE_REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

    for folder_name in sorted(set(STYLE_REFERENCE_FOLDERS.values())):
        (STYLE_REFERENCE_DIR / folder_name).mkdir(
            parents=True,
            exist_ok=True,
        )


ensure_style_reference_folders()


def get_style_reference_folder(category):
    folder_name = STYLE_REFERENCE_FOLDERS.get(category, "beauty")
    return STYLE_REFERENCE_DIR / folder_name


def get_style_reference_files(category=None):
    """
    With a category: return ONLY that category library.
    Without a category: return all categorized references.
    """
    if category is not None:
        folder = get_style_reference_folder(category)

        if not folder.exists():
            return []

        return sorted([
            path
            for path in folder.iterdir()
            if (
                path.is_file()
                and path.suffix.lower() in STYLE_REFERENCE_EXTENSIONS
            )
        ])

    files = []

    for folder_name in sorted(set(STYLE_REFERENCE_FOLDERS.values())):
        folder = STYLE_REFERENCE_DIR / folder_name

        if not folder.exists():
            continue

        files.extend([
            path
            for path in folder.iterdir()
            if (
                path.is_file()
                and path.suffix.lower() in STYLE_REFERENCE_EXTENSIONS
            )
        ])

    return sorted(files)


def choose_style_references_for_job(job_index, category):
    """
    Every job may ONLY pull from its category's reference folder.
    """
    files = get_style_reference_files(category)

    if not files:
        return {"primary": None, "supporting": []}

    total = len(files)
    primary = files[job_index % total]
    supporting = []

    for idx in (
        (job_index + 7) % total,
        (job_index + 13) % total,
    ):
        candidate = files[idx]

        if candidate != primary and candidate not in supporting:
            supporting.append(candidate)

    return {
        "primary": primary,
        "supporting": supporting,
    }


def category_art_direction(category):
    if category == "Fashion":
        return """
CLOTHING PRODUCT-HERO RULE

The supplied affiliate clothing item is the HERO.

Create beautiful, natural Pinterest outfit inspiration,
NOT a conventional advertisement.

The viewer should immediately understand which clothing item is featured
without arrows, labels, prices, banners, BUY NOW text, or ecommerce graphics.

Style the affiliate item as part of a complete aspirational outfit,
but supporting clothes and accessories must not visually compete.

Use composition, framing, placement, contrast, lighting and styling
to make the featured piece the clearest and most memorable item.

Desired reaction:
"I love THAT piece — where is it from?"
not merely:
"I like this outfit."

Use realistic mannequin or headless-model styling when appropriate,
believable bedroom / vanity / dressing-room environments,
natural fabric behavior, coordinated accessories and soft editorial lighting.

SELL THROUGH STYLING, NOT THROUGH AD GRAPHICS.
""".strip()

    if category == "Perfume":
        return """
FRAGRANCE STORYTELLING RULE

Preserve the exact recognizable bottle and packaging.
Use fragrance notes to inspire atmosphere, materials and restrained props.
Ingredients should feel naturally integrated into the editorial environment,
not arranged as literal icons around the bottle.
The perfume stays the visual hero.
""".strip()

    if category == "Hair":
        return """
HAIR / WIG REALISM RULE

For wigs and hair products preserve intended color, length, density,
texture or curl pattern, parting and recognizable construction.

Create aspirational Pinterest hair imagery with believable strands,
volume, edges and lighting.

Do not beautify a supplied wig into a different hairstyle or product.
""".strip()

    if category == "Accessories":
        return """
ACCESSORY PRODUCT-HERO RULE

Make the supplied bag, shoe, jewelry or accessory the visual hero
inside an aspirational outfit or lifestyle scene.

Supporting pieces may explain how to style the item
but must not visually compete with it.

Avoid catalog layouts, price graphics, arrows and banner-ad styling.
""".strip()

    if category == "Beauty":
        return """
BEAUTY CLICK-IT RULE

Create Pinterest-native beauty discovery imagery designed to earn curiosity
without looking like a conventional advertisement.

Keep the real product central and recognizable.
Do not use fake buttons, arrows, SALE graphics or misleading claims.

The image should make someone want to click for a closer look.
""".strip()

    return """
MAKEUP + SKINCARE EDITORIAL RULE

Preserve the real product exactly while styling it in tactile,
believable beauty photography.

Favor vanities, trays, fabric, mirrors, swatches, glass,
cosmetic texture and layered foreground/background depth
when appropriate to the primary reference.

The product remains the hero.
Avoid generic ecommerce renders.
""".strip()


# =========================
# SESSION STATE
# =========================
defaults = {
    "products": [],
    "pin_jobs": [],
    "imported_images": {},
    "returned_metadata": {},
    "batch_number": 1,
    "current_schedule": [],
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================
# CSS
# =========================
st.markdown("""
<style>
html { color-scheme: light !important; }
body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"] { background-color:#f8dfea!important; color:#4d3040!important; }
.stApp { background-image:linear-gradient(rgba(255,255,255,.25) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.25) 1px,transparent 1px),radial-gradient(circle at 15% 15%,#f3c6da 0 2px,transparent 3px),radial-gradient(circle at 82% 35%,#dfc9f2 0 2px,transparent 3px); background-size:18px 18px,18px 18px,90px 90px,110px 110px; }
.block-container { max-width:1180px; padding-top:1.2rem; padding-bottom:4rem; }
.stApp p,.stApp label,.stApp span,.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6 { color:#4d3040; }
[data-testid="stCaptionContainer"] { color:#755869!important; }
[data-testid="stWidgetLabel"] p { color:#59374a!important; font-weight:800!important; }
.logo { text-align:center; font-size:47px; font-weight:900; color:#9f416a; text-shadow:2px 2px #ffd8e7,4px 4px #eaa2bf; margin-bottom:2px; }
.tagline { text-align:center; font-family:monospace; color:#735064; margin-bottom:24px; }
.desktop { border:3px solid #91415f; background:#fff8fb; box-shadow:6px 6px 0 #e69fbb; margin-bottom:22px; }
.desktop-bar { background:linear-gradient(90deg,#ed91b3,#f2b3cc); border-bottom:3px solid #91415f; padding:8px 13px; font-weight:900; color:#562c40; }
.desktop-menu { padding:10px 13px; font-family:monospace; color:#634052; }
.window { border:3px solid #a94d71; background:#fffafd; box-shadow:5px 5px 0 #edabc4; margin-top:22px; margin-bottom:17px; }
.window-title { background:#efa1bf; border-bottom:3px solid #a94d71; padding:8px 13px; font-weight:900; color:#592d43; }
.stTextInput input,.stTextArea textarea,.stNumberInput input { background:#fffdfd!important; color:#3e2935!important; border:2px solid #cf81a0!important; border-radius:2px!important; }
div[data-baseweb="select"]>div { background:#fffdfd!important; color:#3e2935!important; border-color:#cf81a0!important; }
[data-testid="stFileUploaderDropzone"] { background:#fff9fc!important; border:2px dashed #c87899!important; }
div[data-testid="stButton"] button,div[data-testid="stDownloadButton"] button { background:#ffd1e1!important; color:#5d3046!important; border:2px solid #9f496b!important; border-radius:2px!important; font-weight:900!important; box-shadow:3px 3px 0 #dd8fac!important; }
.product-card,.pin-card { background:#fff8fb; border:2px solid #ce789a; padding:14px; box-shadow:3px 3px 0 #efb6cb; margin-bottom:12px; }
.badge,.keyword { display:inline-block; border:1px solid #c87d9b; background:#ffe5ef; color:#684153; padding:4px 8px; margin:3px; font-size:12px; }
.pin-id { font-family:monospace; font-size:17px; font-weight:900; color:#a03e67; }
.folder-strip { display:flex; justify-content:center; gap:24px; flex-wrap:wrap; font-family:monospace; font-size:13px; margin-bottom:18px; color:#694658; }
.folder-icon { text-align:center; min-width:75px; }
.pixel-row { text-align:center; font-family:monospace; color:#98506e; letter-spacing:6px; margin:10px 0 16px 0; }
.status { background:#ffe5ef; border:2px solid #a95677; box-shadow:3px 3px 0 #eaa8c1; padding:8px 12px; font-family:monospace; margin-top:30px; color:#624052; }
.note-box { background:#fff4f8; border-left:5px solid #df8dab; padding:12px; margin:10px 0; }
.schedule-card { background:#fff7fb; border:1px solid #c97c9b; padding:10px 12px; margin-bottom:8px; font-family:monospace; }
</style>
""", unsafe_allow_html=True)


# =========================
# HELPERS
# =========================
def clean_price(price):
    price = str(price).strip()
    if not price:
        return ""
    if price.startswith("$"):
        return price
    if re.fullmatch(r"\d+(\.\d{1,2})?", price):
        return "$" + price
    return price


def limit_text(text, maximum):
    text = str(text).strip()
    if len(text) <= maximum:
        return text
    shortened = text[:maximum]
    if " " in shortened:
        shortened = shortened.rsplit(" ", 1)[0]
    return shortened.rstrip(" ,.;:-")


def create_pin_id(product_number, pin_number):
    return f"PF_{product_number:03d}_{pin_number:02d}"


def identify_pin_id(filename):
    match = re.search(r"(PF_\d{3}_\d{2})", filename.upper())
    return match.group(1) if match else None



def apply_returned_metadata(results_data):
    """
    Accept multiple reasonable ChatGPT JSON layouts and normalize them.

    Supported examples:
    {"pins": [{"pin_id": "PF_001_01", ...}]}
    {"pins": {"PF_001_01": {...}}}
    {"PF_001_01": {...}, "PF_001_02": {...}}
    [{"pin_id": "PF_001_01", ...}]
    """

    jobs_by_id = {
        job["pin_id"]: job
        for job in st.session_state.pin_jobs
    }

    warnings = []
    normalized = []

    if isinstance(results_data, list):
        raw_pins = results_data
    elif isinstance(results_data, dict):
        raw_pins = results_data.get("pins", results_data)
    else:
        return 0, ["SEO metadata is not a JSON object or list."]

    if isinstance(raw_pins, dict):
        for key, value in raw_pins.items():
            if not str(key).upper().startswith("PF_"):
                continue

            if isinstance(value, dict):
                item = value.copy()
                item.setdefault("pin_id", str(key).upper())
            else:
                item = {
                    "pin_id": str(key).upper(),
                    "seo_title": str(value),
                }

            normalized.append(item)

    elif isinstance(raw_pins, list):
        for value in raw_pins:
            if isinstance(value, dict):
                normalized.append(value)
            elif isinstance(value, str):
                pin_id = identify_pin_id(value)
                if pin_id:
                    normalized.append({
                        "pin_id": pin_id,
                        "seo_title": value,
                    })
                else:
                    warnings.append(
                        "Ignored an unrecognized text entry in SEO metadata."
                    )
            else:
                warnings.append(
                    "Ignored an unsupported SEO metadata entry."
                )
    else:
        return 0, [
            "The SEO metadata exists, but its pin collection has an unsupported format."
        ]

    applied = 0

    for item in normalized:
        if not isinstance(item, dict):
            continue

        pin_id = str(
            item.get(
                "pin_id",
                item.get("id", item.get("pf_id", "")),
            )
        ).upper().strip()

        if pin_id not in jobs_by_id:
            warnings.append(
                f"Unknown metadata ID: {pin_id or 'missing pin_id'}"
            )
            continue

        title = (
            item.get("seo_title")
            or item.get("title")
            or item.get("pinterest_title")
            or ""
        )

        description = (
            item.get("seo_description")
            or item.get("description")
            or item.get("pinterest_description")
            or ""
        )

        keywords = (
            item.get("seo_keywords")
            or item.get("keywords")
            or item.get("search_keywords")
            or []
        )

        title = limit_text(title, 100)
        description = limit_text(description, 800)

        if isinstance(keywords, str):
            keywords = [
                part.strip()
                for part in keywords.split(",")
                if part.strip()
            ]
        elif not isinstance(keywords, list):
            keywords = []

        keywords = [
            str(keyword).strip()
            for keyword in keywords
            if str(keyword).strip()
        ][:10]

        job = jobs_by_id[pin_id]

        if title:
            job["seo_title"] = title
        if description:
            job["seo_description"] = description
        if keywords:
            job["keywords"] = keywords

        st.session_state.returned_metadata[pin_id] = {
            "seo_title": title,
            "seo_description": description,
            "seo_keywords": keywords,
        }

        applied += 1

    if not normalized:
        warnings.append("No recognizable PF metadata entries were found.")

    return applied, warnings


# =========================
# SEO + KEYWORDS
# =========================
def product_search_terms(product):
    name = product["name"].lower()
    category = product["category"]
    if "lip oil" in name:
        return ["lip oil", "glossy lips", "hydrating lip product", "lip combo", "lip makeup"]
    if "lip balm" in name:
        return ["lip balm", "hydrating lip balm", "soft lips", "lip care", "everyday lip product"]
    if "lip gloss" in name or "gloss" in name:
        return ["lip gloss", "glossy lips", "lip combo", "everyday lip makeup", "beauty find"]
    if "blush" in name:
        return ["blush", "pink blush", "cheek makeup", "soft glam makeup", "everyday blush"]
    if "mascara" in name:
        return ["mascara", "lash makeup", "long lashes", "eye makeup", "everyday mascara"]
    if "primer" in name:
        return ["makeup primer", "face primer", "makeup prep", "long lasting makeup", "beauty find"]
    if "setting spray" in name:
        return ["setting spray", "makeup setting spray", "dewy makeup", "long lasting makeup", "makeup must have"]
    if category == "Perfume":
        return ["perfume recommendations", "fragrance finds", "feminine perfume", "perfume aesthetic", "perfume wishlist"]
    if category == "Skincare":
        return ["skincare routine", "skincare finds", "glowing skin", "beauty routine", "skincare products"]
    if category == "Fashion":
        return ["outfit inspiration", "cute outfits", "feminine fashion", "Pinterest outfits", "style inspiration"]
    return ["Pinterest finds", "cute finds", "shopping finds", "aesthetic finds", "wishlist finds"]


def make_title(product, pin_number):
    name = product["name"].strip()
    category = product["category"]
    season = product["season"]
    lead = product_search_terms(product)[0].title()
    variations = [
        f"{name} | {lead} Worth Trying",
        f"{name} | Cute {category} Find",
        f"{name} | Pinterest {category} Inspiration",
    ]
    if season != "None":
        variations.insert(0, f"{name} | Cute {season} {category} Find")
    return limit_text(variations[(pin_number - 1) % len(variations)], 100)


def make_description(product, pin_number):
    name = product["name"].strip()
    category = product["category"]
    season = product["season"]
    notes = product["notes"].strip()
    terms = product_search_terms(product)

    if category in ["Beauty", "Makeup"]:
        description = f"Looking for a {terms[0]} worth adding to your beauty routine? {name} is a cute pick for {terms[1]}, {terms[2]}, and everyday makeup inspiration."
    elif category == "Skincare":
        description = f"Looking for a skincare find to add to your routine? {name} is worth saving for skincare inspiration, glowing skin routines and everyday beauty."
    elif category == "Perfume":
        description = f"If you love discovering new fragrances, save {name}. It fits perfume recommendations, fragrance finds, feminine perfume inspiration and scent wishlists."
    elif category == "Fashion":
        description = f"Save {name} for your next outfit idea. It works well for outfit inspiration, cute outfits, feminine fashion and everyday Pinterest style."
    elif category == "Hair":
        description = f"Looking for a new hair find? Save {name} for haircare inspiration, beauty routines and products worth checking out."
    elif category == "Accessories":
        description = f"Save {name} for your next look. It is a cute accessory find for feminine outfits, Pinterest style and everyday fashion inspiration."
    else:
        description = f"{name} is a Pinterest find worth saving for later. Perfect for wishlists, shopping inspiration and aesthetic finds."

    if season != "None":
        description += f" It also fits {season.lower()} inspiration and seasonal shopping."
    if notes:
        description += f" {notes}"
    endings = [
        " Tap the pin to view the linked product and current details.",
        " Save this idea for later and tap through when you are ready to shop.",
        " Add it to your wishlist and tap the pin to see the product.",
    ]
    description += endings[(pin_number - 1) % len(endings)]
    return limit_text(description, 800)


def make_keywords(product):
    category = product["category"]
    season = product["season"]
    keywords = product_search_terms(product)
    extras = {
        "Beauty": ["beauty finds", "makeup finds", "beauty must haves", "everyday makeup", "Pinterest beauty"],
        "Makeup": ["beauty finds", "makeup finds", "beauty must haves", "everyday makeup", "Pinterest makeup"],
        "Skincare": ["skincare must haves", "beauty finds", "skin care tips", "skincare wishlist", "Pinterest skincare"],
        "Perfume": ["best perfumes", "fragrance inspiration", "perfume collection", "perfume lovers", "Pinterest perfume"],
        "Fashion": ["fashion finds", "everyday outfits", "cute fashion", "fashion wishlist", "Pinterest fashion"],
        "Hair": ["hair products", "haircare routine", "healthy hair", "hair must haves", "Pinterest hair"],
        "Accessories": ["cute accessories", "fashion accessories", "outfit accessories", "fashion finds", "accessory wishlist"],
        "Other": ["Pinterest inspiration", "cute finds", "shopping inspiration", "wishlist ideas", "aesthetic finds"],
    }
    keywords.extend(extras.get(category, extras["Other"]))
    if season != "None":
        keywords.extend([f"{season.lower()} finds", f"{season.lower()} inspiration"])
    unique = []
    for kw in keywords:
        if kw not in unique:
            unique.append(kw)
    for kw in ["Pinterest inspiration", "cute finds", "wishlist ideas", "shopping inspiration", "aesthetic finds"]:
        if len(unique) >= 10:
            break
        if kw not in unique:
            unique.append(kw)
    return unique[:10]


def make_hook(product, pin_number):
    name = product["name"].lower()
    price = product["price"]
    season = product["season"]
    category = product["category"]
    if "lip" in name or "gloss" in name:
        hooks = [f"Cute lip find for {price} ♡" if price else "Your next lip favorite ♡", "Glossy lips, but make it pretty ♡", "Would you add this to your lip combo?"]
    elif "mascara" in name:
        hooks = ["Want longer-looking lashes?", "Mascara worth trying ♡", "Your lashes might love this ♡"]
    elif category == "Perfume":
        hooks = ["Want to smell this good all day?", "A perfume worth smelling ♡", "Your next fragrance obsession?"]
    elif category == "Fashion":
        hooks = ["Would you wear this outfit?", "Cute outfit inspiration ♡", "Adding this to the outfit board ♡"]
    elif season == "Fall":
        hooks = ["Adding this to my fall wishlist 🍂", "A cute fall find ♡", "Fall Pinterest find 🍂"]
    else:
        hooks = [f"Cute find for {price} ♡" if price else "Cute find worth saving ♡", "Would you add this to your wishlist?", "Pinterest find of the day ♡"]
    return hooks[(pin_number - 1) % len(hooks)]


# =========================
# IMAGE PROMPT
# =========================
def make_image_prompt(product, pin_number):
    category = product["category"]
    season = product["season"]
    notes = product["notes"]
    visual = product["visual_direction"]
    base = f"""
Create ONE ultra-high-resolution vertical 2:3 Pinterest image.

PRODUCT: {product['name']}
CATEGORY: {category}
PRODUCT DETAILS: {notes if notes else 'Use the supplied product reference images for visual accuracy.'}

CRITICAL PRODUCT ACCURACY:
Use the supplied reference images. Preserve the recognizable product design, shape, packaging, colors, proportions, cap, applicator, logos, wording and label placement. Do not invent a different product or random branding.

GOAL:
Create a beautiful Pinterest image that looks intentionally styled, not like a product photo pasted onto a template. The product must be the visual hero.
"""
    if category in ["Beauty", "Makeup", "Skincare"]:
        base += """
STYLE:
Clean feminine beauty editorial photography. Realistic cosmetic texture. Soft natural studio lighting. Use ribbons, flowers, fabric, glass, mirrors, trays, pearls or jewelry only when they fit naturally. Do not clutter the scene.
"""
    elif category == "Perfume":
        base += """
STYLE:
Create an atmospheric fragrance editorial scene. Integrate visual elements inspired by the supplied fragrance notes naturally into the environment. Keep the perfume as the hero.
"""
    elif category == "Fashion":
        base += """
STYLE:
Show the clothing as a cohesive wearable outfit. Use a realistic headless model/mannequin or elegant outfit display. Do not show a recognizable face.
"""
    else:
        base += """
STYLE:
Pinterest editorial product photography. Clean, aesthetically pleasing and visually cohesive.
"""
    if season != "None":
        base += f"\nSEASONAL DIRECTION:\nSubtly incorporate {season} atmosphere and styling without overloading the scene.\n"
    if visual:
        base += f"\nUSER VISUAL DIRECTION:\n{visual}\n"

    base += (
        "\nCATEGORY-SPECIFIC ART DIRECTION:\n"
        + category_art_direction(category)
        + "\n"
    )

    base += f"""

VARIATION:
This is visual variation {pin_number}. Create a noticeably different believable composition from other variations. The product may be re-staged or re-oriented, but its identity may not change.

QUALITY:
Photorealistic. Sharp details. Natural shadows. Realistic materials. Balanced composition. Professional Pinterest-ready vertical framing.

NO collage. NO grid. NO watermark. NO random logos. NO gibberish. NO distorted packaging. NO unnecessary text.
"""
    return base.strip()


# =========================
# BUILD JOBS
# =========================
def build_pin_jobs():
    jobs = []
    for product_index, product in enumerate(st.session_state.products, start=1):
        for pin_number in range(1, product["pin_count"] + 1):
            pin_id = create_pin_id(product_index, pin_number)
            jobs.append({
                "pin_id": pin_id,
                "product_id": product["id"],
                "product_number": product_index,
                "pin_number": pin_number,
                "product_name": product["name"],
                "price": product["price"],
                "category": product["category"],
                "season": product["season"],
                "affiliate_url": product["affiliate_url"],
                "hook": make_hook(product, pin_number),
                "seo_title": make_title(product, pin_number),
                "seo_description": make_description(product, pin_number),
                "keywords": make_keywords(product),
                "image_prompt": make_image_prompt(product, pin_number),
                "approved": False,
            })
    for job_index, job in enumerate(jobs):
        selected = choose_style_references_for_job(
            job_index,
            job["category"],
        )

        job["style_reference_folder"] = STYLE_REFERENCE_FOLDERS.get(
            job["category"],
            "beauty",
        )

        job["category_art_direction"] = category_art_direction(
            job["category"]
        )

        job["primary_style_reference"] = (
            selected["primary"].name
            if selected["primary"]
            else None
        )

        job["supporting_style_references"] = [
            path.name
            for path in selected["supporting"]
        ]

    return jobs


# =========================
# BATCH ZIP
# =========================
def create_batch_zip():
    jobs = st.session_state.pin_jobs
    memory = io.BytesIO()
    batch_instructions = """
PIN FACTORY — STRICT PRODUCT ACCURACY AI BATCH

PROCESS THE ENTIRE BATCH. Do not ask to generate one product at a time.
The uploaded product/reference images are the SOURCE OF TRUTH.

CRITICAL PRODUCT PRESERVATION:
Preserve exact packaging shape, cap color, bottle/tube color, proportions, logo, brand name, printed wording, text placement, applicator design and recognizable product details. If regenerating the product would alter these details, preserve the original product pixels instead. Generate the creative around the product — not a new version of the product.

REALISTIC INTEGRATION:
The product must not look pasted into the scene. Match lighting, contact shadows, brightness, color temperature, scale, perspective and reflections while preserving crisp branding.

PRIMARY STYLE REFERENCE:
Every job has ONE primary style reference. It controls scene construction, camera angle, product placement, background environment, surface materials, prop density, lighting, depth of field, layering and photographic mood. Scene structure matters more than simply making everything pink.

SUPPORTING REFERENCES:
Supporting references may influence lighting, props, palette, texture, decorative details and mood, but must not override the primary composition.

FORBIDDEN unless clearly present in the primary reference:
product podiums, circular pedestals, floating rings, giant circles, geometric blobs, abstract arches, empty gradients, sterile advertising sets, infographic layouts, generic ecommerce hero renders, empty white studio scenes, floating products.

PRODUCT-LED COLOR DIRECTION:
Build the surrounding palette to complement and frame the actual product. Do not simply repeat the product's dominant color everywhere. Let the product remain a strong visual color anchor.

POSE VARIATION:
The product reference controls identity, not exact pose. Re-stage naturally: diagonal on fabric, horizontal on a tray, leaning against a prop, slight overhead view, nestled into satin/lace/flowers, off-center crop, vanity placement, decorative dish, handheld when appropriate. Do not always default to upright bottle + upright applicator.

OUTPUT:
Generate exactly ONE final vertical 2:3 image for EACH Pin Factory job.
Do not skip jobs.
Use exact filenames like PF_001_01.png.

============================================================
PINTEREST SEO TITLE + DESCRIPTION — REQUIRED
============================================================

For EVERY Pin Factory job, also create a FINAL Pinterest SEO title and description.

TITLE RULES:
- Maximum 100 characters.
- Accurately identify the actual product.
- Lead with useful searchable wording instead of vague filler.
- Naturally include relevant search phrases a Pinterest shopper may type.
- Make the title appealing to someone who may actually buy the product.
- Do NOT invent product features, materials, ingredients, benefits, shades, or claims.
- Avoid vague filler when a more specific search phrase is available.
- Do NOT keyword-stuff.

DESCRIPTION RULES:
- Maximum 800 characters.
- Accurately describe the actual product using supplied product information and references.
- Naturally weave in multiple HIGHLY RELEVANT Pinterest/search keywords.
- Prioritize product type, shade/color, finish, aesthetic, style, use case, season,
  fragrance family/notes, clothing type, accessory type, etc. ONLY when supported.
- Make the copy useful to a shopper and give a natural reason to click.
- Write normal readable sentences.
- Do NOT dump a keyword list into the description.
- Do NOT invent claims, ingredients, materials, sizes, benefits, or specifications.
- Do NOT use fake urgency, fake reviews, or misleading sales language.
- Do NOT add a block of hashtags at the end.

SEO KEYWORDS:
Also identify up to 10 strong search phrases for each Pin.
These are for Pin Factory's internal SEO data.
They should be specific and relevant, not broad filler.

============================================================
RETURNED METADATA FILE — REQUIRED
============================================================

Alongside the generated images, create ONE JSON file named exactly:

PIN_FACTORY_RESULTS.json

Use this exact structure:

{
  "pins": [
    {
      "pin_id": "PF_001_01",
      "seo_title": "Final Pinterest SEO title here",
      "seo_description": "Final natural SEO description here",
      "seo_keywords": [
        "keyword phrase 1",
        "keyword phrase 2"
      ]
    }
  ]
}

Requirements:
- Include exactly one metadata object for EVERY generated Pin job.
- pin_id MUST exactly match the image filename ID.
- seo_title MUST be 100 characters or fewer.
- seo_description MUST be 800 characters or fewer.
- seo_keywords MUST contain no more than 10 relevant phrases.
- Return the images AND PIN_FACTORY_RESULTS.json together in ONE downloadable ZIP.
""".strip()

    manifest = {
        "pin_factory_version": "0.6",
        "created": datetime.now().isoformat(),
        "product_accuracy_mode": "STRICT",
        "preserve_original_product": True,
        "permanent_style_library": True,
        "style_reference_count": len(get_style_reference_files()),
        "instructions": batch_instructions,
        "expected_return": {
            "images": "One image per pin_id",
            "metadata_file": "PIN_FACTORY_RESULTS.json",
            "single_zip": True,
        },
        "pins": jobs,
    }

    with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as archive:
        style_files = get_style_reference_files()

        archive.writestr(
            "STYLE_REFERENCE_RULES.txt",
            (
                "STYLE REFERENCES = HOW THE WORLD SHOULD LOOK. "
                "PRODUCT REFERENCES = EXACTLY WHAT THE PRODUCT MUST LOOK LIKE. "
                "A Pin Factory job may ONLY use references from its assigned "
                "category folder."
            ),
        )

        for folder_name in sorted(set(STYLE_REFERENCE_FOLDERS.values())):
            folder = STYLE_REFERENCE_DIR / folder_name

            folder_files = sorted([
                path
                for path in folder.iterdir()
                if (
                    path.is_file()
                    and path.suffix.lower() in STYLE_REFERENCE_EXTENSIONS
                )
            ])

            for n, path in enumerate(folder_files, start=1):
                archive.writestr(
                    (
                        f"style_references/{folder_name}/"
                        f"STYLE_{n:02d}"
                        f"{path.suffix.lower()}"
                    ),
                    path.read_bytes(),
                )

        style_lookup = {
            (path.parent.name, path.name): path
            for path in style_files
        }

        product_lookup = {
            p["id"]: p
            for p in st.session_state.products
        }

        for job in jobs:
            job_folder = f"job_style_references/{job['pin_id']}/"

            style_folder = job.get(
                "style_reference_folder",
                "beauty",
            )

            primary_name = job.get(
                "primary_style_reference"
            )

            primary_key = (
                style_folder,
                primary_name,
            )

            if primary_name and primary_key in style_lookup:
                p = style_lookup[primary_key]

                archive.writestr(
                    (
                        job_folder
                        + "PRIMARY_STYLE"
                        + p.suffix.lower()
                    ),
                    p.read_bytes(),
                )

            for n, support_name in enumerate(
                job.get("supporting_style_references", []),
                start=1,
            ):
                support_key = (
                    style_folder,
                    support_name,
                )

                if support_key in style_lookup:
                    p = style_lookup[support_key]

                    archive.writestr(
                        (
                            job_folder
                            + f"SUPPORT_{n:02d}"
                            + p.suffix.lower()
                        ),
                        p.read_bytes(),
                    )

            fallback = f"CHATGPT_FALLBACK/{job['pin_id']}/"
            archive.writestr(fallback + "READ_ME_FIRST.txt", f"PIN ID: {job['pin_id']}\nPRODUCT: {job['product_name']}\nUpload every image in this folder if ChatGPT cannot use references from the full ZIP. PRODUCT_REFERENCE controls exact product identity. PRIMARY_STYLE controls composition. SUPPORT files are secondary inspiration. Generate exactly one final image for this job.")
            product = product_lookup.get(job["product_id"])
            if product:
                for n, image_data in enumerate(product["images"], start=1):
                    ext = os.path.splitext(image_data["name"])[1].lower()
                    if ext not in STYLE_REFERENCE_EXTENSIONS:
                        ext = ".png"
                    archive.writestr(fallback + f"PRODUCT_REFERENCE_{n:02d}" + ext, image_data["bytes"])
            if primary_name and primary_key in style_lookup:
                p = style_lookup[primary_key]

                archive.writestr(
                    (
                        fallback
                        + "PRIMARY_STYLE"
                        + p.suffix.lower()
                    ),
                    p.read_bytes(),
                )

            for n, support_name in enumerate(
                job.get("supporting_style_references", []),
                start=1,
            ):
                support_key = (
                    style_folder,
                    support_name,
                )

                if support_key in style_lookup:
                    p = style_lookup[support_key]

                    archive.writestr(
                        (
                            fallback
                            + f"SUPPORT_{n:02d}"
                            + p.suffix.lower()
                        ),
                        p.read_bytes(),
                    )

        archive.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        archive.writestr("BATCH_INSTRUCTIONS.txt", batch_instructions)

        master = (
            "PIN FACTORY AI BATCH\n\n"
            "Read BATCH_INSTRUCTIONS.txt FIRST. Generate every requested job. "
            "Each finished image must be a separate vertical 2:3 image using the exact PF ID as filename. "
            "You MUST also create PIN_FACTORY_RESULTS.json containing the final SEO title, "
            "SEO description, and up to 10 SEO keyword phrases for EVERY job. "
            "Return all images + PIN_FACTORY_RESULTS.json together in ONE ZIP.\n\n"
        )
        for job in jobs:
            master += (
                f"PIN ID: {job['pin_id']}\n"
                f"PRODUCT: {job['product_name']}\n"
                f"CATEGORY: {job['category']}\n"
                f"PRICE: {job['price']}\n"
                f"SEASON: {job['season']}\n"
                f"HOOK IDEA: {job['hook']}\n"
                f"STYLE REFERENCE FOLDER: {job.get('style_reference_folder')}\n"
                f"CATEGORY ART DIRECTION:\n"
                f"{job.get('category_art_direction', '')}\n"
                f"PRIMARY STYLE REFERENCE: {job.get('primary_style_reference')}\n"
                f"SUPPORTING STYLE REFERENCES: "
                f"{', '.join(job.get('supporting_style_references', []))}\n"
                f"IMAGE DIRECTION:\n{job['image_prompt']}\n"
                f"PRODUCT ACCURACY: STRICT\n"
                + "=" * 60
                + "\n"
            )
        archive.writestr("GENERATE_THIS_BATCH.txt", master)

        for product_index, product in enumerate(st.session_state.products, start=1):
            folder = f"references/product_{product_index:03d}/"
            info = {k: product[k] for k in ["name", "price", "category", "season", "notes", "visual_direction", "affiliate_url"]}
            info["product_number"] = product_index
            info["product_accuracy"] = "STRICT"
            info["preserve_original_product"] = True
            archive.writestr(folder + "product_info.json", json.dumps(info, indent=2, ensure_ascii=False))
            for n, image_data in enumerate(product["images"], start=1):
                ext = os.path.splitext(image_data["name"])[1].lower()
                if ext not in STYLE_REFERENCE_EXTENSIONS:
                    ext = ".png"
                archive.writestr(folder + f"reference_{n:02d}" + ext, image_data["bytes"])

    memory.seek(0)
    return memory.getvalue()


# =========================
# SCHEDULER
# =========================
INTERVAL = 30

def time_to_minutes(value):
    return value.hour * 60 + value.minute

def snap_up(value):
    rem = value % INTERVAL
    return value if rem == 0 else value + INTERVAL - rem

def snap_down(value):
    return (value // INTERVAL) * INTERVAL

def minutes_to_time(value):
    value = max(0, min(value, 23*60+30))
    return time(value // 60, value % 60)

def available_slots(start_time, end_time):
    start = snap_up(time_to_minutes(start_time))
    end = snap_down(time_to_minutes(end_time))
    return [] if end < start else list(range(start, end + 1, INTERVAL))

def reorder_jobs(jobs):
    remaining = jobs.copy(); random.shuffle(remaining); ordered = []
    while remaining:
        if not ordered:
            ordered.append(remaining.pop(0)); continue
        prev = ordered[-1].get("product_id")
        idx = next((i for i, j in enumerate(remaining) if j.get("product_id") != prev), None)
        ordered.append(remaining.pop(idx if idx is not None else 0))
    return ordered

def schedule_times(selected_date, count, start_time, end_time, mode):
    slots = available_slots(start_time, end_time)
    if count <= 0 or count > len(slots):
        return []
    if count == 1:
        chosen = [random.choice(slots) if mode == "Smart Spread" else slots[len(slots)//2]]
    elif mode == "Evenly Spaced":
        chosen = [slots[round(i*(len(slots)-1)/(count-1))] for i in range(count)]
        chosen = sorted(set(chosen))
        for slot in slots:
            if len(chosen) >= count: break
            if slot not in chosen: chosen.append(slot)
        chosen.sort()
    else:
        chosen = []
        for i in range(count):
            a = int(i*len(slots)/count); b = int((i+1)*len(slots)/count)
            zone = slots[a:b]
            if zone: chosen.append(random.choice(zone))
        chosen = sorted(set(chosen))
        remaining = [s for s in slots if s not in chosen]; random.shuffle(remaining)
        while len(chosen) < count and remaining: chosen.append(remaining.pop())
        chosen.sort()
    return [datetime.combine(selected_date, minutes_to_time(s)) for s in chosen[:count]]

def create_schedule(jobs, selected_date, count, start_time, end_time, mode, avoid_same_product):
    count = min(int(count), len(jobs))
    selected = reorder_jobs(jobs)[:count] if avoid_same_product else random.sample(jobs, count)
    times = schedule_times(selected_date, count, start_time, end_time, mode)
    if len(times) != count:
        return []
    result = []
    for job, dt in zip(selected, times):
        item = job.copy()
        item["scheduled_datetime"] = dt.isoformat()
        item["scheduled_date"] = dt.strftime("%Y-%m-%d")
        item["scheduled_time"] = dt.strftime("%I:%M %p")
        result.append(item)
    return result


# =========================
# HEADER
# =========================
st.markdown('<div class="logo">🎀 PIN FACTORY.exe</div>', unsafe_allow_html=True)
st.markdown('<div class="tagline">♡ affiliate pin production system — v0.6 ♡</div>', unsafe_allow_html=True)
st.markdown("""
<div class="desktop"><div class="desktop-bar">♡ PINFACTORY_DESKTOP <span style="float:right;">— &nbsp; □ &nbsp; ×</span></div><div class="desktop-menu">File &nbsp;&nbsp; Products &nbsp;&nbsp; AI Batch &nbsp;&nbsp; Import &nbsp;&nbsp; Pinterest &nbsp;&nbsp; Schedule &nbsp;&nbsp; Help</div></div>
<div class="folder-strip"><div class="folder-icon">📁<br>products</div><div class="folder-icon">💾<br>ai_batch</div><div class="folder-icon">🖼️<br>generated</div><div class="folder-icon">📌<br>pinterest</div><div class="folder-icon">🗓️<br>schedule</div></div>
<div class="pixel-row">♡ ▪ ♡ ▪ ♡ ▪ ♡ ▪ ♡</div>
""", unsafe_allow_html=True)


# =========================
# CATEGORY REFERENCE LIBRARIES
# =========================

st.markdown(
    """
<div class="window">
    <div class="window-title">
        🎀 REFERENCE_STUDIOS.folder
    </div>
</div>
""",
    unsafe_allow_html=True,
)

reference_studios = [
    ("💄 Makeup + Skincare", "Makeup", "makeup_skincare"),
    ("🫧 Perfume", "Perfume", "perfume"),
    ("👗 Fashion", "Fashion", "fashion"),
    ("🎀 Hair", "Hair", "hair"),
    ("👜 Accessories", "Accessories", "accessories"),
    ("✨ Beauty / Click-It", "Beauty", "beauty"),
]

studio_columns = st.columns(3)

for studio_index, (
    studio_label,
    studio_category,
    studio_folder,
) in enumerate(reference_studios):

    refs = get_style_reference_files(
        studio_category
    )

    with studio_columns[
        studio_index % 3
    ]:
        st.markdown(
            f"""
<div class="product-card">
    <b>{studio_label}</b><br><br>
    <span class="badge">{len(refs)} reference(s)</span>
    <span class="badge">{studio_folder}/</span>
</div>
""",
            unsafe_allow_html=True,
        )


# =========================
# NEW PRODUCT
# =========================
st.markdown('<div class="window"><div class="window-title">📁 NEW_PRODUCT.exe</div></div>', unsafe_allow_html=True)
with st.form("new_product", clear_on_submit=True):
    left, right = st.columns(2)
    with left:
        name = st.text_input("Product name")
        price = st.text_input("Price", placeholder="14 or $14")
        category = st.selectbox("Category", ["Beauty", "Makeup", "Skincare", "Perfume", "Fashion", "Hair", "Accessories", "Other"])
        pin_count = st.number_input("Number of pins", min_value=1, max_value=10, value=2, step=1)
    with right:
        affiliate_url = st.text_input("Affiliate URL")
        season = st.selectbox("Season / occasion", ["None", "Fall", "Halloween", "Thanksgiving", "Christmas", "Winter", "Valentine's Day", "Spring", "Summer", "Back to School"])
        notes = st.text_area("Product details", placeholder="Describe finish, texture, benefits, fragrance notes, clothing details, etc.", height=100)
        visual_direction = st.text_area("Visual direction", placeholder="Optional: coquette vanity, cream satin, soft pink accents, no hands...", height=100)
    uploads = st.file_uploader("Product/reference images", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
    add = st.form_submit_button("♡ ADD PRODUCT")
    if add:
        if not name.strip(): st.error("Enter a product name.")
        elif not affiliate_url.strip(): st.error("Enter the affiliate URL.")
        elif not uploads: st.error("Upload at least one product/reference image.")
        else:
            stored_images = [{"id": str(uuid.uuid4()), "name": u.name, "bytes": u.getvalue()} for u in uploads]
            st.session_state.products.append({"id": str(uuid.uuid4()), "name": name.strip(), "price": clean_price(price), "category": category, "season": season, "notes": notes.strip(), "visual_direction": visual_direction.strip(), "affiliate_url": affiliate_url.strip(), "pin_count": int(pin_count), "images": stored_images})
            st.session_state.pin_jobs = []; st.session_state.imported_images = {}; st.session_state.current_schedule = []
            st.success(f"{name.strip()} added ♡")


# =========================
# PRODUCT LIBRARY
# =========================
st.markdown('<div class="window"><div class="window-title">📂 PRODUCTS.folder</div></div>', unsafe_allow_html=True)
if not st.session_state.products:
    st.info("No products yet.")
else:
    for product_number, product in enumerate(list(st.session_state.products), start=1):
        st.markdown(f'<div class="product-card"><b>PRODUCT_{product_number:03d} ♡ {product["name"]}</b><br><br><span class="badge">{product["price"] or "no price"}</span><span class="badge">{product["category"]}</span><span class="badge">{product["season"]}</span><span class="badge">{product["pin_count"]} pin(s)</span></div>', unsafe_allow_html=True)
        info, actions = st.columns([3,1])
        with info:
            st.caption("Affiliate URL"); st.code(product["affiliate_url"])
            if product["notes"]: st.write("**Details:**", product["notes"])
            if product["visual_direction"]: st.write("**Visual direction:**", product["visual_direction"])
        with actions:
            if st.button("🗑 Delete product", key=f'delete_{product["id"]}'):
                st.session_state.products = [x for x in st.session_state.products if x["id"] != product["id"]]
                st.session_state.pin_jobs = []; st.session_state.imported_images = {}; st.session_state.current_schedule = []; st.rerun()
        if product["images"]:
            cols = st.columns(min(4, len(product["images"])))
            for index, image_data in enumerate(list(product["images"])):
                with cols[index % len(cols)]:
                    st.image(image_data["bytes"], width="stretch")
                    if st.button("Remove", key=f'remove_{image_data["id"]}'):
                        product["images"] = [img for img in product["images"] if img["id"] != image_data["id"]]
                        st.session_state.pin_jobs = []; st.session_state.imported_images = {}; st.session_state.current_schedule = []; st.rerun()
        st.divider()


# =========================
# AI BATCH
# =========================
st.markdown('<div class="window"><div class="window-title">✨ AI_BATCH.exe</div></div>', unsafe_allow_html=True)
st.markdown('<div class="note-box"><b>How V0.6 works:</b><br>1. Build the AI batch.<br>2. Download the ZIP.<br>3. Upload it to ChatGPT for image + SEO generation.<br>4. Import the ONE results ZIP returned by ChatGPT.<br>5. Approve finished pins.<br>6. Use AUTO SCHEDULER.exe.</div>', unsafe_allow_html=True)
if st.button("🪄 BUILD AI BATCH", key="build_batch"):
    if not st.session_state.products: st.error("Add at least one product first.")
    else:
        st.session_state.pin_jobs = build_pin_jobs(); st.session_state.imported_images = {}; st.session_state.current_schedule = []
        st.success(f'{len(st.session_state.pin_jobs)} AI pin job(s) prepared ♡')


# =========================
# BATCH REVIEW
# =========================
if st.session_state.pin_jobs:
    st.markdown('<div class="window"><div class="window-title">💾 BATCH_PREVIEW.folder</div></div>', unsafe_allow_html=True)
    for job in st.session_state.pin_jobs:
        st.markdown(f'<div class="pin-card"><div class="pin-id">{job["pin_id"]}</div><b>{job["product_name"]}</b></div>', unsafe_allow_html=True)
        left, right = st.columns(2)
        with left:
            edited_hook = st.text_input("Hook", value=job["hook"], key=f'hook_{job["pin_id"]}')
            edited_title = st.text_input("SEO title", value=job["seo_title"], max_chars=100, key=f'title_{job["pin_id"]}')
            st.caption(f'{len(edited_title)}/100 characters')
            edited_desc = st.text_area("SEO description", value=job["seo_description"], max_chars=800, height=180, key=f'desc_{job["pin_id"]}')
            st.caption(f'{len(edited_desc)}/800 characters')
        with right:
            st.write("**10 Pinterest keywords**")
            st.markdown("".join(f'<span class="keyword">{kw}</span>' for kw in job["keywords"]), unsafe_allow_html=True)
            with st.expander("View AI image prompt"):
                st.text_area("Prompt", value=job["image_prompt"], height=330, key=f'prompt_{job["pin_id"]}')
            st.caption("Affiliate URL"); st.code(job["affiliate_url"])
        job["hook"] = edited_hook; job["seo_title"] = limit_text(edited_title, 100); job["seo_description"] = limit_text(edited_desc, 800)
        st.divider()

    batch_zip = create_batch_zip()
    st.download_button("📦 EXPORT AI BATCH", data=batch_zip, file_name="pin_factory_ai_batch_" + datetime.now().strftime("%Y%m%d_%H%M") + ".zip", mime="application/zip", key="export_batch")
    st.caption("Upload this ZIP to ChatGPT. ChatGPT should return ONE ZIP containing the PF images plus PIN_FACTORY_RESULTS.json.")


# =========================
# IMPORT CHATGPT RESULTS
# =========================
st.markdown(
    '<div class="window"><div class="window-title">🖼️ IMPORT_CHATGPT_RESULTS.folder</div></div>',
    unsafe_allow_html=True,
)

if not st.session_state.pin_jobs:
    st.caption("Build an AI batch first.")

else:
    st.markdown(
        """
<div class="note-box">
<b>Preferred:</b> Upload the ONE ZIP returned by ChatGPT.
Pin Factory will import the generated images and automatically replace
the draft SEO title, description, and keywords with the final values from
<code>PIN_FACTORY_RESULTS.json</code>.
</div>
""",
        unsafe_allow_html=True,
    )

    results_zip = st.file_uploader(
        "Upload ChatGPT results ZIP",
        type=["zip"],
        accept_multiple_files=False,
        key="chatgpt_results_zip",
    )

    if results_zip is not None:
        try:
            zip_buffer = io.BytesIO(
                results_zip.getvalue()
            )

            valid_ids = {
                job["pin_id"]
                for job in st.session_state.pin_jobs
            }

            matched_images = 0
            unmatched_images = []
            metadata_found = False
            metadata_applied = 0
            metadata_warnings = []

            with zipfile.ZipFile(
                zip_buffer,
                "r",
            ) as result_archive:

                member_names = (
                    result_archive.namelist()
                )

                for member_name in member_names:
                    if member_name.endswith("/"):
                        continue

                    filename = os.path.basename(
                        member_name
                    )

                    extension = os.path.splitext(
                        filename
                    )[1].lower()

                    if extension not in {
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".webp",
                    }:
                        continue

                    pin_id = identify_pin_id(
                        filename
                    )

                    if (
                        pin_id
                        and pin_id in valid_ids
                    ):
                        st.session_state.imported_images[
                            pin_id
                        ] = {
                            "name": filename,
                            "bytes": result_archive.read(
                                member_name
                            ),
                        }

                        matched_images += 1

                    else:
                        unmatched_images.append(
                            filename
                        )

                result_json_member = next(
                    (
                        name
                        for name in member_names
                        if os.path.basename(
                            name
                        ).upper()
                        == "PIN_FACTORY_RESULTS.JSON"
                    ),
                    None,
                )

                if result_json_member:
                    metadata_found = True

                    raw_json = result_archive.read(
                        result_json_member
                    ).decode(
                        "utf-8"
                    )

                    results_data = json.loads(
                        raw_json
                    )

                    (
                        metadata_applied,
                        metadata_warnings,
                    ) = apply_returned_metadata(
                        results_data
                    )

            st.success(
                f"{matched_images} image(s) matched automatically ♡"
            )

            if metadata_found:
                st.success(
                    f"ChatGPT SEO metadata applied to "
                    f"{metadata_applied} pin(s) ♡"
                )
            else:
                st.warning(
                    "The ZIP did not contain PIN_FACTORY_RESULTS.json. "
                    "Images were imported, but the draft Pin Factory SEO text was kept."
                )

            if unmatched_images:
                st.warning(
                    "Could not match image file(s): "
                    + ", ".join(
                        unmatched_images
                    )
                )

            if metadata_warnings:
                st.warning(
                    "Metadata notes: "
                    + " | ".join(
                        metadata_warnings
                    )
                )

        except zipfile.BadZipFile:
            st.error(
                "That file is not a readable ZIP."
            )

        except json.JSONDecodeError:
            st.warning(
                "The images can still be used, but PIN_FACTORY_RESULTS.json "
                "contains invalid JSON, so Pin Factory kept the existing SEO copy."
            )

        except Exception as error:
            st.warning(
                "The images were processed, but Pin Factory could not read the "
                "returned SEO metadata. Existing SEO copy was kept. "
                f"Technical detail: {error}"
            )

    with st.expander(
        "Manual fallback: upload individual generated images"
    ):
        st.caption(
            "Use this only if ChatGPT did not return one ZIP."
        )

        finished_files = st.file_uploader(
            "Upload individual finished images",
            type=[
                "png",
                "jpg",
                "jpeg",
                "webp",
            ],
            accept_multiple_files=True,
            key="finished_ai_images_manual",
        )

        if finished_files:
            valid_ids = {
                job["pin_id"]
                for job in st.session_state.pin_jobs
            }

            matched = 0
            unmatched = []

            for file in finished_files:
                pin_id = identify_pin_id(
                    file.name
                )

                if (
                    pin_id
                    and pin_id in valid_ids
                ):
                    st.session_state.imported_images[
                        pin_id
                    ] = {
                        "name": file.name,
                        "bytes": file.getvalue(),
                    }

                    matched += 1

                else:
                    unmatched.append(
                        file.name
                    )

            st.success(
                f"{matched} image(s) matched automatically ♡"
            )

            if unmatched:
                st.warning(
                    "Could not match: "
                    + ", ".join(
                        unmatched
                    )
                )


# =========================
# FINAL REVIEW + APPROVAL
# =========================
if st.session_state.pin_jobs and st.session_state.imported_images:
    st.markdown('<div class="window"><div class="window-title">📌 FINAL_PINS.folder</div></div>', unsafe_allow_html=True)
    for job in st.session_state.pin_jobs:
        pin_id = job["pin_id"]
        if pin_id not in st.session_state.imported_images: continue
        image_data = st.session_state.imported_images[pin_id]
        left, right = st.columns([1,1.2])
        with left: st.image(image_data["bytes"], width="stretch")
        with right:
            st.markdown(
                f"### {pin_id}"
            )

            st.write(
                f'**{job["product_name"]}**'
            )

            if (
                pin_id
                in st.session_state.returned_metadata
            ):
                st.success(
                    "✨ SEO copy imported from ChatGPT"
                )
            else:
                st.caption(
                    "Using Pin Factory draft SEO copy"
                )

            st.write(
                "**Title:**",
                job["seo_title"],
            )

            st.write(
                "**Description:**",
                job["seo_description"],
            )

            st.write(
                "**Keywords:**",
                ", ".join(
                    job["keywords"]
                ),
            )

            st.caption(
                "Destination URL"
            )

            st.code(
                job["affiliate_url"]
            )

            job["approved"] = st.toggle(
                "Approve for scheduling",
                value=bool(
                    job.get(
                        "approved",
                        False,
                    )
                ),
                key=f'approve_{pin_id}',
            )
        st.divider()


# =========================
# AUTO SCHEDULER
# =========================
approved = [job for job in st.session_state.pin_jobs if job.get("approved")]
st.markdown('<div class="window"><div class="window-title">♡ AUTO SCHEDULER.exe</div></div>', unsafe_allow_html=True)
if not approved:
    st.info("Approve at least one imported pin first. Only pins marked 'Approve for scheduling' appear here.")
else:
    st.success(f"{len(approved)} approved pin(s) ready for scheduling ♡")
    c1, c2 = st.columns(2)
    with c1:
        schedule_date = st.date_input("📅 Day to schedule", value=date.today()+timedelta(days=1), key="v05_schedule_date")
        schedule_count = st.number_input("📌 Pins to schedule this day", min_value=1, max_value=len(approved), value=min(10,len(approved)), step=1, key="v05_schedule_pin_count")
    with c2:
        schedule_start = st.time_input("🌤️ Start posting", value=time(10,0), step=1800, key="v05_schedule_start")
        schedule_end = st.time_input("🌙 Stop posting", value=time(21,30), step=1800, key="v05_schedule_end")
    schedule_mode = st.radio("Timing style", ["Smart Spread", "Evenly Spaced"], horizontal=True, key="v05_schedule_mode")
    avoid_same = st.checkbox("Avoid the same product back-to-back", value=True, key="v05_avoid_same_product")
    slots = available_slots(schedule_start, schedule_end)
    if not slots:
        st.error("Your stop time must be later than your start time.")
    elif schedule_count > len(slots):
        st.error(f"You selected {schedule_count} pins, but this window only contains {len(slots)} available 30-minute slots.")
    else:
        b1, b2 = st.columns(2)
        with b1: build_clicked = st.button("♡ BUILD SCHEDULE", use_container_width=True, key="v05_build_schedule")
        with b2: reshuffle_clicked = st.button("↻ RESHUFFLE", use_container_width=True, key="v05_reshuffle_schedule")
        if build_clicked or reshuffle_clicked:
            new_schedule = create_schedule(approved, schedule_date, schedule_count, schedule_start, schedule_end, schedule_mode, avoid_same)
            if new_schedule:
                st.session_state.current_schedule = new_schedule; st.success(f"Schedule built for {schedule_date.strftime('%B %d, %Y')} ♡")
            else: st.error("Pin Factory could not build this schedule. Try a longer posting window or fewer pins.")


# =========================
# SCHEDULE PREVIEW + EXPORT
# =========================
if st.session_state.current_schedule:
    current = st.session_state.current_schedule
    st.markdown("### 🖥️ SCHEDULE PREVIEW")
    for item in current:
        st.markdown(f'<div class="schedule-card"><strong>{item.get("scheduled_time","")}</strong>&nbsp; │ &nbsp;{item.get("pin_id","")}&nbsp; │ &nbsp;{item.get("product_name","")}&nbsp; │ &nbsp;{item.get("category","")}</div>', unsafe_allow_html=True)
    export = {"pin_factory_version":"0.5", "schedule_date":current[0].get("scheduled_date"), "timezone_note":"Times are local to the Pin Factory user.", "interval_minutes":30, "pin_count":len(current), "pins":current}
    schedule_json = json.dumps(export, indent=2, ensure_ascii=False)
    st.download_button("💾 DOWNLOAD SCHEDULE", data=schedule_json, file_name="pin_factory_schedule_" + current[0].get("scheduled_date","schedule") + ".json", mime="application/json", use_container_width=True, key="v05_download_schedule")


st.markdown('<div class="note-box">Pinterest publishing is still OFF in V0.6. V0.5 prepares approved pins and scheduled times. Pinterest OAuth/publishing can be added after API access is available.</div>', unsafe_allow_html=True)

approved = [job for job in st.session_state.pin_jobs if job.get("approved")]
st.markdown(f'<div class="status">♡ PRODUCTS: {len(st.session_state.products)} &nbsp; | &nbsp; AI JOBS: {len(st.session_state.pin_jobs)} &nbsp; | &nbsp; IMAGES IMPORTED: {len(st.session_state.imported_images)} &nbsp; | &nbsp; APPROVED: {len(approved)} &nbsp; | &nbsp; SCHEDULED: {len(st.session_state.current_schedule)} &nbsp; | &nbsp; PINTEREST: OFFLINE &nbsp; | &nbsp; VERSION: 0.6</div>', unsafe_allow_html=True)
