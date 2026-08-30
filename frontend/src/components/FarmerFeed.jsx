function FarmerFeed({ farmers, loading, onDelete }) {
  const stressBadge = {
    low: 'bg-green-100 text-green-800',
    moderate: 'bg-yellow-100 text-yellow-800',
    high: 'bg-orange-100 text-orange-800',
    critical: 'bg-red-100 text-red-800',
  };

  if (loading) return <p className="text-gray-500">Loading farmers...</p>;

  return (
    <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
      <h2 className="text-lg font-semibold px-5 py-3 border-b bg-gray-50">Farmer Feed</h2>
      <table className="w-full text-left">
        <thead>
          <tr className="text-sm text-gray-500 border-b">
            <th className="px-5 py-2">Phone</th>
            <th className="px-5 py-2">Village</th>
            <th className="px-5 py-2">Crop</th>
            <th className="px-5 py-2">Stress Level</th>
            <th className="px-5 py-2">Registered</th>
            <th className="px-5 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {farmers.map((farmer) => (
            <tr key={farmer.id} className="border-b last:border-0">
              <td className="px-5 py-3">{farmer.phone_number}</td>
              <td className="px-5 py-3">{farmer.village_name}</td>
              <td className="px-5 py-3 capitalize">{farmer.crop_name}</td>
              <td className="px-5 py-3">
                <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${stressBadge[farmer.stress_level] || 'bg-gray-100 text-gray-800'}`}>
                  {farmer.stress_level}
                </span>
              </td>
              <td className="px-5 py-3 text-sm text-gray-500">
                {new Date(farmer.registered_at).toLocaleDateString()}
              </td>
              <td className="px-5 py-3">
                <button
                  onClick={() => onDelete(farmer.id)}
                  className="text-red-500 hover:text-red-700 text-sm"
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {farmers.length === 0 && (
        <p className="text-center text-gray-400 py-6">No farmers registered yet.</p>
      )}
    </div>
  );
}

export default FarmerFeed;