"""Context-aware OpenAI content generation service."""
import json
from openai import OpenAI

# Color scheme definitions used in the HTML5 landing page prompt
_COLOR_SCHEMES = {
    'dark_barbershop': 'Dark barbershop aesthetic: black background (#0d0d0d), gold accents (#c9a84c), white text (#ffffff)',
    'corporate_blue': 'Corporate professional: deep navy (#0a1628), blue accents (#1e88e5), white text (#ffffff)',
    'modern_green': 'Modern and fresh: dark green (#0d2818), emerald accents (#00c853), white text (#ffffff)',
    'medical_white': 'Clean medical: white background (#ffffff), teal accents (#00897b), dark text (#212121)',
}

# Layout definitions
_PAGE_LAYOUTS = {
    'hero_features': 'Hero section + Features grid + CTA',
    'landing_page': 'Full landing page with all sections',
    'local_seo_hub': 'Local SEO hub with service areas and schema',
}


def generate_content(
    client_name: str,
    business_type: str,
    niche: str,
    location: str,
    target_keywords: str,
    content_type: str = 'article',
    tone: str = 'professional',
    extra_context: str = '',
    api_key: str = '',
    phone: str = '',
    website: str = '',
    youtube_shorts: str = '',
    subscriber_count: str = '',
    client_photo: str = '',
    video_bg: str = '',
    color_scheme: str = 'dark_barbershop',
    page_layout: str = 'landing_page',
) -> str:
    """Generate SEO content using GPT-4 with full client context.

    When content_type is 'html5_landing_page' a complete, self-contained HTML5
    document is returned.  For all other content types the legacy HTML-fragment
    behaviour is preserved so that existing functionality is unaffected.
    """
    openai_client = OpenAI(api_key=api_key)

    if content_type == 'html5_landing_page':
        return _generate_html5_landing_page(
            openai_client=openai_client,
            client_name=client_name,
            business_type=business_type,
            niche=niche,
            location=location,
            target_keywords=target_keywords,
            phone=phone,
            website=website,
            youtube_shorts=youtube_shorts,
            subscriber_count=subscriber_count,
            client_photo=client_photo,
            video_bg=video_bg,
            color_scheme=color_scheme,
            page_layout=page_layout,
            extra_context=extra_context,
        )

    # ── Legacy HTML-fragment path ──────────────────────────────────────────
    system_prompt = (
        f"You are writing content for a {business_type} named {client_name} located in {location}. "
        f"This is a {niche} business. "
        f"Write content that is SPECIFICALLY relevant to this business — use terminology, concerns, "
        f"and language appropriate for a {niche}. "
        f"Do NOT use generic marketing or corporate language unless this is explicitly a marketing "
        f"or corporate client. "
        f"Tone: {tone}. Write in valid HTML with proper headings, paragraphs and lists."
    )

    user_prompt = (
        f"Create a {content_type.replace('_', ' ')} for {client_name}, a {business_type} in {location}.\n"
        f"Business niche: {niche}\n"
        f"Target keywords to incorporate naturally: {target_keywords}\n"
    )
    if extra_context:
        user_prompt += f"Additional context: {extra_context}\n"
    user_prompt += (
        "\nRequirements:\n"
        "- Use the target keywords naturally throughout the content\n"
        "- Include a compelling headline (H1)\n"
        "- Use subheadings (H2, H3) to organise sections\n"
        "- Write at least 800 words\n"
        "- Include a clear call-to-action relevant to the business\n"
        "- Make the content genuinely useful and informative for the target audience\n"
    )

    response = openai_client.chat.completions.create(
        model='gpt-4',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        max_tokens=2000,
        temperature=0.7,
    )
    return response.choices[0].message.content


def _generate_html5_landing_page(
    openai_client,
    client_name: str,
    business_type: str,
    niche: str,
    location: str,
    target_keywords: str,
    phone: str = '',
    website: str = '',
    youtube_shorts: str = '',
    subscriber_count: str = '',
    client_photo: str = '',
    video_bg: str = '',
    color_scheme: str = 'dark_barbershop',
    page_layout: str = 'landing_page',
    extra_context: str = '',
) -> str:
    """Generate a complete, self-contained HTML5 landing page."""
    color_desc = _COLOR_SCHEMES.get(color_scheme, _COLOR_SCHEMES['dark_barbershop'])
    layout_desc = _PAGE_LAYOUTS.get(page_layout, _PAGE_LAYOUTS['landing_page'])

    shorts_list = [s.strip() for s in youtube_shorts.splitlines() if s.strip()] if youtube_shorts else []
    shorts_block = '\n'.join(shorts_list) if shorts_list else 'None'

    system_prompt = f"""You are an elite web developer and SEO specialist building a premium HTML5 landing page.

Client: {client_name}
Business Type: {business_type}
Niche: {niche}
Location: {location}
Phone: {phone or 'Not provided'}
Website: {website or 'Not provided'}
Target Keywords: {target_keywords}
YouTube Shorts: {shorts_block}
Subscriber Count: {subscriber_count or 'Not provided'}
Client Photo URL: {client_photo or 'Not provided'}
Video Background URL: {video_bg or 'Not provided'}
Color Scheme: {color_desc}
Layout: {layout_desc}
{('Additional context: ' + extra_context) if extra_context else ''}

Generate a COMPLETE, self-contained HTML5 page (no external CSS files, all styles inline in <style> tag).
The page must look premium and professional — like a $5,000 agency website.

Required sections (based on layout '{page_layout}'):
- Sticky navigation bar (dark, with logo/name + CTA button). Add inline JS to change background on scroll.
- Hero section: full-viewport height (100vh), {'video background using the provided Video Background URL with a dark overlay (rgba(0,0,0,0.6))' if video_bg else 'dark gradient background with overlay'}, {'circular client photo using the provided Client Photo URL' if client_photo else 'decorative placeholder'}, H1 with primary keyword, subheadline, two CTA buttons (Book Now + Call Now){(', YouTube subscriber count badge showing ' + subscriber_count) if subscriber_count else ''}
- Services section: CSS Grid, icon cards with hover effects
- About/Trust section: photo left, text right — {'mention ' + subscriber_count + ' YouTube subscribers as social proof' if subscriber_count else 'trust signals'}
{('- YouTube Shorts section: embedded iframes in a responsive grid for these URLs:\n' + shorts_block) if shorts_list else ''}
- Testimonials section: 3 professionally styled placeholder review cards
- Service area / Local SEO section: mentions target cities and neighborhoods in {location}
- Contact / Booking CTA section: {'phone number ' + phone + ' prominent' if phone else 'contact form placeholder'}, booking form placeholder
- Footer: NAP (Name, Address, Phone), links, copyright

Technical requirements:
- Full <!DOCTYPE html> document with <head> containing meta charset, viewport, description, OG tags, Twitter Card tags
- LocalBusiness JSON-LD schema injected from client data
- Google Fonts loaded via <link> (Montserrat for headings, Open Sans for body)
- CSS custom properties (variables) for the color scheme
- Smooth scroll behavior
- Box shadows on cards
- Gradient buttons with hover transitions
- Mobile-first responsive design with media queries
- Hamburger nav on mobile, stacked grid on small screens
- CSS animations: fade-in on scroll (use IntersectionObserver), hover effects on cards and buttons

Output ONLY the complete HTML document. No explanation, no markdown, no code fences."""

    user_prompt = (
        f"Build the complete HTML5 landing page for {client_name}, a {business_type} in {location}. "
        f"Target keywords: {target_keywords}. "
        f"Do NOT generate placeholder lorem ipsum — write real, keyword-rich content specific to this exact business. "
        f"Do NOT use generic marketing language like 'ROI' or 'synergy'. "
        f"Output ONLY the HTML document."
    )

    response = openai_client.chat.completions.create(
        model='gpt-4',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        max_tokens=4096,
        temperature=0.7,
    )
    return response.choices[0].message.content


def generate_schema_markup(client_data: dict) -> str:
    """Generate LocalBusiness JSON-LD schema markup."""
    schema = {
        '@context': 'https://schema.org',
        '@type': 'LocalBusiness',
        'name': client_data.get('name', ''),
        'description': f"{client_data.get('business_type', '')} serving {client_data.get('location', '')}",
        'address': {
            '@type': 'PostalAddress',
            'addressLocality': client_data.get('location', ''),
        },
    }
    if client_data.get('phone'):
        schema['telephone'] = client_data['phone']
    if client_data.get('website'):
        schema['url'] = client_data['website']

    return f'<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>'
