import React from 'react';

interface ResultsTableProps {
  data: any; // The JSON data to display
}

const renderValue = (value: any): JSX.Element | string => {
  if (typeof value === 'object' && value !== null) {
    if (Array.isArray(value)) {
      return (
        <ul>
          {value.map((item, index) => (
            <li key={index}>{renderValue(item)}</li>
          ))}
        </ul>
      );
    }
    // For objects, render key-value pairs or a sub-table
    return (
      <table className="min-w-full divide-y divide-gray-700 border border-gray-600 bg-gray-800 text-sm">
        <tbody className="divide-y divide-gray-700">
          {Object.entries(value).map(([key, val]) => (
            <tr key={key}>
              <td className="whitespace-nowrap px-3 py-2 font-medium text-gray-300 capitalize">{key.replace(/_/g, ' ')}</td>
              <td className="px-3 py-2 text-gray-400">{renderValue(val)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }
  if (value === null || value === undefined) {
    return <span className="italic text-gray-500">N/A</span>;
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  return String(value);
};

const ResultsTable: React.FC<ResultsTableProps> = ({ data }) => {
  if (!data) {
    return <p className="text-gray-400">No data to display.</p>;
  }

  // Filter out private attributes like _documents if they exist
  const displayData = { ...data };
  if (displayData._documents) {
    delete displayData._documents;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-700 bg-gray-900 text-white">
      <table className="min-w-full divide-y divide-gray-700 text-sm">
        <thead className="bg-gray-800">
          <tr>
            <th scope="col" className="whitespace-nowrap px-3 py-2.5 text-left font-semibold text-gray-300">
              Factor / Category
            </th>
            <th scope="col" className="whitespace-nowrap px-3 py-2.5 text-left font-semibold text-gray-300">
              Details
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-700 bg-gray-850">
          {Object.entries(displayData).map(([key, value]) => (
            <tr key={key}>
              <td className="whitespace-nowrap px-3 py-2 font-medium text-gray-300 capitalize">
                {key.replace(/_/g, ' ')}
              </td>
              <td className="px-3 py-2 text-gray-400">
                {renderValue(value)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ResultsTable;

