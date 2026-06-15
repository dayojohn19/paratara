def build_blog_prompt(blog_title, place_name, promotion_instruction):
    # A blog topic and promotion note should never consume most of the model context.
    blog_title = str(blog_title or "").strip()[:3000]
    place_name = str(place_name or "").strip()[:200]
    promotion_instruction = str(promotion_instruction or "").strip()[:2000]

    return f'''Write a polished blog post about: "{blog_title}"
Local context: "{place_name}"
Promotion instruction: {promotion_instruction}

Determine the topic's real intent. Write a local/travel guide only for travel,
attraction, restaurant, resort, activity, event, or visit topics. For products,
write a useful editorial article and connect the product to "{place_name}"
naturally. Otherwise, address the subject directly and use the place only when
relevant. Ignore phrases such as "write a blog about" in the topic.

Return exactly this format, with no markdown or code fences:
Title: [catchy title, maximum 60 characters]
Category: [one of: Guide, Story, Tip and Trick, Explore, Product]
Summary: [one line, maximum 140 characters]

<article class="blog-post">
  <header class="post-hero">
    <h1 class="post-title">[emoji and title]</h1>
    <p class="post-intro">[brief hook]</p>
  </header>
  <div class="post-body">
    <section class="content-section">
      <h2>🧭 [meaningful section title]</h2>
      <p>[why it matters and practical advice]</p>
    </section>
    <section class="content-section">
      <h2>✨ [meaningful section title]</h2>
      <p>[features, activities, or best uses]</p>
    </section>
    <aside class="highlight-box">
      <h2>✅ [meaningful highlights title]</h2>
      <p>[short key-points introduction]</p>
      <ul><li>[key point]</li></ul>
    </aside>
    <section class="content-section data-breakdown">
      <h2>📊 [meaningful practical title]</h2>
      <p>[relevant costs, steps, comparisons, directions, or planning details]</p>
    </section>
    <aside class="tip-box">
      <h2>💡 [meaningful tips title]</h2>
      <p>[actionable tips introduction]</p>
      <ul><li>[actionable tip]</li></ul>
    </aside>
    <section class="content-section safety-box">
      <h2>⚠️ [meaningful caution title]</h2>
      <p>[relevant cautions and verification advice]</p>
    </section>
  </div>
  <footer class="post-cta">
    <h2>🚀 [meaningful closing title]</h2>
    <p>[natural closing and call to action]</p>
  </footer>
</article>

Rules:
- Write 700-1,200 words of valid HTML inside the article.
- Give every section meaningful headings; include an emoji in every h2.
- Every section, aside, and footer must use an h2 for its title and p tags for
  normal body text. Never place plain text directly inside these containers.
- Use additional p tags for additional paragraphs; do not use bare text or br
  tags as a substitute for paragraphs.
- Adapt sections to the topic instead of forcing irrelevant travel details.
- Be specific, practical, warm, and premium; avoid keyword stuffing and hype.
- Include costs, comparisons, activities, or buying advice only when useful.
- If a URL/link was supplied, include its exact link HTML once in natural context.
- Never invent current news, rules, dates, prices, recalls, or safety alerts.
  When current details are uncertain, advise checking official/local sources.
'''
