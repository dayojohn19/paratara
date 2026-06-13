def build_blog_prompt(blog_title, place_name, promotion_instruction):
    return f'''Create a polished, engaging blog post from this user topic/request:
"{blog_title}"

Local context/place: "{place_name}"
Promotion/link instruction: {promotion_instruction}

IMPORTANT INTENT RULES:
- First understand the real intent of the topic/request. It may be travel, a product promotion, a general lifestyle topic, a local guide, an event, a story, a tip article, or something else.
- Do NOT force every article to be a tourist travel guide.
- If the topic is travel, attractions, restaurants, resorts, activities, events, or visiting "{place_name}", write a useful travel/local guide.
- If the topic promotes a product or includes a promotional URL, write an editorial blog that connects "{place_name}" to the product naturally. For example, show how the product helps with a local activity, trip, lifestyle, climate, family outing, commute, resort stay, beach day, pool day, or everyday need. Mention the product with helpful context, not as spam.
- If the topic is not travel-related, write about the requested subject directly and use "{place_name}" only as a relevant local angle, example, audience context, or setting.
- If the request text includes words like "create a blog about", "write about", or similar instructions, ignore those command words and focus on the actual subject.
- Never invent specific breaking news, official rules, festival dates, prices, or safety alerts. If exact current details are uncertain, say readers should verify official/local sources before going or buying.

RESPONSE FORMAT (EXACTLY):
Title: [Catchy title, max 60 chars]
Category: [Choose ONE based on intent: Guide, Story, Tip and Trick, Explore, Product]
Summary: [One-line summary for preview, max 140 chars]

<article class="blog-post">
[HTML content below]
</article>

REQUIREMENTS:
- HTML only (no markdown)
- Use CSS classes: blog-post, intro-section, content-section, highlight-box, tip-box, mindset-box, cta-section
- Include emojis in all h2 headings
- Match the audience to the intent: tourists for travel topics, local readers for local/lifestyle topics, shoppers for product topics, and general readers for broad topics
- Be specific, practical, warm, and premium in tone
- Include estimated costs, comparisons, practical tips, activities, use cases, or buying considerations only when relevant to the topic
- If a URL was provided, include the exact link HTML from the promotion/link instruction once, with natural context
- Avoid keyword stuffing and hard-sell language

CONTENT STRUCTURE (must include ALL sections, but adapt headings/content to the intent):

HTML TEMPLATE EXAMPLE:
<article class="blog-post">
  <div class="intro-section">
    <h1 class="white-color">🎯 [Emoji + Title]</h1>
    <p>[Intro Section (150 words max) - Hook the reader with a relevant story or situation]</p>
  </div>
  <div class="content-section">
    <h2>🧭 [What Makes It Worth personal Experience]</h2>
    <p>[How To Experience / Use / Choose It - Practical next steps, directions, usage tips, or buying advice]</p>
  </div>  
  <div class="content-section">
    <h2>✨ [Feature Title]</h2>
    <p>[Best Uses / Things To Do / Key Benefits - Choose the label that fits the topic]</p>
    <div class="highlight-box">
      <h3>Known for:</h3>
      <ul><li>✅ Item 1</li><li>✅ Item 2</li></ul>
    </div>
  </div>
  [Practical Breakdown - Costs, budget, time, features, comparisons, or planning details when relevant, how to get there, or how to use/buy]
  <div class="tip-box">
  [Safety, Updates & Smart Tips - Safety, maintenance, local cautions, verification advice, or current-year considerations without inventing facts]
    <p><strong>💡 Pro Tips:</strong></p>
    <ul><li>Tip 1</li><li>Tip 2</li></ul>
  </div>
  <div class="mindset-box">
    <h1>⚠️ Safety & Updates</h1>
    <p>[Safety information and current local news]</p>
  </div>
  <div class="cta-section">
    <h1>🚀 Ready to Visit?</h1>
    <p>[Call to Action - Strong closing statement that fits the topic ]</p>
  </div>
</article>
'''
