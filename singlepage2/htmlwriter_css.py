<script>
function toggleMenu() {{
  const navLinks = document.getElementById('navLinks');
  const hamburger = document.getElementById('hamburgerBtn');
  navLinks.classList.toggle('open');
  if (hamburger) {{
    hamburger.classList.toggle('open');
  }}
}}

function toggleDropdown(e) {{
  e.preventDefault();
  const dropdown = e.target.closest('#dropdowntoogle');
  if (!dropdown) return;
  dropdown.classList.toggle('open');
}}

// Fetch and insert images into content
async function fetchAndInsertImages() {{
  try {{
    const response = await fetch(`/imageapp/images/{{{{ placename }}}}/`);
    const data = await response.json();
    const images = data.images.map(img => img.imbbURL);
    const shuffled = shuffleArray(images);
    const bodyContents = document.querySelector("#body-contents");
    if (!bodyContents) return;

    const sections = Array.from(bodyContents.querySelectorAll('.content-section, .intro-section'));
    const insertionPoints = sections.length > 0 ? sections : [bodyContents];

    let count = 0;
    const maxImages = 3;
    shuffled.slice(0, maxImages).forEach((imgUrl) => {{
      if (count >= maxImages) return;
      count++;
      const img = document.createElement("img");
      Object.assign(img, {{
        src: imgUrl,
        loading: "lazy",
        alt: "Blog content image",
        style: `
          max-width: 100%; display: block; margin: 1.5rem 0; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        `
      }});

      const section = insertionPoints[Math.floor(Math.random() * insertionPoints.length)];
      const children = Array.from(section.children);
      if (children.length > 0) {{
        const randIndex = Math.floor(Math.random() * children.length);
        children[randIndex].insertAdjacentElement('afterend', img);
      }} else {{
        section.appendChild(img);
      }}
    }});
  }} catch (err) {{
    console.error("Error fetching images:", err);
  }}
}}

// Generic fetch function with error handling
async function fetchData(endpoint, elementId, templateFn, errorMsg) {{
  const csrftoken = getCookie('csrftoken');
  try {{
    const response = await fetch(`/apis/${{endpoint}}/`, {{
      headers: {{
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrftoken,
      }}
    }});
    if (!response.ok) throw new Error(`HTTP ${{response.status}}`);
    const data = await response.json();
    if (!data || data.length === 0) {{
      const el = document.getElementById(elementId);
      if (el) el.textContent = errorMsg;
      return;
    }}
    templateFn(data);
  }} catch (err) {{
    console.error(`Error fetching ${{endpoint}}:`, err);
    const el = document.getElementById(elementId);
    if (el) el.textContent = `Failed to load ${{endpoint}}`;
  }}
}}

// Populate blog list
function getBlogLists() {{
  fetchData('getPlaceBlogs/{{{{ placename }}}}', 'blog-list', (data) => {{
    const list = document.getElementById('blog-list');
    const fragment = document.createDocumentFragment();
    data.forEach(blog => {{
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = blog.localurlpath;
      a.textContent = blog.title.replace(/<\/?a[^>]*>/g, '');
      li.appendChild(a);
      fragment.appendChild(li);
    }});
    list.appendChild(fragment);
  }}, 'No blogs found for this place.');
}}

// Populate collections
function fetchCollections() {{
  fetchData('getPlaceCollections/{{{{ placename }}}}', 'collections-loading', (data) => {{
    const container = document.querySelector('#dynamic-collections');
    const fragment = document.createDocumentFragment();
    data.forEach(col => {{
      const div = document.createElement('div');
      div.className = 'collection-item';

      if (col.collectionPicture) {{
        const img = document.createElement('img');
        img.src = col.collectionPicture;
        img.alt = col.collectionName || 'Collection image';
        img.loading = 'lazy';
        div.appendChild(img);
      }}

      const h4 = document.createElement('h4');
      h4.textContent = col.name || '';
      div.appendChild(h4);

      if (col.address || col.collectionDescription) {{
        const p = document.createElement('p');
        p.textContent = (col.collectionDescription || '').substring(0, 130) + '...';
        div.appendChild(p);
      }}

      fragment.appendChild(div);
    }});
    container.appendChild(fragment);
    document.getElementById('collections-loading').style.display = 'none';
  }}, 'No local collections found nearby.');
}}

// Helper to get cookie value
function getCookie(name) {{
  const cookies = document.cookie ? document.cookie.split(';') : [];
  for (let cookie of cookies) {{
    cookie = cookie.trim();
    if (cookie.startsWith(`${{name}}=`)) {{
      return decodeURIComponent(cookie.slice(name.length + 1));
    }}
  }}
  return null;
}}

// Initialize event listeners on DOMContentLoaded
document.addEventListener("DOMContentLoaded", () => {{
  // Submit form
  const form = document.querySelector("#imageform");
  form.addEventListener("submit", (e) => {{
    e.preventDefault();
    const formData = new FormData(form);
    fetch("{{{{ upload_url }}}}", {{
      method: "POST",
      body: formData,
      headers: {{
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCookie('csrftoken'),
      }}
    }})
    .then(res => res.json())
    .then(data => console.log("Success:", data))
    .catch(err => console.error(err));
  }});

  // Fetch images and populate content
  fetchAndInsertImages();
  getBlogLists();
  fetchCollections();

  // Hamburger toggle
  const hamburgerBtn = document.getElementById('hamburgerBtn');
  if (hamburgerBtn) {{
    hamburgerBtn.addEventListener('click', () => {{
      hamburgerBtn.classList.toggle('open');
      document.getElementById('navLinks').classList.toggle('open');
    }});
  }}

  // Close dropdown on outside click
  document.addEventListener('click', (ev) => {{
    const dropdown = document.getElementById('dropdowntoogle');
    if (!dropdown) return;
    if (dropdown.classList.contains('open') && !dropdown.contains(ev.target)) {{
      dropdown.classList.remove('open');
    }}
    // Close on link click inside dropdown
    if (ev.target.tagName === 'A' && dropdown.contains(ev.target)) {{
      dropdown.classList.remove('open');
    }}
  }});

  // Close dropdown on Escape
  document.addEventListener('keydown', (ev) => {{
    if (ev.key === 'Escape') {{
      const dropdown = document.getElementById('dropdowntoogle');
      dropdown && dropdown.classList.remove('open');
    }}
  }});
}});
</script>