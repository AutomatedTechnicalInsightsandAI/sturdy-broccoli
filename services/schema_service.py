"""LocalBusiness JSON-LD schema generator."""
import json


def generate_local_business_schema(client_data: dict) -> str:
    """Return a <script> tag containing LocalBusiness JSON-LD markup."""
    schema = {
        '@context': 'https://schema.org',
        '@type': 'LocalBusiness',
        'name': client_data.get('name', ''),
        'description': (
            f"{client_data.get('business_type', '')} serving {client_data.get('location', '')}"
        ),
        'address': {
            '@type': 'PostalAddress',
            'addressLocality': client_data.get('location', ''),
            'addressCountry': 'US',
        },
    }
    if client_data.get('phone'):
        schema['telephone'] = client_data['phone']
    if client_data.get('website'):
        schema['url'] = client_data['website']
    if client_data.get('niche'):
        schema['@type'] = _niche_to_schema_type(client_data['niche'])

    return f'<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>'


def _niche_to_schema_type(niche: str) -> str:
    niche_lower = niche.lower()
    mapping = {
        'restaurant': 'Restaurant',
        'dentist': 'Dentist',
        'dental': 'Dentist',
        'lawyer': 'LegalService',
        'legal': 'LegalService',
        'plumber': 'Plumber',
        'plumbing': 'Plumber',
        'electrician': 'Electrician',
        'doctor': 'Physician',
        'medical': 'MedicalBusiness',
        'hotel': 'Hotel',
        'gym': 'ExerciseGym',
        'fitness': 'ExerciseGym',
        'real estate': 'RealEstateAgent',
        'salon': 'HairSalon',
        'hair': 'HairSalon',
        'spa': 'DaySpa',
        'auto': 'AutoRepair',
        'car': 'AutoDealer',
    }
    for key, schema_type in mapping.items():
        if key in niche_lower:
            return schema_type
    return 'LocalBusiness'
