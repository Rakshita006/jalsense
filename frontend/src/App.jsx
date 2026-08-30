import { useState, useEffect } from 'react';
import axios from 'axios';
import Stats from './components/Stats';
import FarmerFeed from './components/FarmerFeed';
import FarmersMap from './components/FarmersMap';

function App() {
  const [village, setVillage] = useState('');
  const [crop, setCrop] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [farmers, setFarmers] = useState([]);
  const [stats, setStats] = useState(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);

  const fetchDashboardData = () => {
    axios.get('http://127.0.0.1:8000/api/farmers')
      .then((response) => setFarmers(response.data.farmers))
      .catch(() => setFarmers([]));

    axios.get('http://127.0.0.1:8000/api/stats')
      .then((response) => setStats(response.data))
      .catch(() => setStats(null))
      .finally(() => setDashboardLoading(false));
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post('http://127.0.0.1:8000/api/analyze', {
        village: village,
        crop: crop,
        phone_number: `demo-${Date.now()}`,
      });
      setResult(response.data);
      fetchDashboardData();
    } catch (err) {
      setError('Something went wrong. Check the village name and try again.');
    } finally {
      setLoading(false);
    }
  };

  const stressColor = {
    low: 'bg-green-100 text-green-800 border-green-400',
    moderate: 'bg-yellow-100 text-yellow-800 border-yellow-400',
    high: 'bg-orange-100 text-orange-800 border-orange-400',
    critical: 'bg-red-100 text-red-800 border-red-400',
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8 font-sans space-y-8">
      <h1 className="text-3xl font-bold text-gray-800">🌾 JalSense Live Demo</h1>

      <Stats stats={stats} />
      <FarmerFeed farmers={farmers} loading={dashboardLoading} />
      <FarmersMap farmers={farmers} />

      <div>
        <div className="flex gap-3 mb-4">
          <input
            type="text"
            placeholder="Village name"
            value={village}
            onChange={(e) => setVillage(e.target.value)}
            className="border border-gray-300 rounded-lg px-4 py-2 w-48 focus:outline-none focus:ring-2 focus:ring-green-500"
          />
          <input
            type="text"
            placeholder="Crop"
            value={crop}
            onChange={(e) => setCrop(e.target.value)}
            className="border border-gray-300 rounded-lg px-4 py-2 w-48 focus:outline-none focus:ring-2 focus:ring-green-500"
          />
          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-medium px-6 py-2 rounded-lg transition"
          >
            {loading ? 'Analyzing...' : 'Analyze'}
          </button>
        </div>

        {error && (
          <p className="text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2 inline-block">
            {error}
          </p>
        )}

        {result && (
          <div
            className={`mt-4 max-w-md rounded-xl border-2 p-5 shadow-sm ${
              stressColor[result.stress_level] || 'bg-gray-100 text-gray-800 border-gray-300'
            }`}
          >
            <p className="text-lg font-semibold capitalize mb-2">
              Stress Level: {result.stress_level} ({result.stress_score}/100)
            </p>
            <p><span className="font-medium">NDVI:</span> {result.ndvi}</p>
            <p><span className="font-medium">NDWI:</span> {result.ndwi}</p>
            <p><span className="font-medium">Rain Probability:</span> {result.rain_probability}%</p>
            <p className="mt-3 border-t pt-3">{result.recommendation_hi}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;