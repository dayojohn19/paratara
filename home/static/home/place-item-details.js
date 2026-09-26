(function () {
  const modal = document.getElementById('piM');
  const toggle = document.getElementById('piMore');
  const details = document.getElementById('piDetails');
  const summaryWrap = document.getElementById('piSummaryWrap');
  const summary = document.getElementById('piSummary');
  const addressWrap = document.getElementById('piAddressWrap');
  const address = document.getElementById('piAddress');
  const mapWrap = document.getElementById('piMapWrap');
  const map = document.getElementById('piMap');
  const mapLink = document.getElementById('piMapLink');
  const establishmentLink = document.getElementById('piEstablishmentLink');

  if (!modal || !toggle || !details) return;

  function validCoordinates(item) {
    if (item.resortLatitude == null || item.resortLongitude == null ||
        item.resortLatitude === '' || item.resortLongitude === '') return null;
    const latitude = Number(item.resortLatitude);
    const longitude = Number(item.resortLongitude);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;
    if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) return null;
    return { latitude, longitude };
  }

  function mapUrl(latitude, longitude) {
    const delta = 0.008;
    const bounds = [longitude - delta, latitude - delta, longitude + delta, latitude + delta].join(',');
    return `https://www.openstreetmap.org/export/embed.html?bbox=${encodeURIComponent(bounds)}&layer=mapnik&marker=${encodeURIComponent(`${latitude},${longitude}`)}`;
  }

  function mapSearchUrl(item, coordinates) {
    const query = coordinates
      ? `${coordinates.latitude},${coordinates.longitude}`
      : item.resortAddress;
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
  }

  function resetDetails() {
    details.hidden = true;
    toggle.setAttribute('aria-expanded', 'false');
    toggle.textContent = 'More details';
    map.src = 'about:blank';
  }

  function prepareDetails(item) {
    const resortSummary = String(item.resortDescription || '').trim();
    const resortAddress = String(item.resortAddress || '').trim();
    const resortLink = String(item.resortLink || '').trim();
    const coordinates = validCoordinates(item);
    const hasDetails = Boolean(resortSummary || resortAddress || coordinates || resortLink);

    summary.textContent = resortSummary;
    summaryWrap.hidden = !resortSummary;
    address.textContent = resortAddress;
    addressWrap.hidden = !resortAddress;
    mapWrap.hidden = !coordinates;
    mapLink.hidden = !(coordinates || resortAddress);
    mapLink.href = coordinates || resortAddress ? mapSearchUrl(item, coordinates) : '';
    establishmentLink.hidden = !resortLink;
    establishmentLink.href = resortLink;
    map.title = item.resortName
      ? `Map showing ${item.resortName}`
      : 'Map showing this establishment';
    map.dataset.embedUrl = coordinates
      ? mapUrl(coordinates.latitude, coordinates.longitude)
      : '';
    toggle.hidden = !hasDetails;
    resetDetails();
  }

  document.addEventListener('click', function (event) {
    const card = event.target.closest && event.target.closest('.jpic');
    if (card) {
      const item = window.placeItemModalState && window.placeItemModalState.item;
      item ? prepareDetails(item) : resetDetails();
      return;
    }

    if (event.target.closest && event.target.closest('#piMore')) {
      const isOpen = details.hidden;
      details.hidden = !isOpen;
      toggle.setAttribute('aria-expanded', String(isOpen));
      toggle.textContent = isOpen ? 'Hide details' : 'More details';
      if (isOpen && map.dataset.embedUrl && map.getAttribute('src') !== map.dataset.embedUrl) {
        map.src = map.dataset.embedUrl;
      }
    }
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && modal.classList.contains('is-open')) resetDetails();
  });
}());