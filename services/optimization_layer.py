"""
Virtual Optimization Layer — GPT-4o powered meta-tag optimizer and
async-safe JavaScript injection script builder.
"""
from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI


def generate_optimization_payload(
    page_url: str,
    client_data: dict[str, Any],
    api_key: str,
) -> dict[str, Any]:
    """
    Call GPT-4o to analyse the page and return optimised SEO tags.

    Parameters
    ----------
    page_url:
        The URL of the page to optimise.
    client_data:
        Dict with keys: name, business_type, niche, location, phone, website.
    api_key:
        OpenAI API key.

    Returns
    -------
    dict with keys: title, meta_description, schema_json, og_tags, twitter_tags.
    """
    client = OpenAI(api_key=api_key)

    business_name = client_data.get("name", "")
    business_type = client_data.get("business_type", "")
    niche = client_data.get("niche", "")
    location = client_data.get("location", "")
    phone = client_data.get("phone", "")
    website = client_data.get("website", page_url)

    system_prompt = (
        "You are an expert SEO systems architect. "
        "Return ONLY valid JSON — no markdown, no code fences, no commentary."
    )

    user_prompt = f"""Analyse this page and generate production-ready SEO tags.

Page URL: {page_url}
Business: {business_name}
Type: {business_type}
Niche: {niche}
Location: {location}
Phone: {phone}
Website: {website}

Return a single JSON object with EXACTLY these keys:
{{
  "title": "<60-char keyword-first title tag value>",
  "meta_description": "<155-char meta description ending with a CTA>",
  "schema_json": {{...LocalBusiness JSON-LD object (not wrapped in <script>)...}},
  "og_tags": {{
    "og:title": "...",
    "og:description": "...",
    "og:type": "website",
    "og:locale": "en_US",
    "og:url": "{page_url}"
  }},
  "twitter_tags": {{
    "twitter:card": "summary_large_image",
    "twitter:title": "...",
    "twitter:description": "...",
    "twitter:site": "@{business_name.replace(' ', '')}"
  }}
}}

Rules:
- title: keyword-first, max 60 chars, no brand suffix needed
- meta_description: max 155 chars, include action CTA ("Call today", "Get a free quote", etc.)
- schema_json: full LocalBusiness schema with @context, @type, name, telephone, url, address
- og:title and twitter:title may match the title tag
- All values must be strings (no nested objects except schema_json and address)"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1200,
        temperature=0.3,
    )

    raw = response.choices[0].message.content.strip()
    # Strip any accidental markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    payload: dict[str, Any] = json.loads(raw)
    return payload


def build_injection_script(payload: dict[str, Any]) -> str:
    """
    Build a minified, async-safe JavaScript snippet that injects meta tags
    into any page's <head> — with a MutationObserver guard to re-inject
    if the CMS removes them.

    Parameters
    ----------
    payload:
        The dict returned by ``generate_optimization_payload``.

    Returns
    -------
    A ``<script>`` tag string ready to paste into any site's ``<head>``.
    """
    title = _js_str(payload.get("title", ""))
    meta_desc = _js_str(payload.get("meta_description", ""))

    schema_obj = payload.get("schema_json", {})
    schema_str = _js_str(json.dumps(schema_obj, separators=(",", ":")))

    og_tags: dict[str, str] = payload.get("og_tags", {})
    twitter_tags: dict[str, str] = payload.get("twitter_tags", {})

    # Build arrays of [name/property, content] pairs
    og_entries = json.dumps(
        [[k, v] for k, v in og_tags.items()], separators=(",", ":")
    )
    tw_entries = json.dumps(
        [[k, v] for k, v in twitter_tags.items()], separators=(",", ":")
    )

    # Raw (non-minified) JavaScript — we strip whitespace below
    js_source = f"""(function(){{
var TITLE={title!r};
var DESC={meta_desc!r};
var SCHEMA={schema_str!r};
var OG={og_entries};
var TW={tw_entries};
function cleanup(){{
var h=document.head;
var sel=['meta[name="description"]','script[type="application/ld+json"]'];
var og_re=/^og:/;
var tw_re=/^twitter:/;
h.querySelectorAll('meta').forEach(function(m){{
var p=m.getAttribute('property')||'';
var n=m.getAttribute('name')||'';
if(n==='description'||og_re.test(p)||tw_re.test(n))m.remove();
}});
h.querySelectorAll('script[type="application/ld+json"]').forEach(function(s){{s.remove();}});
}}
function inject(){{
cleanup();
var h=document.head;
document.title=TITLE;
var dm=document.createElement('meta');
dm.setAttribute('name','description');
dm.setAttribute('content',DESC);
h.appendChild(dm);
OG.forEach(function(pair){{
var m=document.createElement('meta');
m.setAttribute('property',pair[0]);
m.setAttribute('content',pair[1]);
h.appendChild(m);
}});
TW.forEach(function(pair){{
var m=document.createElement('meta');
m.setAttribute('name',pair[0]);
m.setAttribute('content',pair[1]);
h.appendChild(m);
}});
var s=document.createElement('script');
s.setAttribute('type','application/ld+json');
s.textContent=SCHEMA;
h.appendChild(s);
}}
var _tags=[];
function reInject(){{
_tags=[].slice.call(document.head.querySelectorAll(
'meta[name="description"],meta[property^="og:"],meta[name^="twitter:"],script[type="application/ld+json"]'
));
if(_tags.length<3)inject();
}}
function attachGuard(){{
inject();
var obs=new MutationObserver(function(){{reInject();}});
obs.observe(document.head,{{childList:true}});
setTimeout(function(){{obs.disconnect();}},30000);
}}
if(document.readyState==='complete'||document.readyState==='interactive'){{
attachGuard();
}}else{{
document.addEventListener('DOMContentLoaded',attachGuard);
}}
}})();"""

    # Minify: collapse runs of whitespace / newlines
    minified = re.sub(r"\s{2,}", " ", js_source.replace("\n", " "))
    # Strip spaces around braces/brackets/parens/semicolons that are safe
    for pair in [(" {", "{"), ("{ ", "{"), (" }", "}"), ("} ", "}"),
                 (" (", "("), ("( ", "("), (" )", ")"), (") ", ")"),
                 (" ;", ";"), ("; ", ";"), (" ,", ","), (", ", ","),
                 (" =", "="), ("= ", "="), (" +", "+"), ("+ ", "+")]:
        minified = minified.replace(pair[0], pair[1])

    script_tag = f"<script>{minified.strip()}</script>"
    return script_tag


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _js_str(value: str) -> str:
    """Escape a Python string for safe embedding as a JS string literal."""
    return value.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
