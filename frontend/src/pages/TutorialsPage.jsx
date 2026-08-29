import React, { useState } from "react";
import { Play, X, Clock, PlayCircle } from "lucide-react";

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
    thumbnail:
      "https://images.unsplash.com/photo-1556742049-63ff75e904f0?w=800&q=80",
    videoUrl: "https://www.youtube.com/embed/dQw4w9WgXcQ", // Replace with your actual video IDs
  },
  {
    id: 2,
    title: "Processing Your First Order",
    category: "POS",
    duration: "6:45",
    thumbnail:
      "https://images.unsplash.com/photo-1556740734-7f95834d1599?w=800&q=80",
    videoUrl: "https://www.youtube.com/embed/dQw4w9WgXcQ",
  },
  {
    id: 3,
    title: "Understanding Sales Reports",
    category: "Reports",
    duration: "10:03",
    thumbnail:
      "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80",
    videoUrl: "https://www.youtube.com/embed/dQw4w9WgXcQ",
  },
  {
    id: 4,
    title: "Managing Inventory",
    category: "Inventory",
    duration: "7:30",
    thumbnail:
      "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=800&q=80",
    videoUrl: "https://www.youtube.com/embed/dQw4w9WgXcQ",
  },
  {
    id: 5,
    title: "Configuring Restaurant Settings",
    category: "Settings",
    duration: "9:15",
    thumbnail:
      "https://images.unsplash.com/photo-1551288049-bbbda5366392?w=800&q=80",
    videoUrl: "https://www.youtube.com/embed/dQw4w9WgXcQ",
  },
];

export default function TutorialsPage() {
  const [activeCategory, setActiveCategory] = useState("All");
  const [selectedVideo, setSelectedVideo] = useState(null);

  const filtered =
    activeCategory === "All"
      ? VIDEOS
      : VIDEOS.filter((v) => v.category === activeCategory);

  return (
    <div className="space-y-6 p-4 max-w-7xl mx-auto">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Video Tutorials</h1>
          <p className="text-slate-500 text-sm">
            Learn how to master BEEPOS step-by-step.
          </p>
        </div>
      </div>

      {/* Category filter */}
      <div className="flex flex-wrap gap-2 pb-2">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setActiveCategory(cat)}
            className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${
              activeCategory === cat
                ? "bg-amber-400 text-slate-950 shadow-md shadow-amber-200"
                : "bg-white text-slate-600 border border-slate-200 hover:border-amber-300"
            }`}>
            {cat}
          </button>
        ))}
      </div>

      {/* Video grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {filtered.map((video) => (
          <div
            key={video.id}
            onClick={() => setSelectedVideo(video)}
            className="group bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all cursor-pointer">
            <div className="relative aspect-video overflow-hidden">
              <img
                src={video.thumbnail}
                alt={video.title}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />
              <div className="absolute inset-0 bg-black/20 group-hover:bg-black/40 transition-colors flex items-center justify-center">
                <div className="bg-white/90 p-3 rounded-full scale-90 group-hover:scale-100 transition-transform">
                  <Play
                    className="text-slate-900 fill-current"
                    size={24}
                  />
                </div>
              </div>
              <div className="absolute bottom-2 right-2 bg-black/70 text-white text-[10px] font-bold px-2 py-1 rounded flex items-center gap-1">
                <Clock size={10} /> {video.duration}
              </div>
            </div>

            <div className="p-4">
              <span className="text-[10px] font-bold text-amber-600 uppercase tracking-wider">
                {video.category}
              </span>
              <h3 className="font-bold text-slate-800 mt-1 line-clamp-1 group-hover:text-amber-600 transition-colors">
                {video.title}
              </h3>
            </div>
          </div>
        ))}
      </div>

      {/* Video Player Modal */}
      {selectedVideo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/90 backdrop-blur-sm">
          <div className="relative w-full max-w-4xl bg-black rounded-3xl overflow-hidden shadow-2xl animate-in zoom-in-95 duration-200">
            <button
              onClick={() => setSelectedVideo(null)}
              className="absolute top-4 right-4 z-10 p-2 bg-white/10 hover:bg-white/20 text-white rounded-full transition-colors">
              <X size={24} />
            </button>

            <div className="aspect-video w-full">
              <iframe
                src={`${selectedVideo.videoUrl}?autoplay=1`}
                title={selectedVideo.title}
                className="w-full h-full"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen></iframe>
            </div>

            <div className="p-6 bg-slate-900">
              <div className="flex items-center gap-2 text-amber-400 text-xs font-bold uppercase mb-2">
                <PlayCircle size={14} /> Now Playing
              </div>
              <h2 className="text-xl font-bold text-white">
                {selectedVideo.title}
              </h2>
              <p className="text-slate-400 text-sm mt-1">
                Category: {selectedVideo.category} • {selectedVideo.duration}
              </p>
            </div>
          </div>
          {/* Click outside to close */}
          <div
            className="absolute inset-0 -z-10"
            onClick={() => setSelectedVideo(null)}></div>
        </div>
      )}
    </div>
  );
}
