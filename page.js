"use client";
import { useState } from "react";

export default function Home() {
  const [text, setText] = useState("");
  const [tone, setTone] = useState("professional");
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRewrite = async () => {
    if (!text) return alert("Please enter some text!");
    setLoading(true);
    setResult("");
    
    try {
      const res = await fetch("http://127.0.0.1:8000/api/rewrite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, tone })
      });
      const data = await res.json();
      
      if (data.rewritten) {
        setResult(data.rewritten);
      } else {
        alert("Error: Something went wrong.");
      }
    } catch (error) {
      alert("Error connecting to server. Is your Python backend running?");
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8 font-sans">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-center text-gray-800 mb-2">
          ENL Semantic Rewriter
        </h1>
        <p className="text-center text-gray-500 mb-8">
          Rewrite articles with human-like flow and 100% uniqueness.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Input Box */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <h2 className="text-lg font-semibold text-gray-700 mb-3">Original Text</h2>
            <textarea
              className="w-full h-64 p-4 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none resize-none"
              placeholder="Paste your article here..."
              value={text}
              onChange={(e) => setText(e.target.value)}
            ></textarea>

            <div className="mt-4 flex items-center justify-between">
              <select 
                value={tone}
                onChange={(e) => setTone(e.target.value)}
                className="p-2 border border-gray-200 rounded-lg text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="professional">Professional</option>
                <option value="casual">Casual / Conversational</option>
                <option value="academic">Academic / Formal</option>
                <option value="creative">Creative / Storytelling</option>
              </select>

              <button
                onClick={handleRewrite}
                disabled={loading}
                className={`px-6 py-2 rounded-lg text-white font-medium transition-all ${
                  loading ? "bg-blue-300 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700 shadow-md"
                }`}
              >
                {loading ? "Rewriting..." : "Rewrite Now 🚀"}
              </button>
            </div>
          </div>

          {/* Output Box */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <h2 className="text-lg font-semibold text-gray-700 mb-3">Rewritten Result</h2>
            <div className="w-full h-64 p-4 bg-gray-50 border border-gray-200 rounded-lg overflow-y-auto">
              {loading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="animate-pulse flex space-x-2">
                    <div className="w-3 h-3 bg-blue-400 rounded-full"></div>
                    <div className="w-3 h-3 bg-blue-400 rounded-full"></div>
                    <div className="w-3 h-3 bg-blue-400 rounded-full"></div>
                  </div>
                </div>
              ) : result ? (
                <p className="text-gray-800 whitespace-pre-wrap">{result}</p>
              ) : (
                <p className="text-gray-400 text-center mt-20">Your rewritten text will appear here.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}