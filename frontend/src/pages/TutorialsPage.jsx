import { useState } from "react";

const CATEGORIES = [
  "All",
  "Onboarding",
  "POS",
  "Reports",
  "Inventory",
  "Settings",
];

const VIDEOS = [
  {
    id: 1,
    title: "Getting Started with BEEPOS",
    category: "Onboarding",
    duration: "8:12",
    thumbnail: "https://via.placeholder.com/320x180?text=Onboarding+1",
  },
  {
    id: 2,
    title: "Processing Your First Order",
    category: "POS",
    duration: "6:45",
    thumbnail: "https://via.placeholder.com/320x180?text=POS+1",
  },
  {
    id: 3,
    title: "Understanding Sales Reports",
    category: "Reports",
    duration: "10:03",
    thumbnail: "https://via.placeholder.com/320x180?text=Reports+1",
  },
  {
    id: 4,
    title: "Managing Inventory",
    category: "Inventory",
    duration: "7:30",
    thumbnail: "https://via.placeholder.com/320x180?text=Inventory+1",
  },
  {
    id: 5,
    title: "Configuring Restaurant Settings",
    category: "Settings",
    duration: "9:15",
    thumbnail: "https://via.placeholder.com/320x180?text=Settings+1",
  },
];

export default function TutorialsPage() {
  const [activeCategory, setActiveCategory] = useState("All");

  const filtered =
    activeCategory === "All"
      ? VIDEOS
      : VIDEOS.filter((v) => v.category === activeCategory);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Video Tutorials</h1>

      {/* Category filter */}
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setActiveCategory(cat)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
              activeCategory === cat
                ? "bg-amber-400 text-slate-950"
                : "bg-white text-slate-700 border border-slate-300 hover:bg-slate-50"
            }`}>
            {cat}
          </button>
        ))}
      </div>

      {/* Video grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((video) => (
          <div
            key={video.id}
            className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <img
              src={video.thumbnail}
              alt={video.title}
              className="w-full aspect-video object-cover"
            />
            <div className="p-4">
              <div className="text-xs text-slate-500 mb-1">
                {video.category}
              </div>
              <h3 className="font-semibold text-slate-800 mb-2">
                {video.title}
              </h3>
              <div className="text-xs text-slate-500">{video.duration}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
