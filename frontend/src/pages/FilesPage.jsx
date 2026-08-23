import { useState } from "react";

const INITIAL_FILES = [
  {
    id: 1,
    name: "products_import_2025-09-01.csv",
    type: "CSV",
    size: "245 KB",
    uploadedAt: "2025-09-01 10:23",
  },
  {
    id: 2,
    name: "sales_report_august_2025.xlsx",
    type: "Excel",
    size: "1.2 MB",
    uploadedAt: "2025-09-05 14:10",
  },
  {
    id: 3,
    name: "invoice_1023.pdf",
    type: "PDF",
    size: "180 KB",
    uploadedAt: "2025-09-10 09:05",
  },
];

export default function FilesPage() {
  const [files, setFiles] = useState(INITIAL_FILES);
  const [uploading, setUploading] = useState(false);

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    // Mock upload delay
    setTimeout(() => {
      const newFile = {
        id: Date.now(),
        name: file.name,
        type: file.name.split(".").pop()?.toUpperCase() || "FILE",
        size: `${(file.size / 1024).toFixed(1)} KB`,
        uploadedAt: new Date().toISOString().slice(0, 16).replace("T", " "),
      };
      setFiles((f) => [newFile, ...f]);
      setUploading(false);
      e.target.value = "";
    }, 800);
  }

  function handleDelete(id) {
    if (!confirm("Delete this file?")) return;
    setFiles((f) => f.filter((file) => file.id !== id));
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">File Management</h1>

      {/* Upload */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">
          Upload Files
        </h2>
        <div className="flex items-center gap-4">
          <label className="inline-flex items-center gap-2 bg-slate-800 hover:bg-slate-900 text-white font-semibold px-4 py-2 rounded-lg text-sm cursor-pointer transition">
            <input
              type="file"
              className="hidden"
              onChange={handleFileChange}
              disabled={uploading}
            />
            <span>{uploading ? "Uploading..." : "Choose File"}</span>
          </label>
          <div className="text-sm text-slate-500">
            Supported: CSV, Excel, PDF, images
          </div>
        </div>
      </div>

      {/* File list */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-700">
              <tr>
                <th className="text-left px-4 py-3 font-semibold">Name</th>
                <th className="text-left px-4 py-3 font-semibold">Type</th>
                <th className="text-left px-4 py-3 font-semibold">Size</th>
                <th className="text-left px-4 py-3 font-semibold">Uploaded</th>
                <th className="text-right px-4 py-3 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {files.map((file) => (
                <tr
                  key={file.id}
                  className="border-t border-slate-100">
                  <td className="px-4 py-3 text-slate-800">{file.name}</td>
                  <td className="px-4 py-3 text-slate-600">{file.type}</td>
                  <td className="px-4 py-3 text-slate-600">{file.size}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {file.uploadedAt}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => handleDelete(file.id)}
                      className="text-red-600 hover:text-red-700 font-medium">
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {files.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-6 text-center text-slate-500">
                    No files uploaded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
