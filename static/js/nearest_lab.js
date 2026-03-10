// Leaflet + Geolocation + Overpass API glue for Nearest Soil Labs
(function(){
  let map = null;
  let userMarker = null;
  let labMarkers = [];
  let loading = false;

  function msgBox() {
    return document.getElementById('lab-messages');
  }

  function clearMessages() {
    const box = msgBox();
    if (box) box.innerHTML = '';
  }

  function showMessage(kind, text) {
    const box = msgBox();
    if (!box) { console[kind === 'error' ? 'error' : 'log'](text); return; }
    const div = document.createElement('div');
    div.className = `alert alert-${kind}`; // matches base.html styling
    div.setAttribute('role', 'alert');
    div.innerHTML = `${text} <button type="button" class="close-btn" aria-label="Close">&times;</button>`;
    div.querySelector('.close-btn').addEventListener('click', () => div.remove());
    box.appendChild(div);
    // Auto-dismiss (errors stay longer)
    const ttl = kind === 'error' ? 8000 : 5000;
    setTimeout(() => {
      if (div && div.parentNode) div.remove();
    }, ttl);
  }

  function setLoading(isLoading) {
    loading = !!isLoading;
    const btns = [
      document.getElementById('locate-btn'),
      document.getElementById('city-submit'),
    ].filter(Boolean);
    btns.forEach(b => b.disabled = loading);
  }

  function initMap(lat, lon) {
    const center = [lat, lon];
    // Swap placeholder -> map
    const ph = document.getElementById('map-placeholder');
    const mapEl = document.getElementById('map');
    if (ph) ph.style.display = 'none';
    if (mapEl && mapEl.style.display === 'none') mapEl.style.display = 'block';

    if (!map) {
      // Disable default zoomControl so we can place it explicitly
      map = L.map('map', { zoomControl: false }).setView(center, 13);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(map);
      // Re-add zoom control at a non-overlapping position
      L.control.zoom({ position: 'bottomright' }).addTo(map);
      // Ensure proper sizing after becoming visible
      setTimeout(() => { if (map) map.invalidateSize(); }, 0);
    } else {
      map.setView(center, 13);
      map.invalidateSize();
    }
    if (userMarker) {
      map.removeLayer(userMarker);
    }
    userMarker = L.marker(center, { title: 'Your location' }).addTo(map).bindPopup('You are here');
    userMarker.openPopup();
  }

  function clearLabMarkers() {
    labMarkers.forEach(m => m.remove());
    labMarkers = [];
  }

  async function geocodeCity(city) {
    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(city)}&limit=1`;
    const res = await fetch(url, {
      headers: {
        // Let browser set User-Agent; include a referer implicitly. Keep lightweight.
        'Accept': 'application/json'
      }
    });
    if (!res.ok) throw new Error(`Geocoding failed (${res.status})`);
    const arr = await res.json();
    if (!Array.isArray(arr) || arr.length === 0) throw new Error('City not found');
    const item = arr[0];
    const lat = parseFloat(item.lat);
    const lon = parseFloat(item.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) throw new Error('Invalid geocoding result');
    return { lat, lon, displayName: item.display_name };
  }

  async function fetchLabs(lat, lon) {
    const url = `/get-nearby-labs/?lat=${lat}&lon=${lon}`;
    console.log('Requesting labs:', { lat, lon, url });
    const res = await fetch(url);
    const text = await res.text();
    let payload = {};
    try { payload = text ? JSON.parse(text) : {}; } catch (e) { payload = { raw: text }; }
    if (!res.ok) {
      if (res.status === 404) return { labs: [] };
      if (res.status === 504) {
        throw new Error('Lab search service is busy right now. Please try again in a few seconds.');
      }
      const msg = (payload && (payload.error || payload.message)) || `Server error ${res.status}`;
      throw new Error(msg);
    }
    return payload;
  }

  function renderLabs(lat, lon, data) {
    clearLabMarkers();

    const labs = Array.isArray(data?.labs) ? data.labs : [];
    if (labs.length === 0) {
      showMessage('warning', 'No labs found within 100km of your location.');
      return;
    }

    const bounds = L.latLngBounds([[lat, lon]]);

    labs.forEach(lab => {
      const pos = [lab.lat, lab.lon];
      const name = lab.name || 'Unknown Lab';
      const addr = lab.address || 'Address not available';

      // Optional contact info
      const phone = (lab.phone && lab.phone !== 'Not available') ? lab.phone : null;
      const email = (lab.email && lab.email !== 'Not available') ? lab.email : null;
      const website = (lab.website && lab.website !== 'Not available') ? lab.website : null;

      let popupHtml = `<strong>${name}</strong><br>${addr}`;
      if (phone) popupHtml += `<br>Phone: ${phone}`;
      if (email) popupHtml += `<br>Email: ${email}`;
      if (website) {
        const href = website.startsWith('http') ? website : `http://${website}`;
        popupHtml += `\n<br><a href="${href}" target="_blank" rel="noopener">Website</a>`;
      }

      const m = L.marker(pos, { title: name })
        .addTo(map)
        .bindPopup(popupHtml);
      labMarkers.push(m);
      bounds.extend(pos);
    });

    // Ensure user's location is included in bounds
    bounds.extend([lat, lon]);
    map.fitBounds(bounds.pad(0.15));

    showMessage('success', `${labs.length} lab(s) found within 100km.`);
  }

  async function runWithCoords(lat, lon) {
    try {
      clearMessages();
      setLoading(true);
      showMessage('info', 'Searching labs near your location...');
      initMap(lat, lon);
      const data = await fetchLabs(lat, lon);
      renderLabs(lat, lon, data);
    } catch (e) {
      console.error('Failed to load labs:', e);
      showMessage('error', `Failed to load labs: ${e.message || e}`);
    }
    finally { setLoading(false); }
  }

  function wireEvents() {
    const btn = document.getElementById('locate-btn');
    if (btn) {
      btn.addEventListener('click', () => {
        if (!navigator.geolocation) {
          showMessage('warning', 'Geolocation is not supported by your browser. Please search by city instead.');
          return;
        }
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            const lat = pos.coords.latitude;
            const lon = pos.coords.longitude;
            runWithCoords(lat, lon);
          },
          (err) => {
            console.warn('Geolocation error:', err);
            showMessage('error', 'Unable to get your location. Please allow location access or search by city.');
          },
          { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
      });
    }

    // manual-form removed

    const cityForm = document.getElementById('city-form');
    if (cityForm) {
      cityForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const input = document.getElementById('city-name');
        const city = (input && input.value || '').trim();
        if (!city) {
          showMessage('warning', 'Please enter a city name.');
          return;
        }
        try {
          clearMessages();
          setLoading(true);
          showMessage('info', 'Searching city...');
          const { lat, lon, displayName } = await geocodeCity(city);
          initMap(lat, lon);
          const data = await fetchLabs(lat, lon);
          renderLabs(lat, lon, data);
          if (displayName) showMessage('success', `Showing labs near ${displayName}`);
        } catch (err) {
          console.error('City search failed:', err);
          showMessage('error', `City search failed: ${err.message || err}`);
        }
        finally { setLoading(false); }
      });
    }
  }

  document.addEventListener('DOMContentLoaded', wireEvents);
})();
