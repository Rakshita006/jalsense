import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

function FarmersMap({ farmers }) {
  const stressColor = {
    low: '#22c55e',
    moderate: '#eab308',
    high: '#f97316',
    critical: '#ef4444',
  };

  const center = farmers.length > 0
    ? [farmers[0].latitude, farmers[0].longitude]
    : [22.9734, 78.6569]; // rough center of India, fallback

  return (
    <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
      <h2 className="text-lg font-semibold px-5 py-3 border-b bg-gray-50">Farmer Map</h2>
      <MapContainer center={center} zoom={5} style={{ height: '400px', width: '100%' }}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
        />
        {farmers.map((farmer) => (
          <CircleMarker
            key={farmer.id}
            center={[farmer.latitude, farmer.longitude]}
            radius={10}
            pathOptions={{
              color: stressColor[farmer.stress_level] || '#9ca3af',
              fillColor: stressColor[farmer.stress_level] || '#9ca3af',
              fillOpacity: 0.7,
            }}
          >
            <Popup>
              <strong>{farmer.village_name}</strong><br />
              Crop: {farmer.crop_name}<br />
              Stress: {farmer.stress_level}
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}

export default FarmersMap;