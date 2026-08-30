function Stats({ stats }) {
  if (!stats) return <p className="text-gray-500">Loading stats...</p>;

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      <div className="bg-white rounded-xl shadow-sm border p-4 text-center">
        <p className="text-2xl font-bold text-gray-800">{stats.total_farmers}</p>
        <p className="text-sm text-gray-500">Total Farmers</p>
      </div>
      <div className="bg-green-50 rounded-xl shadow-sm border border-green-200 p-4 text-center">
        <p className="text-2xl font-bold text-green-700">{stats.by_stress_level.low}</p>
        <p className="text-sm text-green-600">Low</p>
      </div>
      <div className="bg-yellow-50 rounded-xl shadow-sm border border-yellow-200 p-4 text-center">
        <p className="text-2xl font-bold text-yellow-700">{stats.by_stress_level.moderate}</p>
        <p className="text-sm text-yellow-600">Moderate</p>
      </div>
      <div className="bg-orange-50 rounded-xl shadow-sm border border-orange-200 p-4 text-center">
        <p className="text-2xl font-bold text-orange-700">{stats.by_stress_level.high}</p>
        <p className="text-sm text-orange-600">High</p>
      </div>
      <div className="bg-red-50 rounded-xl shadow-sm border border-red-200 p-4 text-center">
        <p className="text-2xl font-bold text-red-700">{stats.by_stress_level.critical}</p>
        <p className="text-sm text-red-600">Critical</p>
      </div>
    </div>
  );
}

export default Stats;