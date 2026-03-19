"""
multi_format_generator.py

Generates platform-specific content from a single source piece.

Supported output formats
------------------------
- ``html``          — Full HTML landing page block
- ``markdown``      — Blog post in GitHub-flavoured Markdown
- ``linkedin``      — Short-form LinkedIn post (hashtag optimised)
- ``youtube``       — YouTube video script outline
- ``reddit``        — Reddit thread outline (title + comment structure)
- ``twitter``       — Twitter/X thread (numbered tweets)
- ``email``         — Email newsletter snippet

The ``MultiFormatGenerator`` accepts a content source dictionary and an
optional LLM client.  When an LLM client is provided, it generates richer
content per format; otherwise it uses deterministic templates.
"""
from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class FormatOutput:
    """A single formatted piece of content."""

    format_name: str
    content: str
    platform_notes: str = ""
    estimated_reach: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MultiFormatBundle:
    """Container for all format outputs from a single source."""

    source_topic: str
    source_keyword: str
    outputs: dict[str, FormatOutput] = field(default_factory=dict)

    def get(self, format_name: str) -> FormatOutput | None:
        return self.outputs.get(format_name)

    def format_names(self) -> list[str]:
        return list(self.outputs.keys())


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

_SUPPORTED_FORMATS = [
    "html",
    "markdown",
    "linkedin",
    "youtube",
    "reddit",
    "twitter",
    "email",
]


class MultiFormatGenerator:
    """
    Converts a content source into multiple platform-specific formats.

    Parameters
    ----------
    llm_client:
        Optional LLM client with a ``complete(prompt)`` method.  When
        provided, format outputs are generated via LLM calls; otherwise
        deterministic template logic is used.

    Usage::

        gen = MultiFormatGenerator()
        bundle = gen.generate_all(source)
        print(bundle.get("linkedin").content)
    """

    def __init__(self, llm_client: Any = None) -> None:
        self._llm = llm_client

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    @staticmethod
    def supported_formats() -> list[str]:
        """Return the list of supported format names."""
        return list(_SUPPORTED_FORMATS)

    def generate_all(
        self,
        source: dict[str, Any],
        formats: list[str] | None = None,
    ) -> MultiFormatBundle:
        """
        Generate all (or a subset of) formats from *source*.

        Parameters
        ----------
        source:
            Content source dictionary.  Expected keys:

            - ``topic`` (str) — article/page topic
            - ``primary_keyword`` (str) — target keyword
            - ``service_name`` (str, optional) — service label
            - ``key_points`` (list[str], optional) — 3-5 core messages
            - ``cta`` (str, optional) — call-to-action text
            - ``content`` (str, optional) — full generated content
            - ``trust_factors`` (list[str], optional)
            - ``testimonials`` (list[dict], optional)
        formats:
            Subset of ``supported_formats()`` to generate.  Defaults to all.

        Returns
        -------
        MultiFormatBundle
        """
        if formats is None:
            formats = _SUPPORTED_FORMATS
        else:
            unknown = set(formats) - set(_SUPPORTED_FORMATS)
            if unknown:
                raise ValueError(
                    f"Unsupported format(s): {sorted(unknown)}. "
                    f"Supported: {_SUPPORTED_FORMATS}"
                )

        bundle = MultiFormatBundle(
            source_topic=source.get("topic", ""),
            source_keyword=source.get("primary_keyword", ""),
        )

        for fmt in formats:
            generator_fn = getattr(self, f"_generate_{fmt}")
            bundle.outputs[fmt] = generator_fn(source)

        return bundle

    def generate_single(
        self, source: dict[str, Any], format_name: str
    ) -> FormatOutput:
        """
        Generate a single format output from *source*.

        Parameters
        ----------
        source:
            Content source dictionary (see ``generate_all``).
        format_name:
            One of ``supported_formats()``.

        Returns
        -------
        FormatOutput
        """
        if format_name not in _SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format '{format_name}'. "
                f"Supported: {_SUPPORTED_FORMATS}"
            )
        generator_fn = getattr(self, f"_generate_{format_name}")
        return generator_fn(source)

    # -----------------------------------------------------------------------
    # Format generators
    # -----------------------------------------------------------------------

    def _generate_html(self, source: dict[str, Any]) -> FormatOutput:
        topic = source.get("topic", "Service")
        keyword = source.get("primary_keyword", topic)
        service = source.get("service_name", topic)
        key_points = source.get("key_points", [])
        trust_factors = source.get("trust_factors", [])
        testimonials = source.get("testimonials", [])
        cta = source.get("cta", "Contact Us Today")

        if self._llm:
            prompt = (
                f"Write an HTML landing page content block (no <html>/<body> wrapper) for "
                f"'{service}' targeting the keyword '{keyword}'. "
                f"Include: H1, service description paragraph, a trust factors list, "
                f"and a CTA button. Use semantic HTML5. Keep it concise."
            )
            content = self._llm.complete(prompt)
        else:
            lines = [f"<h1>{topic}</h1>", ""]
            if key_points:
                lines += ["<ul class=\"key-points\">"]
                for pt in key_points:
                    lines.append(f"  <li>{pt}</li>")
                lines += ["</ul>", ""]
            if trust_factors:
                lines += ["<section class=\"trust\">", "  <ul>"]
                for tf in trust_factors:
                    lines.append(f"    <li>{tf}</li>")
                lines += ["  </ul>", "</section>", ""]
            for t in testimonials:
                lines += [
                    "<blockquote>",
                    f'  <p>"{t.get("quote", "")}"</p>',
                    f'  <cite>— {t.get("author", "")}</cite>',
                    "</blockquote>",
                    "",
                ]
            lines.append(
                f'<a href="#contact" class="cta-primary">{cta}</a>'
            )
            content = "\n".join(lines)

        return FormatOutput(
            format_name="html",
            content=content,
            platform_notes="Embed in CMS or static site page template.",
            estimated_reach="All organic search visitors",
        )

    def _generate_markdown(self, source: dict[str, Any]) -> FormatOutput:
        topic = source.get("topic", "Service")
        keyword = source.get("primary_keyword", topic)
        key_points = source.get("key_points", [])
        cta = source.get("cta", "Contact us to learn more.")

        if self._llm:
            prompt = (
                f"Write a 600-800 word blog post in GitHub-flavoured Markdown about "
                f"'{topic}' targeting the keyword '{keyword}'. "
                f"Include: H1 title, intro paragraph, 3 H2 sections with body text, "
                f"and a conclusion with CTA. Do not include front matter."
            )
            content = self._llm.complete(prompt)
        else:
            lines = [f"# {topic}", ""]
            lines.append(
                f"This guide covers everything you need to know about **{keyword}** "
                f"to make informed decisions for your business."
            )
            lines.append("")
            if key_points:
                for i, pt in enumerate(key_points[:5], 1):
                    lines += [f"## {i}. {pt}", "", f"Content about {pt}.", ""]
            else:
                lines += [
                    "## Why This Matters", "", f"Understanding {keyword} is essential.", "",
                    "## How It Works", "", "Here is a breakdown of the process.", "",
                    "## Getting Started", "", "Follow these steps to begin.", "",
                ]
            lines += [f"## Next Steps", "", cta, ""]
            content = "\n".join(lines)

        return FormatOutput(
            format_name="markdown",
            content=content,
            platform_notes="Publish to blog CMS or GitHub Pages. Add front matter as needed.",
            estimated_reach="Organic search + RSS/newsletter subscribers",
        )

    def _generate_linkedin(self, source: dict[str, Any]) -> FormatOutput:
        topic = source.get("topic", "")
        keyword = source.get("primary_keyword", topic)
        key_points = source.get("key_points", [])
        cta = source.get("cta", "Drop a comment or DM me to learn more.")

        # Build hashtags from keyword
        hashtags = self._make_hashtags(keyword, n=5)

        if self._llm:
            prompt = (
                f"Write a LinkedIn post about '{topic}'. "
                f"Hook in first line (no 'I' start). 3-5 short paragraphs. "
                f"End with a question and these hashtags: {' '.join(hashtags)}. "
                f"Max 300 words. Conversational but professional tone."
            )
            content = self._llm.complete(prompt)
        else:
            hook = f"Most people get {keyword} completely wrong. Here's what actually works:"
            bullets = "\n".join(f"• {pt}" for pt in (key_points or [f"Insight about {keyword}"])[:5])
            content = (
                f"{hook}\n\n"
                f"{bullets}\n\n"
                f"The bottom line: a data-driven approach to {keyword} consistently "
                f"outperforms intuition.\n\n"
                f"What's your experience? Drop a comment below.\n\n"
                f"{cta}\n\n"
                + " ".join(hashtags)
            )

        return FormatOutput(
            format_name="linkedin",
            content=content,
            platform_notes=(
                "Post between 08:00–10:00 or 17:00–19:00 on Tuesday–Thursday. "
                "Engage with comments within the first hour."
            ),
            estimated_reach="1st/2nd-degree connections + hashtag followers",
            metadata={"hashtags": hashtags, "recommended_length": "150-300 words"},
        )

    def _generate_youtube(self, source: dict[str, Any]) -> FormatOutput:
        topic = source.get("topic", "")
        keyword = source.get("primary_keyword", topic)
        key_points = source.get("key_points", [])
        cta = source.get("cta", "Subscribe for more content like this.")

        if self._llm:
            prompt = (
                f"Write a YouTube video script outline for a 10-minute video about "
                f"'{topic}' targeting '{keyword}'. "
                f"Include: hook (30s), intro (60s), 4-5 main sections with talking "
                f"points, B-roll suggestions, and outro with CTA. "
                f"Format as a script outline with timestamps."
            )
            content = self._llm.complete(prompt)
        else:
            sections = key_points if key_points else [
                f"What is {keyword}?",
                f"Why {keyword} matters in 2024",
                f"Common mistakes with {keyword}",
                f"How to get started with {keyword}",
                "Real-world results and case studies",
            ]
            lines = [
                f"# VIDEO SCRIPT: {topic}",
                f"**Target keyword:** {keyword}",
                f"**Estimated length:** 10-12 minutes",
                "",
                "---",
                "",
                "## HOOK [0:00–0:30]",
                f"Open with a bold statement or statistic about {keyword}.",
                "Tease the value viewers will get by watching.",
                "",
                "## INTRO [0:30–1:30]",
                f"Briefly introduce yourself and this channel's focus.",
                f"Explain what viewers will learn about {keyword}.",
                "",
            ]
            timestamp = 90
            for i, section in enumerate(sections[:5], 1):
                end = timestamp + 120
                lines += [
                    f"## SECTION {i}: {section} [{timestamp//60}:{timestamp%60:02d}–{end//60}:{end%60:02d}]",
                    f"- Key talking point 1 for: {section}",
                    "- Key talking point 2",
                    "- B-roll: [screen recording / footage suggestion]",
                    "",
                ]
                timestamp = end

            lines += [
                "## OUTRO",
                cta,
                "- Like and subscribe CTA",
                "- Link to full guide in description",
            ]
            content = "\n".join(lines)

        return FormatOutput(
            format_name="youtube",
            content=content,
            platform_notes=(
                "Upload with keyword-rich title and description. "
                "Add chapters using timestamps from the script."
            ),
            estimated_reach="YouTube search + subscriber notifications",
        )

    def _generate_reddit(self, source: dict[str, Any]) -> FormatOutput:
        topic = source.get("topic", "")
        keyword = source.get("primary_keyword", topic)
        key_points = source.get("key_points", [])

        if self._llm:
            prompt = (
                f"Write a Reddit thread outline for a post about '{topic}'. "
                f"Title should be a question or discussion prompt (no self-promotion). "
                f"Include: post body (300-400 words, educational), "
                f"3 suggested comment angles to seed discussion, "
                f"and recommended subreddits. Format as a structured outline."
            )
            content = self._llm.complete(prompt)
        else:
            subreddits = self._suggest_subreddits(keyword)
            insights = (
                "\n".join(f"- {pt}" for pt in key_points[:5])
                if key_points
                else f"- Key insight 1 about {keyword}\n- Key insight 2\n- Key insight 3"
            )
            content = textwrap.dedent(f"""\
                # REDDIT THREAD OUTLINE: {topic}

                **Suggested Subreddits:** {", ".join(subreddits)}

                ---

                ## THREAD TITLE (choose one):
                - "What's actually working for {keyword} in 2024? Sharing what we learned."
                - "I spent 6 months testing {keyword} strategies — here's the honest breakdown"
                - "Ask me anything about {keyword} — I've managed campaigns for 50+ clients"

                ---

                ## POST BODY:

                Background: [1-2 sentences on your experience/credentials]

                Here's what I've found actually moves the needle for {keyword}:

                {insights}

                What I've seen fail repeatedly:
                - [Common mistake 1]
                - [Common mistake 2]

                Happy to answer questions. What challenges are you currently facing?

                ---

                ## SEED COMMENT ANGLES:

                1. **Data angle:** Share a specific metric or test result
                2. **Contrarian angle:** Challenge a common assumption about {keyword}
                3. **Resource angle:** Offer a framework or checklist (no links initially)
            """)

        return FormatOutput(
            format_name="reddit",
            content=content,
            platform_notes=(
                "Post during peak hours (09:00–12:00 EST). "
                "Do not include promotional links in the initial post. "
                "Engage genuinely with all replies."
            ),
            estimated_reach="Subreddit subscribers + search traffic to thread",
        )

    def _generate_twitter(self, source: dict[str, Any]) -> FormatOutput:
        topic = source.get("topic", "")
        keyword = source.get("primary_keyword", topic)
        key_points = source.get("key_points", [])
        cta = source.get("cta", "Follow for more.")

        if self._llm:
            prompt = (
                f"Write a Twitter/X thread of 8-10 tweets about '{topic}'. "
                f"Tweet 1 is the hook (under 280 chars, no 'I' opener). "
                f"Tweets 2-9 each deliver one insight about {keyword}. "
                f"Final tweet has a CTA. Number each tweet (1/, 2/, etc.)."
            )
            content = self._llm.complete(prompt)
        else:
            points = key_points[:7] if key_points else [
                f"Most people misunderstand {keyword}.",
                "The data tells a different story.",
                "Here's what actually drives results.",
                "The common approach wastes resources.",
                "A better framework exists.",
                "Real results require real strategy.",
                "Start with the fundamentals.",
            ]
            tweets = [f"1/ {keyword.title()} is broken for most businesses.\n\nHere's the framework that actually works: 🧵"]
            for i, pt in enumerate(points, 2):
                tweets.append(f"{i}/ {pt}")
            tweets.append(
                f"{len(tweets) + 1}/ TL;DR: Focus on what moves the needle.\n\n"
                f"{cta}\n\nRT if this was useful 🔁"
            )
            content = "\n\n".join(tweets)

        return FormatOutput(
            format_name="twitter",
            content=content,
            platform_notes=(
                "Post between 08:00–10:00 or 18:00–20:00 local time. "
                "Reply to comments within 2 hours for algorithmic boost."
            ),
            estimated_reach="Followers + algorithmic reach via engagement",
            metadata={"tweet_count": content.count("\n\n") + 1},
        )

    def _generate_email(self, source: dict[str, Any]) -> FormatOutput:
        topic = source.get("topic", "")
        keyword = source.get("primary_keyword", topic)
        key_points = source.get("key_points", [])
        cta = source.get("cta", "Read the full guide →")
        service = source.get("service_name", topic)

        if self._llm:
            prompt = (
                f"Write an email newsletter snippet about '{topic}'. "
                f"Include: subject line (A/B test two options), preview text, "
                f"opening paragraph (2-3 sentences), 3 key takeaways as bullet points, "
                f"and a CTA button label. Keep it under 250 words total. "
                f"Conversational tone, not salesy."
            )
            content = self._llm.complete(prompt)
        else:
            bullets = (
                "\n".join(f"→ {pt}" for pt in key_points[:3])
                if key_points
                else (
                    f"→ Why {keyword} is misunderstood\n"
                    f"→ The framework that delivers results\n"
                    f"→ How to get started this week"
                )
            )
            content = textwrap.dedent(f"""\
                SUBJECT LINE (A): {keyword.title()}: What Most Businesses Get Wrong
                SUBJECT LINE (B): The {service} Strategy That's Working Right Now

                PREVIEW TEXT: Here's what the data shows about {keyword}...

                ---

                Hi [First Name],

                {keyword.title()} is one of those topics where bad advice is everywhere.

                This week, we're breaking down what actually works — with data to back it up.

                Here's what you'll learn:

                {bullets}

                [CTA BUTTON: {cta}]

                See you next week,
                [Sender Name]

                P.S. {key_points[0] if key_points else f"The biggest {keyword} mistake is easy to fix once you know it."}
            """)

        return FormatOutput(
            format_name="email",
            content=content,
            platform_notes=(
                "Send Tuesday–Thursday, 10:00–11:00 or 14:00–15:00. "
                "Personalise subject line with subscriber's first name. "
                "Test both subject line variants on 20% of list before full send."
            ),
            estimated_reach="Email subscribers (expected 20-30% open rate)",
            metadata={"recommended_send_day": "Tuesday or Wednesday"},
        )

    # -----------------------------------------------------------------------
    # Utility helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _make_hashtags(keyword: str, n: int = 5) -> list[str]:
        words = re.sub(r"[^a-zA-Z0-9\s]", "", keyword).split()
        tags: list[str] = []
        # Full keyword as one hashtag
        if words:
            tags.append("#" + "".join(w.capitalize() for w in words))
        # Individual significant words
        for w in words:
            if len(w) > 3:
                tags.append(f"#{w.lower()}")
        # Generic marketing tags
        generic = ["#DigitalMarketing", "#SEO", "#ContentMarketing", "#B2BMarketing", "#GrowthStrategy"]
        for g in generic:
            if len(tags) >= n:
                break
            if g not in tags:
                tags.append(g)
        return tags[:n]

    @staticmethod
    def _suggest_subreddits(keyword: str) -> list[str]:
        keyword_lower = keyword.lower()
        mapping = {
            "seo": ["r/SEO", "r/bigseo", "r/digital_marketing"],
            "marketing": ["r/marketing", "r/digital_marketing", "r/entrepreneur"],
            "linkedin": ["r/linkedin", "r/marketing", "r/socialmedia"],
            "ecommerce": ["r/ecommerce", "r/entrepreneur", "r/Shopify"],
            "content": ["r/content_marketing", "r/marketing", "r/blogging"],
            "investor": ["r/startups", "r/entrepreneur", "r/venturecapital"],
            "pr": ["r/PR", "r/marketing", "r/digital_marketing"],
        }
        for key, subs in mapping.items():
            if key in keyword_lower:
                return subs
        return ["r/marketing", "r/entrepreneur", "r/digital_marketing"]
