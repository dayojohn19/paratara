 const accessKey = "fXI_L-wmv-PZt4chRdmotjG3ha2vQntZgLm3bbb5QHY"; // 🔑 your Unsplash API key
  async function setBackground(PlaceItemToCreateObject) {
    const url = `https://api.unsplash.com/search/photos?query=${PlaceItemToCreateObject.placename}&client_id=${accessKey}&per_page=1`;
    try {
      const res = await fetch(url);
      const data = await res.json();

      if (data.results.length > 0) {
        console.log(`Setting background for ${data.results[0].urls.regular}`);
        const el = document.querySelector(`[data-place="${PlaceItemToCreateObject.placename}"]`);
        // el.style.backgroundImage = 'url("https://picsum.photos/400/300")';
 
        // el.style.backgroundImage = `url(${data.results[0].urls.regular})`;
        el.style.backgroundImage = `url(${PlaceItemToCreateObject.placePhoto})`;
        el.style.backgroundSize = "cover";
        el.style.backgroundPosition = "center";
      } else {
        console.warn(`No image found for ${place}`);
      }
    } catch (err) {
      console.error("Error fetching Unsplash image:", err);
    }
  }
