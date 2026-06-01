import React, { useState } from 'react';
import './index.css';

export default function Home() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [analysisType, setAnalysisType] = useState('full');
  const [error, setError] = useState(null);

  const handleTranscribe = async (e) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    
    if (!url.trim()) {
      setError('Please enter a YouTube URL');
      return;
    }

    setLoading(true);
    
    try {
      const response = await fetch('/api/transcribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: url.trim(),
          analysis_type: analysisType
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Transcription failed');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
  };

  return (
    <div className="container">
      <div className="header">
        <h1>🎬 YouTube Transcript Generator</h1>
        <p>Paste a YouTube URL and get summaries, Twitter threads, and more in seconds.</p>
      </div>

      <form onSubmit={handleTranscribe} className="form">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://youtu.be/vB08-7RzgOs"
          className="input"
          disabled={loading}
        />

        <div className="controls">
          <select
            value={analysisType}
            onChange={(e) => setAnalysisType(e.target.value)}
            className="select"
            disabled={loading}
          >
            <option value="full">Full Analysis</option>
            <option value="summary">Summary Only</option>
            <option value="threads">Twitter Threads</option>
            <option value="show_notes">Show Notes</option>
          </select>

          <button
            type="submit"
            disabled={loading}
            className={`button ${loading ? 'loading' : ''}`}
          >
            {loading ? '⏳ Processing...' : '✨ Transcribe & Analyze'}
          </button>
        </div>
      </form>

      {error && (
        <div className="error">
          <strong>❌ Error:</strong> {error}
        </div>
      )}

      {result && (
        <div className="results">
          <div className="meta">
            <p><strong>Method:</strong> {result.method}</p>
            <p><strong>Time:</strong> {result.processing_time}s</p>
            <p><strong>Cost:</strong> ${result.cost.toFixed(4)}</p>
          </div>

          {result.analysis.summary && (
            <section className="section">
              <h2>📝 Summary</h2>
              <p className="summary-text">{result.analysis.summary}</p>
              <button onClick={() => copyToClipboard(result.analysis.summary)} className="copy-btn">
                Copy
              </button>
            </section>
          )}

          {result.analysis.key_points && (
            <section className="section">
              <h2>🎯 Key Points</h2>
              <ul className="key-points">
                {result.analysis.key_points.map((point, i) => (
                  <li key={i}>{point}</li>
                ))}
              </ul>
            </section>
          )}

          {result.analysis.twitter_threads && (
            <section className="section">
              <h2>🐦 Twitter Threads</h2>
              <div className="threads">
                {result.analysis.twitter_threads.thread_5 && (
                  <div className="thread">
                    <h3>5-Tweet Thread</h3>
                    {result.analysis.twitter_threads.thread_5.map((tweet, i) => (
                      <div key={i} className="tweet">
                        <p>{i + 1}. {tweet}</p>
                      </div>
                    ))}
                    <button 
                      onClick={() => copyToClipboard(result.analysis.twitter_threads.thread_5.join('\n\n'))} 
                      className="copy-btn"
                    >
                      Copy Thread
                    </button>
                  </div>
                )}
              </div>
            </section>
          )}

          {result.analysis.seo_metadata && (
            <section className="section">
              <h2>🔍 SEO Metadata</h2>
              <div className="seo">
                <div>
                  <strong>Title:</strong> {result.analysis.seo_metadata.title}
                </div>
                <div>
                  <strong>Description:</strong> {result.analysis.seo_metadata.description}
                </div>
                <div>
                  <strong>Keywords:</strong> {result.analysis.seo_metadata.keywords.join(', ')}
                </div>
              </div>
            </section>
          )}

          <details className="transcript-details">
            <summary>Full Transcript ({result.transcript.length} chars)</summary>
            <pre>{result.transcript}</pre>
          </details>
        </div>
      )}
    </div>
  );
}
