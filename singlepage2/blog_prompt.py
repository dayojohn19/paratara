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
  <!-- Header Section with Background Hero Capabilities -->
  <header class="post-hero">
    <h1 class="post-title">🎯 [Emoji + Catchy Title]</h1>
    <p class="post-intro">[Intro Hook: Max 150 words. Start with a relatable story, pain point, or vivid situation to grab attention.]</p>
  </header>

  <!-- Core Content Body -->
  <div class="post-body">
    
    <!-- Section 1: The Personal Value/Review -->
    <section class="content-block">
      <h2>🧭 Why It’s Worth It: My Personal Experience</h2>
      <p>[Share your unique perspective. Detail how to experience, use, or choose it. Include practical next steps, setup tips, or buying advice.]</p>
    </section>  

    <!-- Section 2: Core Features & Highlights -->
    <section class="content-block">
      <h2>✨ Key Features & Best Uses</h2>
      <p>[Break down the main benefits, things to do, or top use cases that fit your specific topic.]</p>
      
      <!-- Quick Summary Box -->
      <aside class="highlight-box">
        <h3>Known for:</h3>
        <ul class="check-list">
          <li>✅ Item 1</li>
          <li>✅ Item 2</li>
        </ul>
      </aside>
    </section>

    <!-- Section 3: Data Breakdown (Flexible for Costs, Specs, or Itineraries) -->
    <section class="content-block data-breakdown">
      <h2>📊 Practical Breakdown</h2>
      <p>[Insert your budget tables, step-by-step guides, technical comparisons, or transit directions here.]</p>
    </section>

    <!-- Section 4: Tips, Tricks, and Maintenance -->
    <aside class="tip-box">
      <h3>💡 Pro Tips for Success</h3>
      <ul>
        <li><strong>[Tip 1 Headline]:</strong> [Actionable advice, maintenance trick, or smart hack.]</li>
        <li><strong>[Tip 2 Headline]:</strong> [Current-year consideration or hidden feature advice.]</li>
      </ul>
    </aside>

    <!-- Section 5: Safety, News & Critical Updates -->
    <section class="content-block safety-box">
      <h2>⚠️ Safety, Warnings & Current Updates</h2>
      <p>[Crucial safety information, local cautions, product recalls, or real-time local news/status updates.]</p>
    </section>

  </div>

  <!-- Footer Section: Call to Action -->
  <footer class="post-cta">
    <h2>🚀 Ready to Get Started?</h2>
    <p>[Closing Statement: Ask a question to drive comments, or add a link/button to buy, subscribe, or visit.]</p>
  </footer>
</article>

'''
