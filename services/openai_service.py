"""Context-aware OpenAI content generation service."""
import json
from openai import OpenAI


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
) -> str:
    """Generate SEO content using GPT-4 with full client context."""
    client = OpenAI(api_key=api_key)

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

    response = client.chat.completions.create(
        model='gpt-4',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        max_tokens=2000,
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
